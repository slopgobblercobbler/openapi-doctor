"""Rule to detect and autofix missing or empty response descriptions."""

from __future__ import annotations

from typing import Any, Dict, List

from openapi_doctor.models import Diagnostic, FixAction, RuleId, Severity
from openapi_doctor.parser import ParsedSpec, escape_pointer_token
from openapi_doctor.rules.base import (
    BaseRule,
    get_default_status_description,
    iter_operations,
)


class MissingResponseDescriptionRule(BaseRule):
    """
    Checks that every response definition contains a non-empty `description`.
    OpenAPI 3.0 & 3.1 require `description` on all response objects (unless $ref).
    """

    rule_id = RuleId.MISSING_RESPONSE_DESCRIPTION
    default_severity = Severity.ERROR
    description = "Response object is missing a required non-empty 'description' field."

    def check(self, spec: ParsedSpec, context: Dict[str, Any]) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []

        for path, method, operation, op_pointer in iter_operations(spec.data):
            responses = operation.get("responses")
            if not isinstance(responses, dict):
                continue

            for status_code, response_obj in responses.items():
                if not isinstance(response_obj, dict):
                    continue

                # If response is a $ref, the target object contains the description
                if "$ref" in response_obj:
                    continue

                desc = response_obj.get("description")
                resp_pointer = f"{op_pointer}/responses/{escape_pointer_token(str(status_code))}"
                desc_pointer = f"{resp_pointer}/description"

                if desc is None or (isinstance(desc, str) and not desc.strip()):
                    line, col = spec.get_location(resp_pointer)
                    suggested_desc = get_default_status_description(str(status_code))

                    fix_action = FixAction(
                        rule_id=self.rule_id,
                        description=f"Add description '{suggested_desc}' to {method.upper()} {path} response {status_code}",
                        target_pointer=desc_pointer,
                        action_type="set",
                        value=suggested_desc,
                    )

                    diagnostics.append(
                        Diagnostic(
                            rule_id=self.rule_id,
                            message=f"Response {status_code} in '{method.upper()} {path}' is missing required 'description'.",
                            severity=self.default_severity,
                            pointer=desc_pointer,
                            line=line,
                            column=col,
                            fixable=True,
                            fix_action=fix_action,
                            suggestion=f"Set description to '{suggested_desc}'",
                        )
                    )

        # Also check components/responses if defined
        components = spec.data.get("components")
        if isinstance(components, dict):
            comp_responses = components.get("responses")
            if isinstance(comp_responses, dict):
                for resp_name, resp_obj in comp_responses.items():
                    if not isinstance(resp_obj, dict) or "$ref" in resp_obj:
                        continue
                    desc = resp_obj.get("description")
                    resp_pointer = f"/components/responses/{escape_pointer_token(resp_name)}"
                    desc_pointer = f"{resp_pointer}/description"

                    if desc is None or (isinstance(desc, str) and not desc.strip()):
                        line, col = spec.get_location(resp_pointer)
                        suggested_desc = f"Response {resp_name}"

                        fix_action = FixAction(
                            rule_id=self.rule_id,
                            description=f"Add description to reusable response component '{resp_name}'",
                            target_pointer=desc_pointer,
                            action_type="set",
                            value=suggested_desc,
                        )

                        diagnostics.append(
                            Diagnostic(
                                rule_id=self.rule_id,
                                message=f"Component response '{resp_name}' is missing required 'description'.",
                                severity=self.default_severity,
                                pointer=desc_pointer,
                                line=line,
                                column=col,
                                fixable=True,
                                fix_action=fix_action,
                                suggestion=f"Set description to '{suggested_desc}'",
                            )
                        )

        return diagnostics
