"""Reporters for openapi-doctor output formatting."""

from __future__ import annotations

import json
import sys
from typing import List, Optional

from openapi_doctor.models import Diagnostic, FixResult, LintResult, Severity

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
WHITE = "\033[37m"


def can_encode_unicode() -> bool:
    """Checks whether stdout can safely encode UTF-8 characters."""
    for stream in (sys.stdout, getattr(sys, "__stdout__", None)):
        if stream is None:
            continue
        encoding = getattr(stream, "encoding", None) or "ascii"
        try:
            "\u2716\u2714\u26a0\u2139\u21b3\u2022".encode(encoding)
        except (UnicodeEncodeError, LookupError):
            return False
    return True


def supports_color() -> bool:
    """Check if stdout supports ANSI colors."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def format_text_report(results: List[LintResult], color: bool = True) -> str:
    """Formats lint results for terminal display."""
    lines: List[str] = []

    c_red = RED if color else ""
    c_yellow = YELLOW if color else ""
    c_cyan = CYAN if color else ""
    c_green = GREEN if color else ""
    c_bold = BOLD if color else ""
    c_dim = DIM if color else ""
    c_reset = RESET if color else ""

    unicode_ok = can_encode_unicode()
    icon_err = "\u2716" if unicode_ok else "X"
    icon_warn = "\u26a0" if unicode_ok else "!"
    icon_info = "\u2139" if unicode_ok else "i"
    icon_ok = "\u2714" if unicode_ok else "OK"
    icon_arrow = "\u21b3" if unicode_ok else "->"
    bullet = "\u2022" if unicode_ok else "*"

    total_errors = sum(r.error_count for r in results)
    total_warnings = sum(r.warning_count for r in results)
    total_infos = sum(r.info_count for r in results)
    total_fixable = sum(r.fixable_count for r in results)

    for result in results:
        if result.parse_error:
            lines.append(f"\n{c_bold}{result.file_path}{c_reset}")
            lines.append(f"  {c_red}{icon_err} Parse error:{c_reset} {result.parse_error}")
            continue

        if not result.diagnostics:
            continue

        lines.append(f"\n{c_bold}{result.file_path}{c_reset}")
        for diag in result.diagnostics:
            if diag.severity == Severity.ERROR:
                badge = f"{c_red}{icon_err} error  {c_reset}"
            elif diag.severity == Severity.WARNING:
                badge = f"{c_yellow}{icon_warn} warning{c_reset}"
            else:
                badge = f"{c_cyan}{icon_info} info   {c_reset}"

            loc_str = ""
            if diag.line is not None:
                loc_str = f"{diag.line}:{diag.column or 1}"
            loc_formatted = f"{c_dim}{loc_str:>8}{c_reset} " if loc_str else "         "

            fix_tag = f" {c_green}[fixable]{c_reset}" if diag.fixable else ""
            rule_tag = f" {c_dim}({diag.rule_id}){c_reset}"

            lines.append(f"  {loc_formatted} {badge} {diag.message}{fix_tag}{rule_tag}")
            if diag.suggestion:
                lines.append(f"             {c_dim}{icon_arrow} Suggestion: {diag.suggestion}{c_reset}")

    # Summary bar
    lines.append("")
    if total_errors == 0 and total_warnings == 0:
        lines.append(f"{c_green}{icon_ok} No issues found! Specification is healthy.{c_reset}")
    else:
        parts = []
        if total_errors > 0:
            parts.append(f"{c_red}{total_errors} error{'s' if total_errors > 1 else ''}{c_reset}")
        if total_warnings > 0:
            parts.append(f"{c_yellow}{total_warnings} warning{'s' if total_warnings > 1 else ''}{c_reset}")
        if total_infos > 0:
            parts.append(f"{c_cyan}{total_infos} info{c_reset}")

        summary = f"{icon_err} Found {', '.join(parts)}"
        if total_fixable > 0:
            summary += f" ({c_green}{total_fixable} automatically fixable with 'openapi-doctor fix'{c_reset})"
        lines.append(summary)

    return "\n".join(lines)


def format_json_report(results: List[LintResult]) -> str:
    """Formats lint results as structured JSON."""
    data = {
        "summary": {
            "total_files": len(results),
            "healthy_files": sum(1 for r in results if r.is_valid and r.warning_count == 0),
            "total_errors": sum(r.error_count for r in results),
            "total_warnings": sum(r.warning_count for r in results),
            "total_infos": sum(r.info_count for r in results),
            "total_fixable": sum(r.fixable_count for r in results),
        },
        "results": [r.to_dict() for r in results],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def format_github_report(results: List[LintResult]) -> str:
    """Formats diagnostics as GitHub Actions workflow commands."""
    lines: List[str] = []
    for result in results:
        for diag in result.diagnostics:
            cmd = "error" if diag.severity == Severity.ERROR else "warning"
            file_arg = f"file={result.file_path}"
            line_arg = f",line={diag.line}" if diag.line else ""
            col_arg = f",col={diag.column}" if diag.column else ""
            title_arg = f",title={diag.rule_id}"
            lines.append(f"::{cmd} {file_arg}{line_arg}{col_arg}{title_arg}::{diag.message}")
    return "\n".join(lines)


def format_markdown_report(results: List[LintResult]) -> str:
    """Formats lint results as a Markdown table and summary."""
    lines: List[str] = ["# OpenAPI Doctor Report\n"]

    total_errors = sum(r.error_count for r in results)
    total_warnings = sum(r.warning_count for r in results)
    total_fixable = sum(r.fixable_count for r in results)

    lines.append("| File | Status | Errors | Warnings | Fixable |")
    lines.append("| :--- | :---: | :---: | :---: | :---: |")

    for r in results:
        status = "Clean" if r.is_valid and r.warning_count == 0 else ("Failed" if r.error_count > 0 else "Warnings")
        lines.append(f"| `{r.file_path}` | {status} | {r.error_count} | {r.warning_count} | {r.fixable_count} |")

    lines.append(f"\n**Total**: {total_errors} errors, {total_warnings} warnings ({total_fixable} fixable).\n")

    for r in results:
        if not r.diagnostics:
            continue
        lines.append(f"### Diagnostics for `{r.file_path}`\n")
        lines.append("| Severity | Rule | Location | Message | Suggestion |")
        lines.append("| :---: | :--- | :---: | :--- | :--- |")
        for d in r.diagnostics:
            sev_icon = "Error" if d.severity == Severity.ERROR else "Warning"
            loc = f"L{d.line}:{d.column}" if d.line else d.pointer
            sugg = d.suggestion or "-"
            lines.append(f"| {sev_icon} | `{d.rule_id}` | `{loc}` | {d.message} | {sugg} |")
        lines.append("")

    return "\n".join(lines)


def format_fix_report(results: List[FixResult], color: bool = True) -> str:
    """Formats fix results for terminal output."""
    lines: List[str] = []
    c_green = GREEN if color else ""
    c_red = RED if color else ""
    c_yellow = YELLOW if color else ""
    c_bold = BOLD if color else ""
    c_dim = DIM if color else ""
    c_reset = RESET if color else ""

    unicode_ok = can_encode_unicode()
    icon_ok = "\u2714" if unicode_ok else "OK"
    icon_arrow = "\u21b3" if unicode_ok else "->"
    bullet = "\u2022" if unicode_ok else "*"

    for res in results:
        lines.append(f"\n{c_bold}{res.file_path}{c_reset}")
        if res.backup_path:
            lines.append(f"  {c_dim}{icon_arrow} Created backup at {res.backup_path}{c_reset}")
        if res.dry_run:
            lines.append(f"  {c_yellow}[DRY RUN]{c_reset} Planned {res.fixes_applied} fixes:")
        else:
            lines.append(f"  {c_green}{icon_ok} Applied {res.fixes_applied} fixes:{c_reset}")

        for fix in res.fixes:
            lines.append(f"    {bullet} {fix.description} ({c_dim}{fix.rule_id}{c_reset})")

        if res.remaining_diagnostics:
            rem_err = sum(1 for d in res.remaining_diagnostics if d.severity == Severity.ERROR)
            rem_warn = sum(1 for d in res.remaining_diagnostics if d.severity == Severity.WARNING)
            lines.append(f"  {c_yellow}Remaining issues:{c_reset} {rem_err} errors, {rem_warn} warnings (require manual inspection)")
        else:
            lines.append(f"  {c_green}All detected issues resolved successfully!{c_reset}")

    return "\n".join(lines)
