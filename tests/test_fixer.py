"""Tests for openapi_doctor.fixer."""

import os
from pathlib import Path
import pytest

from openapi_doctor.fixer import apply_fixes
from openapi_doctor.parser import load_spec_file


def test_apply_fixes_dry_run(tmp_path):
    f = tmp_path / "spec.yaml"
    content = """openapi: 3.0.3
paths:
  /ping:
    get:
      responses:
        '200': {}
"""
    f.write_text(content, encoding="utf-8")

    res = apply_fixes(str(f), dry_run=True)
    assert res.dry_run is True
    assert res.fixes_applied == 2  # missing response description + missing operationId
    assert f.read_text(encoding="utf-8") == content  # File unchanged


def test_apply_fixes_in_place_with_backup(tmp_path):
    f = tmp_path / "spec.yaml"
    content = """openapi: 3.0.3
paths:
  /ping:
    get:
      responses:
        '200': {}
"""
    f.write_text(content, encoding="utf-8")

    res = apply_fixes(str(f), backup=True)
    assert res.fixes_applied > 0
    assert res.backup_path is not None
    assert os.path.exists(res.backup_path)

    # Backup should contain original content
    with open(res.backup_path, "r", encoding="utf-8") as b_file:
        assert b_file.read() == content

    # Original file is modified
    fixed_spec = load_spec_file(str(f))
    assert fixed_spec.data["paths"]["/ping"]["get"]["responses"]["200"]["description"] == "OK"


def test_apply_fixes_output_path(tmp_path):
    src = tmp_path / "src.yaml"
    out = tmp_path / "dist" / "fixed.yaml"
    content = """openapi: 3.0.3
paths:
  /ping:
    get:
      operationId: getPing
      responses:
        '200': {}
"""
    src.write_text(content, encoding="utf-8")

    res = apply_fixes(str(src), output_path=str(out))
    assert res.fixes_applied == 1
    assert out.exists()

    # Source untouched
    assert src.read_text(encoding="utf-8") == content

    fixed_spec = load_spec_file(str(out))
    assert fixed_spec.data["paths"]["/ping"]["get"]["responses"]["200"]["description"] == "OK"


def test_apply_fixes_rule_filter(tmp_path):
    f = tmp_path / "spec.yaml"
    content = """openapi: 3.0.3
paths:
  /ping:
    get:
      responses:
        '200': {}
"""
    f.write_text(content, encoding="utf-8")

    # Only fix missing-response-description, leaving missing-operation-id untouched
    res = apply_fixes(str(f), rule_ids=["missing-response-description"])
    assert res.fixes_applied == 1
    assert res.fixes[0].rule_id == "missing-response-description"

    fixed_spec = load_spec_file(str(f))
    assert "description" in fixed_spec.data["paths"]["/ping"]["get"]["responses"]["200"]
    assert "operationId" not in fixed_spec.data["paths"]["/ping"]["get"]
