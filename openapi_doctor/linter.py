"""Core linter engine for openapi-doctor."""

from __future__ import annotations

import glob
import os
from typing import List, Optional

from openapi_doctor.config import Config, load_config
from openapi_doctor.models import LintResult, Severity
from openapi_doctor.parser import ParsedSpec, load_spec_file
from openapi_doctor.rules import DEFAULT_RULES, BaseRule


def find_spec_files(target_paths: List[str]) -> List[str]:
    """Expands directories, files, and glob patterns to a sorted list of spec paths."""
    discovered: List[str] = []
    supported_extensions = (".yaml", ".yml", ".json")

    for target in target_paths:
        if os.path.isfile(target):
            discovered.append(os.path.abspath(target))
        elif os.path.isdir(target):
            for root, _, files in os.walk(target):
                for f in files:
                    if f.lower().endswith(supported_extensions):
                        discovered.append(os.path.abspath(os.path.join(root, f)))
        elif any(c in target for c in ("*", "?", "[")):
            matched = glob.glob(target, recursive=True)
            for m in matched:
                if os.path.isfile(m) and m.lower().endswith(supported_extensions):
                    discovered.append(os.path.abspath(m))

    return sorted(list(set(discovered)))


def lint_spec(
    spec: ParsedSpec,
    rules: Optional[List[BaseRule]] = None,
    config: Optional[Config] = None,
) -> LintResult:
    """Lints a parsed OpenAPI specification using the given rules and configuration."""
    cfg = config or Config()
    active_rules = rules if rules is not None else DEFAULT_RULES

    result = LintResult(
        file_path=spec.file_path,
        openapi_version=spec.openapi_version,
    )

    context = {"config": cfg}

    for rule in active_rules:
        if not cfg.is_rule_enabled(rule.rule_id):
            continue

        rule_diagnostics = rule.check(spec, context)
        for diag in rule_diagnostics:
            # Check for config severity overrides
            diag.severity = cfg.get_rule_severity(diag.rule_id, diag.severity)
            result.diagnostics.append(diag)

    # Sort diagnostics by line and column
    result.diagnostics.sort(key=lambda d: (d.line or 0, d.column or 0, -d.severity.rank))
    return result


def lint_file(
    file_path: str,
    rules: Optional[List[BaseRule]] = None,
    config: Optional[Config] = None,
) -> LintResult:
    """Loads and lints a single OpenAPI specification file."""
    try:
        spec = load_spec_file(file_path)
    except Exception as err:
        return LintResult(
            file_path=file_path,
            parse_error=str(err),
        )

    return lint_spec(spec, rules=rules, config=config)


def lint_paths(
    paths: List[str],
    rules: Optional[List[BaseRule]] = None,
    config: Optional[Config] = None,
) -> List[LintResult]:
    """Discovers and lints all specification files under the provided paths."""
    spec_files = find_spec_files(paths)
    if not spec_files:
        return []

    return [lint_file(p, rules=rules, config=config) for p in spec_files]
