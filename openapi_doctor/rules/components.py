"""Rule to detect and autofix unused components."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from openapi_doctor.models import Diagnostic, FixAction, RuleId, Severity
from openapi_doctor.parser import ParsedSpec, escape_pointer_token
from openapi_doctor.rules.base import BaseRule, iter_operations
from openapi_doctor.rules.references import walk_references

COMPONENT_SECTIONS = (
    "schemas",
    "responses",
    "parameters",
    "examples",
    "requestBodies",
    "headers",
    "securitySchemes",
    "links",
    "callbacks",
)


def collect_used_references_and_security(doc: Dict[str, Any]) -> Tuple[Set[str], Set[str]]:
    """
    Returns (set of all $ref values, set of all security scheme names used in security requirements).
    """
    used_refs: Set[str] = set()
    for ref_val, _, _ in walk_references(doc, []):
        used_refs.add(ref_val)

    used_security_schemes: Set[str] = set()

    def inspect_security(sec_list: Any) -> None:
        if isinstance(sec_list, list):
            for sec_req in sec_list:
                if isinstance(sec_req, dict):
                    for scheme_name in sec_req.keys():
                        used_security_schemes.add(scheme_name)

    # Root security
    inspect_security(doc.get("security"))

    # Operation security
    for _, _, op, _ in iter_operations(doc):
        inspect_security(op.get("security"))

    return used_refs, used_security_schemes


class UnusedComponentRule(BaseRule):
    """
    Detects defined components under `components/*` that are never referenced in the document.
    Autofixes by removing unused components to prune bloat.
    """

    rule_id = RuleId.UNUSED_COMPONENT
    default_severity = Severity.WARNING
    description = "Component is declared in 'components' but never referenced anywhere in the specification."

    def check(self, spec: ParsedSpec, context: Dict[str, Any]) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []
        components = spec.data.get("components")
        if not isinstance(components, dict):
            return diagnostics

        used_refs, used_security_schemes = collect_used_references_and_security(spec.data)

        for section in COMPONENT_SECTIONS:
            items = components.get(section)
            if not isinstance(items, dict):
                continue

            for name in items.keys():
                canonical_ref = f"#/components/{section}/{name}"
                is_used = canonical_ref in used_refs

                # Special check for security schemes
                if section == "securitySchemes" and name in used_security_schemes:
                    is_used = True

                if not is_used:
                    comp_pointer = f"/components/{section}/{escape_pointer_token(name)}"
                    line, col = spec.get_location(comp_pointer)

                    fix_action = FixAction(
                        rule_id=self.rule_id,
                        description=f"Remove unused component '{section}/{name}'",
                        target_pointer=comp_pointer,
                        action_type="delete",
                    )

                    diagnostics.append(
                        Diagnostic(
                            rule_id=self.rule_id,
                            message=f"Unused component '{section}/{name}' is declared but never referenced.",
                            severity=self.default_severity,
                            pointer=comp_pointer,
                            line=line,
                            column=col,
                            fixable=True,
                            fix_action=fix_action,
                            suggestion=f"Remove '{section}/{name}' or add reference to it",
                        )
                    )

        return diagnostics
