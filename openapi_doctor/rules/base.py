"""Base rule interface and utilities for openapi-doctor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional, Tuple

from openapi_doctor.models import Diagnostic, FixAction, Severity
from openapi_doctor.parser import (
    ParsedSpec,
    escape_pointer_token,
    pointer_to_tokens,
    resolve_pointer,
    tokens_to_pointer,
)

HTTP_METHODS = ("get", "post", "put", "delete", "patch", "options", "head", "trace")

STANDARD_HTTP_STATUS_DESCRIPTIONS: Dict[str, str] = {
    "100": "Continue",
    "101": "Switching Protocols",
    "200": "OK",
    "201": "Created",
    "202": "Accepted",
    "203": "Non-Authoritative Information",
    "204": "No Content",
    "205": "Reset Content",
    "206": "Partial Content",
    "300": "Multiple Choices",
    "301": "Moved Permanently",
    "302": "Found",
    "303": "See Other",
    "304": "Not Modified",
    "307": "Temporary Redirect",
    "308": "Permanent Redirect",
    "400": "Bad Request",
    "401": "Unauthorized",
    "402": "Payment Required",
    "403": "Forbidden",
    "404": "Not Found",
    "405": "Method Not Allowed",
    "406": "Not Acceptable",
    "408": "Request Timeout",
    "409": "Conflict",
    "410": "Gone",
    "415": "Unsupported Media Type",
    "422": "Unprocessable Entity",
    "429": "Too Many Requests",
    "500": "Internal Server Error",
    "501": "Not Implemented",
    "502": "Bad Gateway",
    "503": "Service Unavailable",
    "504": "Gateway Timeout",
    "default": "Default response",
}


def get_default_status_description(code: str) -> str:
    """Returns standard description for an HTTP status code or wildcard."""
    code_str = str(code).strip()
    if code_str in STANDARD_HTTP_STATUS_DESCRIPTIONS:
        return STANDARD_HTTP_STATUS_DESCRIPTIONS[code_str]
    if code_str.upper() == "2XX":
        return "Successful response"
    if code_str.upper() == "3XX":
        return "Redirection response"
    if code_str.upper() == "4XX":
        return "Client error"
    if code_str.upper() == "5XX":
        return "Server error"
    if code_str.isdigit():
        num = int(code_str)
        if 200 <= num < 300:
            return f"Successful operation ({code_str})"
        elif 400 <= num < 500:
            return f"Client error ({code_str})"
        elif 500 <= num < 600:
            return f"Server error ({code_str})"
    return f"Response for status {code_str}"


def iter_operations(doc: Dict[str, Any]) -> Iterator[Tuple[str, str, Dict[str, Any], str]]:
    """
    Yields (path, method, operation_dict, pointer) for each operation in doc.
    Example pointer: /paths/~1users~1{id}/get
    """
    paths = doc.get("paths")
    if not isinstance(paths, dict):
        return

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if isinstance(operation, dict):
                pointer = f"/paths/{escape_pointer_token(path)}/{method}"
                yield path, method, operation, pointer


class BaseRule(ABC):
    """Abstract base class for all OpenAPI doctor lint and autofix rules."""

    rule_id: str
    default_severity: Severity
    description: str
    is_fixable: bool = True

    @abstractmethod
    def check(self, spec: ParsedSpec, context: Dict[str, Any]) -> List[Diagnostic]:
        """Runs the rule check against the spec and returns discovered diagnostics."""
        raise NotImplementedError

    def handles_rule_id(self, rule_id: str) -> bool:
        """Returns True if this rule handles diagnostics for rule_id."""
        return rule_id == self.rule_id

    def fix(self, spec: ParsedSpec, diagnostics: List[Diagnostic]) -> int:
        """
        Applies autofixes for this rule directly to `spec.data`.
        Returns number of fixes successfully applied.
        """
        fixes_applied = 0
        for diag in diagnostics:
            if not self.handles_rule_id(diag.rule_id) or not diag.fixable or not diag.fix_action:
                continue
            if self.apply_action(spec.data, diag.fix_action):
                fixes_applied += 1
        return fixes_applied

    def apply_action(self, doc: Dict[str, Any], action: FixAction) -> bool:
        """Applies an atomic fix action to doc."""
        tokens = pointer_to_tokens(action.target_pointer)
        if not tokens:
            return False

        if action.action_type == "set":
            curr = doc
            for token in tokens[:-1]:
                if isinstance(curr, list):
                    try:
                        curr = curr[int(token)]
                    except (ValueError, IndexError):
                        return False
                elif isinstance(curr, dict):
                    if token not in curr or not isinstance(curr[token], (dict, list)):
                        curr[token] = {}
                    curr = curr[token]
                else:
                    return False

            if isinstance(curr, list):
                try:
                    curr[int(tokens[-1])] = action.value
                    return True
                except (ValueError, IndexError):
                    return False
            elif isinstance(curr, dict):
                curr[tokens[-1]] = action.value
                return True
            return False

        elif action.action_type == "delete":
            curr = doc
            for token in tokens[:-1]:
                if isinstance(curr, list):
                    try:
                        curr = curr[int(token)]
                    except (ValueError, IndexError):
                        return False
                elif isinstance(curr, dict):
                    if token not in curr or not isinstance(curr[token], (dict, list)):
                        return False
                    curr = curr[token]
                else:
                    return False

            if isinstance(curr, list):
                try:
                    del curr[int(tokens[-1])]
                    return True
                except (ValueError, IndexError):
                    return False
            elif isinstance(curr, dict):
                if tokens[-1] in curr:
                    del curr[tokens[-1]]
                    return True
            return False

        elif action.action_type == "append":
            curr = doc
            for token in tokens[:-1]:
                if isinstance(curr, list):
                    try:
                        curr = curr[int(token)]
                    except (ValueError, IndexError):
                        return False
                elif isinstance(curr, dict):
                    if token not in curr or not isinstance(curr[token], (dict, list)):
                        curr[token] = {}
                    curr = curr[token]
                else:
                    return False

            if isinstance(curr, dict):
                target_list = curr.get(tokens[-1])
                if target_list is None:
                    curr[tokens[-1]] = [action.value]
                    return True
                elif isinstance(target_list, list):
                    target_list.append(action.value)
                    return True
            elif isinstance(curr, list):
                curr.append(action.value)
                return True
            return False

        elif action.action_type == "merge":
            curr = doc
            for token in tokens[:-1]:
                if isinstance(curr, list):
                    try:
                        curr = curr[int(token)]
                    except (ValueError, IndexError):
                        return False
                elif isinstance(curr, dict):
                    if token not in curr or not isinstance(curr[token], (dict, list)):
                        curr[token] = {}
                    curr = curr[token]
                else:
                    return False

            if isinstance(curr, dict):
                target_dict = curr.get(tokens[-1])
                if target_dict is None:
                    curr[tokens[-1]] = dict(action.value)
                    return True
                elif isinstance(target_dict, dict):
                    target_dict.update(action.value)
                    return True
            return False

        return False
