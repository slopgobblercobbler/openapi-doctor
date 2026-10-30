"""Rule to detect and autofix missing, duplicate, and invalid operation IDs."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set

from openapi_doctor.models import Diagnostic, FixAction, RuleId, Severity
from openapi_doctor.parser import ParsedSpec
from openapi_doctor.rules.base import BaseRule, iter_operations

VALID_OP_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")


def generate_operation_id(method: str, path: str, existing_ids: Set[str]) -> str:
    """
    Generates a clean, unique camelCase operation ID from HTTP method and path.
    Example: GET /users/{userId}/repos -> getUsersReposByUserId
    """
    segments = [s for s in path.strip("/").split("/") if s]
    path_words: List[str] = []
    by_params: List[str] = []

    for seg in segments:
        if seg.startswith("{") and seg.endswith("}"):
            param_name = seg[1:-1]
            # Clean parameter name
            param_name = re.sub(r"[^a-zA-Z0-9]", " ", param_name)
            words = [w.capitalize() for w in param_name.split() if w]
            by_params.append("".join(words))
        else:
            cleaned = re.sub(r"[^a-zA-Z0-9]", " ", seg)
            words = [w.capitalize() for w in cleaned.split() if w]
            path_words.extend(words)

    method_prefix = method.lower()
    base_id = method_prefix + "".join(path_words)
    if by_params:
        base_id += "By" + "And".join(by_params)

    if not base_id or base_id == method_prefix:
        base_id = f"{method_prefix}Endpoint"

    # Ensure uniqueness against existing_ids
    candidate = base_id
    counter = 1
    while candidate in existing_ids:
        candidate = f"{base_id}_{counter}"
        counter += 1

    return candidate


def sanitize_operation_id(op_id: str) -> str:
    """Sanitizes an invalid operationId into a valid alphanumeric identifier."""
    # Replace invalid chars with underscores or spaces
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "_", op_id)
    # Collapse multiple underscores
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned if cleaned else "operation"


class OperationIdRule(BaseRule):
    """
    Validates operationId across all operations:
    1. Checks that operationId is present (missing-operation-id).
    2. Checks that operationId is unique across the document (duplicate-operation-id).
    3. Checks that operationId contains only valid identifier characters (invalid-operation-id).
    Autofixes by generating, deduplicating, or sanitizing operation IDs.
    """

    rule_id = RuleId.MISSING_OPERATION_ID
    default_severity = Severity.WARNING
    description = "Checks for missing, duplicate, or malformed operation IDs."

    def handles_rule_id(self, rule_id: str) -> bool:
        return rule_id in (
            RuleId.MISSING_OPERATION_ID,
            RuleId.DUPLICATE_OPERATION_ID,
            RuleId.INVALID_OPERATION_ID,
        )

    def check(self, spec: ParsedSpec, context: Dict[str, Any]) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []
        seen_op_ids: Dict[str, List[Tuple[str, str, str]]] = {}  # op_id -> [(path, method, op_pointer)]
        all_op_ids: Set[str] = set()

        # First pass: collect all defined operation IDs
        for path, method, op, op_pointer in iter_operations(spec.data):
            op_id = op.get("operationId")
            if isinstance(op_id, str) and op_id.strip():
                clean_id = op_id.strip()
                all_op_ids.add(clean_id)
                seen_op_ids.setdefault(clean_id, []).append((path, method, op_pointer))

        # Second pass: check each operation
        for path, method, op, op_pointer in iter_operations(spec.data):
            op_id = op.get("operationId")
            id_pointer = f"{op_pointer}/operationId"
            line, col = spec.get_location(op_pointer)

            # Check 1: Missing operation ID
            if op_id is None or (isinstance(op_id, str) and not op_id.strip()):
                suggested_id = generate_operation_id(method, path, all_op_ids)
                all_op_ids.add(suggested_id)

                fix_action = FixAction(
                    rule_id=RuleId.MISSING_OPERATION_ID,
                    description=f"Add generated operationId '{suggested_id}' to {method.upper()} {path}",
                    target_pointer=id_pointer,
                    action_type="set",
                    value=suggested_id,
                )

                diagnostics.append(
                    Diagnostic(
                        rule_id=RuleId.MISSING_OPERATION_ID,
                        message=f"Operation '{method.upper()} {path}' is missing 'operationId'.",
                        severity=Severity.WARNING,
                        pointer=id_pointer,
                        line=line,
                        column=col,
                        fixable=True,
                        fix_action=fix_action,
                        suggestion=f"Set operationId to '{suggested_id}'",
                    )
                )
                continue

            if isinstance(op_id, str):
                trimmed_id = op_id.strip()

                # Check 2: Invalid format / illegal characters
                if not VALID_OP_ID_PATTERN.match(trimmed_id):
                    sanitized = sanitize_operation_id(trimmed_id)
                    counter = 1
                    while sanitized in all_op_ids and sanitized != trimmed_id:
                        sanitized = f"{sanitized}_{counter}"
                        counter += 1
                    all_op_ids.add(sanitized)

                    fix_action = FixAction(
                        rule_id=RuleId.INVALID_OPERATION_ID,
                        description=f"Sanitize operationId '{trimmed_id}' to '{sanitized}' in {method.upper()} {path}",
                        target_pointer=id_pointer,
                        action_type="set",
                        value=sanitized,
                    )

                    diagnostics.append(
                        Diagnostic(
                            rule_id=RuleId.INVALID_OPERATION_ID,
                            message=f"Operation '{method.upper()} {path}' has malformed operationId '{trimmed_id}'. Must be alphanumeric identifier.",
                            severity=Severity.WARNING,
                            pointer=id_pointer,
                            line=line,
                            column=col,
                            fixable=True,
                            fix_action=fix_action,
                            suggestion=f"Sanitize to '{sanitized}'",
                        )
                    )

                # Check 3: Duplicate operation ID (OpenAPI Spec ERROR)
                occurrences = seen_op_ids.get(trimmed_id, [])
                if len(occurrences) > 1:
                    # Find our occurrence index
                    occ_indices = [idx for idx, occ in enumerate(occurrences) if occ[2] == op_pointer]
                    if occ_indices and occ_indices[0] > 0:
                        # Only flag and fix subsequent duplicates, preserving the first
                        dedup_idx = occ_indices[0] + 1
                        deduped_id = f"{trimmed_id}_{dedup_idx}"
                        while deduped_id in all_op_ids:
                            dedup_idx += 1
                            deduped_id = f"{trimmed_id}_{dedup_idx}"
                        all_op_ids.add(deduped_id)

                        fix_action = FixAction(
                            rule_id=RuleId.DUPLICATE_OPERATION_ID,
                            description=f"Deduplicate operationId '{trimmed_id}' to '{deduped_id}' in {method.upper()} {path}",
                            target_pointer=id_pointer,
                            action_type="set",
                            value=deduped_id,
                        )

                        diagnostics.append(
                            Diagnostic(
                                rule_id=RuleId.DUPLICATE_OPERATION_ID,
                                message=f"Duplicate operationId '{trimmed_id}' in '{method.upper()} {path}'. Operation IDs must be globally unique.",
                                severity=Severity.ERROR,
                                pointer=id_pointer,
                                line=line,
                                column=col,
                                fixable=True,
                                fix_action=fix_action,
                                suggestion=f"Change duplicate operationId to '{deduped_id}'",
                            )
                        )

        return diagnostics
