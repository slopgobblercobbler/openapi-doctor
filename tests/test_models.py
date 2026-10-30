"""Tests for openapi_doctor.models."""

import pytest
from openapi_doctor.models import (
    Diagnostic,
    FixAction,
    FixResult,
    LintResult,
    RuleId,
    Severity,
)


def test_severity_enum_and_rank():
    assert str(Severity.ERROR) == "error"
    assert str(Severity.WARNING) == "warning"
    assert str(Severity.INFO) == "info"
    assert Severity.ERROR.rank == 3
    assert Severity.WARNING.rank == 2
    assert Severity.INFO.rank == 1


def test_rule_id_constants():
    assert RuleId.MISSING_RESPONSE_DESCRIPTION == "missing-response-description"
    assert RuleId.BROKEN_REF == "broken-ref"
    assert RuleId.UNDEFINED_SCHEMA == "undefined-schema"
    assert RuleId.UNUSED_COMPONENT == "unused-component"
    assert RuleId.MISSING_OPERATION_ID == "missing-operation-id"
    assert RuleId.DUPLICATE_OPERATION_ID == "duplicate-operation-id"
    assert RuleId.INVALID_OPERATION_ID == "invalid-operation-id"
    assert RuleId.UNDEFINED_SECURITY_SCHEME == "undefined-security-scheme"
    assert RuleId.INVALID_SECURITY_SCOPE == "invalid-security-scope"
    assert RuleId.MISSING_PATH_PARAMETER == "missing-path-parameter"
    assert RuleId.UNUSED_PATH_PARAMETER == "unused-path-parameter"


def test_fix_action_to_dict():
    action = FixAction(
        rule_id="test-rule",
        description="Fix something",
        target_pointer="/paths/~1ping/get",
        action_type="set",
        value={"key": "val"},
    )
    d = action.to_dict()
    assert d["rule_id"] == "test-rule"
    assert d["description"] == "Fix something"
    assert d["target_pointer"] == "/paths/~1ping/get"
    assert d["action_type"] == "set"
    assert d["value"] == {"key": "val"}


def test_diagnostic_to_dict():
    action = FixAction(
        rule_id="test-rule",
        description="Fix something",
        target_pointer="/paths",
        action_type="set",
        value="val",
    )
    diag = Diagnostic(
        rule_id="test-rule",
        message="Something is wrong",
        severity=Severity.ERROR,
        pointer="/paths",
        line=10,
        column=5,
        fixable=True,
        fix_action=action,
        suggestion="Do this",
    )
    d = diag.to_dict()
    assert d["rule_id"] == "test-rule"
    assert d["message"] == "Something is wrong"
    assert d["severity"] == "error"
    assert d["pointer"] == "/paths"
    assert d["line"] == 10
    assert d["column"] == 5
    assert d["fixable"] is True
    assert d["fix_action"]["action_type"] == "set"
    assert d["suggestion"] == "Do this"


def test_lint_result_counts_and_dict():
    d_err = Diagnostic(rule_id="r1", message="err", severity=Severity.ERROR, fixable=True)
    d_warn = Diagnostic(rule_id="r2", message="warn", severity=Severity.WARNING, fixable=False)
    d_info = Diagnostic(rule_id="r3", message="info", severity=Severity.INFO, fixable=False)

    lr = LintResult(
        file_path="test.yaml",
        openapi_version="3.0.3",
        diagnostics=[d_err, d_warn, d_info],
    )

    assert not lr.is_valid
    assert lr.error_count == 1
    assert lr.warning_count == 1
    assert lr.info_count == 1
    assert lr.fixable_count == 1

    d = lr.to_dict()
    assert d["file_path"] == "test.yaml"
    assert d["openapi_version"] == "3.0.3"
    assert d["is_valid"] is False
    assert d["error_count"] == 1
    assert len(d["diagnostics"]) == 3

    # Clean lint result
    clean_lr = LintResult(file_path="clean.yaml", openapi_version="3.0.0")
    assert clean_lr.is_valid
    assert clean_lr.error_count == 0

    # Parse error lint result
    err_lr = LintResult(file_path="broken.yaml", parse_error="Syntax error")
    assert not err_lr.is_valid


def test_fix_result_counts_and_dict():
    action = FixAction(
        rule_id="r1",
        description="Fix",
        target_pointer="/",
        action_type="set",
        value=1,
    )
    diag = Diagnostic(rule_id="r2", message="Unfixed error", severity=Severity.ERROR)
    fr = FixResult(
        file_path="orig.yaml",
        output_path="out.yaml",
        fixes_applied=1,
        fixes=[action],
        remaining_diagnostics=[diag],
        dry_run=True,
        backup_path="orig.yaml.bak",
    )
    assert not fr.is_fully_fixed
    d = fr.to_dict()
    assert d["file_path"] == "orig.yaml"
    assert d["output_path"] == "out.yaml"
    assert d["fixes_applied"] == 1
    assert d["dry_run"] is True
    assert d["backup_path"] == "orig.yaml.bak"
    assert d["is_fully_fixed"] is False
    assert d["remaining_error_count"] == 1
    assert d["remaining_warning_count"] == 0

    fr_clean = FixResult(
        file_path="orig.yaml",
        output_path="out.yaml",
        fixes_applied=1,
        remaining_diagnostics=[],
    )
    assert fr_clean.is_fully_fixed
