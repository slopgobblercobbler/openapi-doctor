"""Autofix engine for openapi-doctor."""

from __future__ import annotations

import os
import shutil
from typing import List, Optional, Set

from openapi_doctor.config import Config
from openapi_doctor.linter import lint_spec
from openapi_doctor.models import FixAction, FixResult, LintResult
from openapi_doctor.parser import ParsedSpec, load_spec_file, load_spec_from_text
from openapi_doctor.rules import DEFAULT_RULES, RULE_REGISTRY, BaseRule


def apply_fixes(
    file_path: str,
    output_path: Optional[str] = None,
    rule_ids: Optional[List[str]] = None,
    dry_run: bool = False,
    backup: bool = False,
    config: Optional[Config] = None,
    max_iterations: int = 3,
) -> FixResult:
    """
    Applies automated fixes to an OpenAPI specification file.

    Parameters:
        file_path: Target OpenAPI file
        output_path: Destination for fixed file (defaults to file_path for in-place)
        rule_ids: Optional list of specific rule IDs to fix
        dry_run: If True, simulates fixes without writing to disk
        backup: If True, saves original file to .bak before overwriting
        config: Optional configuration
        max_iterations: Max iterations of lint -> fix cycle (handles chained dependencies)
    """
    spec = load_spec_file(file_path)
    target_output = output_path or file_path

    allowed_rule_ids: Optional[Set[str]] = set(rule_ids) if rule_ids else None
    all_applied_fixes: List[FixAction] = []
    backup_file_path: Optional[str] = None

    for _ in range(max_iterations):
        lint_res = lint_spec(spec, rules=DEFAULT_RULES, config=config)
        iteration_applied = 0

        # Filter fixable diagnostics
        fixable_diags = [
            d for d in lint_res.diagnostics
            if d.fixable and d.fix_action is not None
            and (allowed_rule_ids is None or d.rule_id in allowed_rule_ids)
        ]

        if not fixable_diags:
            break

        for diag in fixable_diags:
            action = diag.fix_action
            if not action:
                continue

            rule = RULE_REGISTRY.get(diag.rule_id)
            if rule and rule.apply_action(spec.data, action):
                all_applied_fixes.append(action)
                iteration_applied += 1

        if iteration_applied == 0:
            break

    # Re-lint after all fixes to check remaining issues
    final_lint = lint_spec(spec, rules=DEFAULT_RULES, config=config)

    if not dry_run and all_applied_fixes:
        # Create backup if requested
        if backup and os.path.exists(file_path):
            backup_file_path = f"{file_path}.bak"
            shutil.copy2(file_path, backup_file_path)

        # Ensure output directory exists
        out_dir = os.path.dirname(os.path.abspath(target_output))
        os.makedirs(out_dir, exist_ok=True)

        with open(target_output, "w", encoding="utf-8") as f:
            f.write(spec.serialize())

    return FixResult(
        file_path=file_path,
        output_path=target_output,
        fixes_applied=len(all_applied_fixes),
        fixes=all_applied_fixes,
        remaining_diagnostics=final_lint.diagnostics,
        dry_run=dry_run,
        backup_path=backup_file_path,
    )
