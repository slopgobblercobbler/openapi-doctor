"""Tests for openapi_doctor.reporter."""

import json
from openapi_doctor.models import Diagnostic, FixAction, FixResult, LintResult, Severity
from openapi_doctor.reporter import (
    can_encode_unicode,
    format_fix_report,
    format_github_report,
    format_json_report,
    format_markdown_report,
    format_text_report,
    supports_color,
)


def test_reporter_helpers():
    # Should run without error
    _ = can_encode_unicode()
    _ = supports_color()


def test_format_text_report_clean():
    res = LintResult(file_path="api.yaml", openapi_version="3.0.0")
    out = format_text_report([res], color=False)
    assert "No issues found" in out


def test_format_text_report_with_issues():
    d1 = Diagnostic(
        rule_id="r1",
        message="Missing description",
        severity=Severity.ERROR,
        line=12,
        column=4,
        fixable=True,
        suggestion="Add OK description",
    )
    d2 = Diagnostic(
        rule_id="r2",
        message="Unused parameter",
        severity=Severity.WARNING,
        line=20,
        column=2,
    )
    d3 = Diagnostic(
        rule_id="r3",
        message="Info note",
        severity=Severity.INFO,
    )
    res = LintResult(file_path="api.yaml", diagnostics=[d1, d2, d3])
    out = format_text_report([res], color=False)

    assert "api.yaml" in out
    assert "Missing description" in out
    assert "Unused parameter" in out
    assert "Info note" in out
    assert "[fixable]" in out
    assert "Suggestion: Add OK description" in out
    assert "1 error, 1 warning, 1 info (1 automatically fixable" in out


def test_format_text_report_parse_error():
    res = LintResult(file_path="bad.yaml", parse_error="Invalid YAML indentation")
    out = format_text_report([res], color=False)
    assert "Parse error: Invalid YAML indentation" in out


def test_format_json_report():
    d = Diagnostic(rule_id="r1", message="Err", severity=Severity.ERROR, line=5)
    res = LintResult(file_path="api.yaml", diagnostics=[d])
    out = format_json_report([res])

    parsed = json.loads(out)
    assert parsed["summary"]["total_files"] == 1
    assert parsed["summary"]["total_errors"] == 1
    assert len(parsed["results"]) == 1
    assert parsed["results"][0]["file_path"] == "api.yaml"


def test_format_github_report():
    d1 = Diagnostic(rule_id="rule-err", message="Fatal issue", severity=Severity.ERROR, line=10, column=5)
    d2 = Diagnostic(rule_id="rule-warn", message="Warning issue", severity=Severity.WARNING, line=20)
    res = LintResult(file_path="api.yaml", diagnostics=[d1, d2])
    out = format_github_report([res])

    lines = out.splitlines()
    assert len(lines) == 2
    assert "::error file=api.yaml,line=10,col=5,title=rule-err::Fatal issue" in lines[0]
    assert "::warning file=api.yaml,line=20,title=rule-warn::Warning issue" in lines[1]


def test_format_markdown_report():
    d = Diagnostic(
        rule_id="rule-err",
        message="Some issue",
        severity=Severity.ERROR,
        line=10,
        column=2,
        suggestion="Fix it",
    )
    res = LintResult(file_path="api.yaml", diagnostics=[d])
    out = format_markdown_report([res])

    assert "# OpenAPI Doctor Report" in out
    assert "| `api.yaml` |" in out
    assert "| Error | `rule-err` | `L10:2` | Some issue | Fix it |" in out


def test_format_fix_report():
    action = FixAction(
        rule_id="missing-response-description",
        description="Add description",
        target_pointer="/paths",
        action_type="set",
    )
    res = FixResult(
        file_path="spec.yaml",
        output_path="spec.yaml",
        fixes_applied=1,
        fixes=[action],
        backup_path="spec.yaml.bak",
        remaining_diagnostics=[],
    )
    out = format_fix_report([res], color=False)
    assert "spec.yaml" in out
    assert "Created backup at spec.yaml.bak" in out
    assert "Applied 1 fixes:" in out
    assert "All detected issues resolved successfully!" in out

    # Dry run with remaining issues
    diag_rem = Diagnostic(rule_id="other", message="rem", severity=Severity.ERROR)
    res_dry = FixResult(
        file_path="spec2.yaml",
        output_path="spec2.yaml",
        fixes_applied=1,
        fixes=[action],
        remaining_diagnostics=[diag_rem],
        dry_run=True,
    )
    out_dry = format_fix_report([res_dry], color=False)
    assert "[DRY RUN] Planned 1 fixes:" in out_dry
    assert "Remaining issues: 1 errors, 0 warnings (require manual inspection)" in out_dry
