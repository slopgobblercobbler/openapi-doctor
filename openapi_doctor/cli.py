"""Command line interface for openapi-doctor."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from openapi_doctor import __version__
from openapi_doctor.config import load_config
from openapi_doctor.fixer import apply_fixes
from openapi_doctor.linter import find_spec_files, lint_file
from openapi_doctor.models import Severity
from openapi_doctor.reporter import (
    format_fix_report,
    format_github_report,
    format_json_report,
    format_markdown_report,
    format_text_report,
    supports_color,
)


def create_parser() -> argparse.ArgumentParser:
    """Creates the root argument parser for openapi-doctor."""
    parser = argparse.ArgumentParser(
        prog="openapi-doctor",
        description="Production-grade OpenAPI 3.0 & 3.1 specification linter and automated autofixer.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: check
    check_parser = subparsers.add_parser(
        "check",
        help="Check and lint OpenAPI specifications for errors and anti-patterns.",
    )
    _add_lint_arguments(check_parser)

    # Command: lint (alias of check)
    lint_parser = subparsers.add_parser(
        "lint",
        help="Alias for 'check'. Lints specification files with custom formatting.",
    )
    _add_lint_arguments(lint_parser)

    # Command: fix
    fix_parser = subparsers.add_parser(
        "fix",
        help="Automatically repair missing response descriptions, undefined schemas, and more.",
    )
    fix_parser.add_argument(
        "paths",
        nargs="+",
        help="Path(s) to OpenAPI YAML or JSON specification files, or directories.",
    )
    fix_parser.add_argument(
        "-o",
        "--output",
        help="Destination path for fixed specification. If omitted, performs in-place edit.",
    )
    fix_parser.add_argument(
        "--in-place",
        action="store_true",
        default=True,
        help="Modify files directly in-place (default).",
    )
    fix_parser.add_argument(
        "-b",
        "--backup",
        action="store_true",
        help="Create a backup file (.bak) before modifying original file.",
    )
    fix_parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Simulate autofixes without writing changes to disk.",
    )
    fix_parser.add_argument(
        "-r",
        "--rules",
        help="Comma-separated list of rule IDs to fix (e.g. missing-response-description,broken-ref).",
    )
    fix_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    fix_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colorized terminal output.",
    )
    fix_parser.add_argument(
        "-c",
        "--config",
        help="Path to custom configuration file.",
    )

    return parser


def _add_lint_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "paths",
        nargs="+",
        help="Path(s) to OpenAPI YAML or JSON specification files, or directories.",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["text", "json", "github", "markdown"],
        default="text",
        help="Output report format (default: text).",
    )
    parser.add_argument(
        "-s",
        "--strict",
        action="store_true",
        help="Strict mode: treat warnings as errors and exit with code 1.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colorized terminal output.",
    )
    parser.add_argument(
        "-c",
        "--config",
        help="Path to custom configuration file.",
    )


def handle_check(args: argparse.Namespace) -> int:
    """Handler for 'check' and 'lint' subcommands."""
    config = load_config(args.config)
    if args.strict:
        config.strict = True

    spec_files = find_spec_files(args.paths)
    if not spec_files:
        sys.stderr.write(f"Error: No OpenAPI specification files found matching: {', '.join(args.paths)}\n")
        return 2

    results = [lint_file(p, config=config) for p in spec_files]

    # Render report
    fmt = args.format or config.format or "text"
    use_color = not args.no_color and supports_color()

    if fmt == "json":
        print(format_json_report(results))
    elif fmt == "github":
        print(format_github_report(results))
    elif fmt == "markdown":
        print(format_markdown_report(results))
    else:
        print(format_text_report(results, color=use_color))

    # Exit code determination
    total_errors = sum(r.error_count for r in results)
    total_warnings = sum(r.warning_count for r in results)
    has_parse_error = any(r.parse_error for r in results)

    if has_parse_error:
        return 2
    if total_errors > 0:
        return 1
    if config.strict and total_warnings > 0:
        return 1

    return 0


def handle_fix(args: argparse.Namespace) -> int:
    """Handler for 'fix' subcommand."""
    config = load_config(args.config)
    spec_files = find_spec_files(args.paths)
    if not spec_files:
        sys.stderr.write(f"Error: No OpenAPI specification files found matching: {', '.join(args.paths)}\n")
        return 2

    if args.output and len(spec_files) > 1:
        sys.stderr.write("Error: --output can only be used with a single specification file.\n")
        return 2

    rule_filter = [r.strip() for r in args.rules.split(",")] if args.rules else None
    use_color = not args.no_color and supports_color()

    fix_results = []
    for file_path in spec_files:
        out_path = args.output if args.output else file_path
        res = apply_fixes(
            file_path=file_path,
            output_path=out_path,
            rule_ids=rule_filter,
            dry_run=args.dry_run,
            backup=args.backup,
            config=config,
        )
        fix_results.append(res)

    if args.format == "json":
        data = {
            "summary": {
                "total_files": len(fix_results),
                "total_fixes_applied": sum(r.fixes_applied for r in fix_results),
                "dry_run": args.dry_run,
            },
            "results": [r.to_dict() for r in fix_results],
        }
        print(json.dumps(data, indent=2))
    else:
        print(format_fix_report(fix_results, color=use_color))

    has_remaining_errors = any(
        any(d.severity == Severity.ERROR for d in r.remaining_diagnostics)
        for r in fix_results
    )

    return 1 if has_remaining_errors else 0


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for openapi-doctor CLI."""
    if argv is None:
        argv = sys.argv[1:]

    # Default to check if first argument is a file/path and not a subcommand
    if argv and not argv[0].startswith("-") and argv[0] not in ("check", "lint", "fix"):
        argv = ["check"] + argv

    parser = create_parser()

    if not argv:
        parser.print_help()
        return 0

    args = parser.parse_args(argv)

    if args.command in ("check", "lint"):
        return handle_check(args)
    elif args.command == "fix":
        return handle_fix(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
