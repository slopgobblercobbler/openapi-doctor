"""Rule to detect and autofix missing and unused path parameters."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set

from openapi_doctor.models import Diagnostic, FixAction, RuleId, Severity
from openapi_doctor.parser import ParsedSpec, escape_pointer_token
from openapi_doctor.rules.base import BaseRule, iter_operations

PATH_PARAM_REGEX = re.compile(r"\{([a-zA-Z0-9_\-]+)\}")


class PathParameterRule(BaseRule):
    """
    Validates path parameters in OpenAPI operations:
    1. Ensures all {param} tokens in the URL template have a matching parameter definition with in: "path".
    2. Ensures path parameters have required: true (OpenAPI 3 requirement).
    3. Detects path parameters declared with in: "path" that do not exist in the URL template.
    Autofixes missing path parameters by generating standard parameter definitions.
    """

    rule_id = RuleId.MISSING_PATH_PARAMETER
    default_severity = Severity.ERROR
    description = "Checks that all URL template variables have matching required path parameter definitions."

    def handles_rule_id(self, rule_id: str) -> bool:
        return rule_id in (
            RuleId.MISSING_PATH_PARAMETER,
            RuleId.UNUSED_PATH_PARAMETER,
        )

    def check(self, spec: ParsedSpec, context: Dict[str, Any]) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []
        paths = spec.data.get("paths")
        if not isinstance(paths, dict):
            return diagnostics

        for path_template, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            template_param_names = set(PATH_PARAM_REGEX.findall(path_template))

            # Parameters declared at path-item level
            path_level_params = path_item.get("parameters")
            path_level_path_params: Set[str] = set()
            if isinstance(path_level_params, list):
                for p in path_level_params:
                    if isinstance(p, dict) and p.get("in") == "path":
                        name = p.get("name")
                        if isinstance(name, str):
                            path_level_path_params.add(name)

            for method in ("get", "post", "put", "delete", "patch", "options", "head", "trace"):
                op = path_item.get(method)
                if not isinstance(op, dict):
                    continue

                op_pointer = f"/paths/{escape_pointer_token(path_template)}/{method}"
                op_params = op.get("parameters")
                op_level_path_params: Set[str] = set()

                if isinstance(op_params, list):
                    for idx, p in enumerate(op_params):
                        if isinstance(p, dict) and p.get("in") == "path":
                            name = p.get("name")
                            if isinstance(name, str):
                                op_level_path_params.add(name)
                                # Check 2: in: path must have required: true
                                if p.get("required") is not True:
                                    param_ptr = f"{op_pointer}/parameters/{idx}/required"
                                    line, col = spec.get_location(param_ptr)
                                    diagnostics.append(
                                        Diagnostic(
                                            rule_id=RuleId.MISSING_PATH_PARAMETER,
                                            message=f"Path parameter '{name}' in '{method.upper()} {path_template}' must have 'required: true'.",
                                            severity=Severity.ERROR,
                                            pointer=param_ptr,
                                            line=line,
                                            column=col,
                                            fixable=True,
                                            fix_action=FixAction(
                                                rule_id=RuleId.MISSING_PATH_PARAMETER,
                                                description=f"Set required: true for path parameter '{name}' in {method.upper()} {path_template}",
                                                target_pointer=param_ptr,
                                                action_type="set",
                                                value=True,
                                            ),
                                            suggestion="Set 'required: true'",
                                        )
                                    )

                all_declared_path_params = path_level_path_params | op_level_path_params

                # Check 1: Missing path parameters
                for missing_name in template_param_names - all_declared_path_params:
                    line, col = spec.get_location(op_pointer)
                    param_def = {
                        "name": missing_name,
                        "in": "path",
                        "required": True,
                        "description": f"Parameter '{missing_name}'",
                        "schema": {"type": "string"},
                    }
                    target_ptr = f"{op_pointer}/parameters"

                    fix_action = FixAction(
                        rule_id=RuleId.MISSING_PATH_PARAMETER,
                        description=f"Add missing path parameter '{missing_name}' to {method.upper()} {path_template}",
                        target_pointer=target_ptr,
                        action_type="append",
                        value=param_def,
                    )

                    diagnostics.append(
                        Diagnostic(
                            rule_id=RuleId.MISSING_PATH_PARAMETER,
                            message=f"Missing path parameter definition for '{{{missing_name}}}' in '{method.upper()} {path_template}'.",
                            severity=Severity.ERROR,
                            pointer=op_pointer,
                            line=line,
                            column=col,
                            fixable=True,
                            fix_action=fix_action,
                            suggestion=f"Add parameter definition for '{missing_name}' with in: path",
                        )
                    )

                # Check 3: Unused path parameters declared on operation
                for declared_name in op_level_path_params:
                    if declared_name not in template_param_names:
                        line, col = spec.get_location(op_pointer)
                        diagnostics.append(
                            Diagnostic(
                                rule_id=RuleId.UNUSED_PATH_PARAMETER,
                                message=f"Path parameter '{declared_name}' declared in '{method.upper()} {path_template}' does not exist in URL template.",
                                severity=Severity.WARNING,
                                pointer=op_pointer,
                                line=line,
                                column=col,
                                fixable=False,
                                suggestion=f"Remove parameter '{declared_name}' or add '{{{declared_name}}}' to URL template",
                            )
                        )

        return diagnostics
