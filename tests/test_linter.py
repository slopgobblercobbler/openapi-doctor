"""Tests for openapi_doctor.linter."""

from pathlib import Path
import pytest

from openapi_doctor.config import Config
from openapi_doctor.linter import find_spec_files, lint_file, lint_paths, lint_spec
from openapi_doctor.models import Severity
from openapi_doctor.parser import load_spec_from_text


def test_find_spec_files(tmp_path):
    f1 = tmp_path / "spec1.yaml"
    f2 = tmp_path / "spec2.json"
    f3 = tmp_path / "spec3.yml"
    txt = tmp_path / "other.txt"

    f1.write_text("openapi: 3.0.0", encoding="utf-8")
    f2.write_text("{}", encoding="utf-8")
    f3.write_text("openapi: 3.0.0", encoding="utf-8")
    txt.write_text("not a spec", encoding="utf-8")

    # Pass folder
    discovered = find_spec_files([str(tmp_path)])
    assert len(discovered) == 3
    assert str(f1.resolve()) in discovered
    assert str(f2.resolve()) in discovered
    assert str(f3.resolve()) in discovered

    # Pass explicit file
    single = find_spec_files([str(f1)])
    assert len(single) == 1
    assert single[0] == str(f1.resolve())

    # Pass glob pattern
    globbed = find_spec_files([str(tmp_path / "*.yaml")])
    assert len(globbed) == 1


def test_lint_spec_with_disabled_rule():
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /users:
    get:
      responses:
        '200': {}
""")
    # With default config, missing description is flagged
    res_default = lint_spec(spec)
    assert res_default.error_count == 1

    # With rule disabled
    cfg = Config(rules={"missing-response-description": "off"})
    res_disabled = lint_spec(spec, config=cfg)
    assert res_disabled.error_count == 0


def test_lint_spec_severity_override():
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /users:
    get:
      operationId: getUsers
      responses:
        '200': {}
""")
    cfg = Config(rules={"missing-response-description": "warning"})
    res = lint_spec(spec, config=cfg)
    assert res.error_count == 0
    assert res.warning_count == 1
    assert res.diagnostics[0].severity == Severity.WARNING


def test_lint_file_success(tmp_path):
    f = tmp_path / "clean.yaml"
    f.write_text("""
openapi: 3.0.3
info:
  title: Clean API
  version: 1.0
paths:
  /ping:
    get:
      operationId: getPing
      responses:
        '200':
          description: ok
""", encoding="utf-8")

    res = lint_file(str(f))
    assert res.is_valid
    assert res.error_count == 0
    assert res.warning_count == 0


def test_lint_file_parse_error(tmp_path):
    f = tmp_path / "broken.yaml"
    f.write_text("openapi: 3.0.0\n  bad_indent:\n- 1\n - 2", encoding="utf-8")

    res = lint_file(str(f))
    assert not res.is_valid
    assert res.parse_error is not None
    assert "YAML parsing error" in res.parse_error


def test_lint_paths(tmp_path):
    f1 = tmp_path / "spec1.yaml"
    f2 = tmp_path / "spec2.yaml"
    f1.write_text("openapi: 3.0.0\npaths: {}\n", encoding="utf-8")
    f2.write_text("openapi: 3.0.0\npaths: {}\n", encoding="utf-8")

    results = lint_paths([str(tmp_path)])
    assert len(results) == 2

    # Empty paths
    assert lint_paths(["non_existent_folder_abc"]) == []
