"""openapi-doctor: Production-grade OpenAPI 3.0 & 3.1 specification linter and autofixer."""

from openapi_doctor.config import Config, load_config
from openapi_doctor.fixer import apply_fixes
from openapi_doctor.linter import lint_file, lint_paths, lint_spec
from openapi_doctor.models import (
    Diagnostic,
    FixAction,
    FixResult,
    LintResult,
    RuleId,
    Severity,
)
from openapi_doctor.parser import ParsedSpec, load_spec_file, load_spec_from_text

__version__ = "1.0.0"

__all__ = [
    "lint_file",
    "lint_paths",
    "lint_spec",
    "apply_fixes",
    "Diagnostic",
    "FixAction",
    "FixResult",
    "LintResult",
    "RuleId",
    "Severity",
    "ParsedSpec",
    "load_spec_file",
    "load_spec_from_text",
    "Config",
    "load_config",
    "__version__",
]
