"""Data models for openapi-doctor."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(str, Enum):
    """Diagnostic severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    def __str__(self) -> str:
        return self.value

    @property
    def rank(self) -> int:
        return {
            Severity.ERROR: 3,
            Severity.WARNING: 2,
            Severity.INFO: 1,
        }[self]


class RuleId:
    """Standard rule identifiers."""
    MISSING_RESPONSE_DESCRIPTION = "missing-response-description"
    BROKEN_REF = "broken-ref"
    UNDEFINED_SCHEMA = "undefined-schema"
    UNUSED_COMPONENT = "unused-component"
    MISSING_OPERATION_ID = "missing-operation-id"
    DUPLICATE_OPERATION_ID = "duplicate-operation-id"
    INVALID_OPERATION_ID = "invalid-operation-id"
    UNDEFINED_SECURITY_SCHEME = "undefined-security-scheme"
    INVALID_SECURITY_SCOPE = "invalid-security-scope"
    MISSING_PATH_PARAMETER = "missing-path-parameter"
    UNUSED_PATH_PARAMETER = "unused-path-parameter"


@dataclass
class FixAction:
    """Represents a discrete autofix operation."""
    rule_id: str
    description: str
    target_pointer: str  # JSON Pointer, e.g. /paths/~1users/get/responses/200/description
    action_type: str     # 'set', 'delete', 'append', 'merge'
    value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "target_pointer": self.target_pointer,
            "action_type": self.action_type,
            "value": self.value,
        }


@dataclass
class Diagnostic:
    """Represents an issue discovered by a linter rule."""
    rule_id: str
    message: str
    severity: Severity = Severity.ERROR
    pointer: str = ""       # JSON pointer path, e.g. /paths/~1users/get/responses/200
    line: Optional[int] = None
    column: Optional[int] = None
    fixable: bool = False
    fix_action: Optional[FixAction] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "message": self.message,
            "severity": str(self.severity),
            "pointer": self.pointer,
            "line": self.line,
            "column": self.column,
            "fixable": self.fixable,
            "fix_action": self.fix_action.to_dict() if self.fix_action else None,
            "suggestion": self.suggestion,
        }


@dataclass
class LintResult:
    """Result of linting a single OpenAPI specification file."""
    file_path: str
    openapi_version: Optional[str] = None
    diagnostics: List[Diagnostic] = field(default_factory=list)
    parse_error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        return self.parse_error is None and self.error_count == 0

    @property
    def error_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == Severity.INFO)

    @property
    def fixable_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.fixable)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "openapi_version": self.openapi_version,
            "is_valid": self.is_valid,
            "parse_error": self.parse_error,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "fixable_count": self.fixable_count,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


@dataclass
class FixResult:
    """Result of autofixing an OpenAPI specification file."""
    file_path: str
    output_path: str
    fixes_applied: int
    fixes: List[FixAction] = field(default_factory=list)
    remaining_diagnostics: List[Diagnostic] = field(default_factory=list)
    dry_run: bool = False
    backup_path: Optional[str] = None

    @property
    def is_fully_fixed(self) -> bool:
        return len(self.remaining_diagnostics) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "output_path": self.output_path,
            "fixes_applied": self.fixes_applied,
            "fixes": [f.to_dict() for f in self.fixes],
            "dry_run": self.dry_run,
            "backup_path": self.backup_path,
            "is_fully_fixed": self.is_fully_fixed,
            "remaining_error_count": sum(1 for d in self.remaining_diagnostics if d.severity == Severity.ERROR),
            "remaining_warning_count": sum(1 for d in self.remaining_diagnostics if d.severity == Severity.WARNING),
        }
