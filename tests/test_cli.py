"""Tests for openapi_doctor.cli."""

import json
from pathlib import Path
import pytest

from openapi_doctor.cli import create_parser, main


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "openapi-doctor" in captured.out


def test_cli_help(capsys):
    ret = main([])
    assert ret == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out or "Available subcommands" in captured.out


def test_cli_check_clean(tmp_path, capsys):
    f = tmp_path / "clean.yaml"
    f.write_text("""openapi: 3.0.3
info:
  title: Clean
  version: 1.0
paths:
  /ping:
    get:
      operationId: getPing
      responses:
        '200':
          description: ok
""", encoding="utf-8")

    code = main(["check", str(f)])
    assert code == 0
    captured = capsys.readouterr()
    assert "No issues found" in captured.out


def test_cli_check_with_errors(tmp_path, capsys):
    f = tmp_path / "broken.yaml"
    f.write_text("""openapi: 3.0.3
paths:
  /ping:
    get:
      responses:
        '200': {}
""", encoding="utf-8")

    code = main(["check", str(f), "--no-color"])
    assert code == 1
    captured = capsys.readouterr()
    assert "missing-response-description" in captured.out


def test_cli_check_implicit_subcommand(tmp_path, capsys):
    # Passing a path directly without 'check' or 'fix' should default to 'check'
    f = tmp_path / "clean.yaml"
    f.write_text("""openapi: 3.0.3
info:
  title: Clean
  version: 1.0
paths:
  /ping:
    get:
      operationId: getPing
      responses:
        '200':
          description: ok
""", encoding="utf-8")

    code = main([str(f), "--no-color"])
    _ = capsys.readouterr()
    assert code == 0


def test_cli_check_formats(tmp_path, capsys):
    f = tmp_path / "spec.yaml"
    f.write_text("""openapi: 3.0.3
paths:
  /ping:
    get:
      responses:
        '200': {}
""", encoding="utf-8")

    # JSON format
    code = main(["check", str(f), "--format", "json"])
    assert code == 1
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["summary"]["total_errors"] >= 1

    # GitHub format
    code = main(["check", str(f), "--format", "github"])
    assert code == 1
    captured = capsys.readouterr()
    assert "::error file=" in captured.out

    # Markdown format
    code = main(["check", str(f), "--format", "markdown"])
    assert code == 1
    captured = capsys.readouterr()
    assert "# OpenAPI Doctor Report" in captured.out


def test_cli_check_strict_mode(tmp_path, capsys):
    f = tmp_path / "warn.yaml"
    f.write_text("""openapi: 3.0.3
paths:
  /ping:
    get:
      responses:
        '200':
          description: ok
""", encoding="utf-8")

    # Missing operationId is a warning
    # Normal mode -> return 0
    code_normal = main(["check", str(f), "--no-color"])
    _ = capsys.readouterr()
    assert code_normal == 0

    # Strict mode -> return 1
    code_strict = main(["check", str(f), "--strict", "--no-color"])
    _ = capsys.readouterr()
    assert code_strict == 1


def test_cli_check_missing_files(capsys):
    code = main(["check", "non_existent_folder_abc"])
    assert code == 2
    captured = capsys.readouterr()
    assert "No OpenAPI specification files found" in captured.err


def test_cli_check_parse_error(tmp_path, capsys):
    f = tmp_path / "syntax_error.yaml"
    f.write_text("openapi: 3.0.0\n  indent_err:\n- 1\n - 2", encoding="utf-8")

    code = main(["check", str(f)])
    assert code == 2
    captured = capsys.readouterr()
    assert "Parse error" in captured.out


def test_cli_fix_dry_run(tmp_path, capsys):
    f = tmp_path / "spec.yaml"
    f.write_text("""openapi: 3.0.3
paths:
  /ping:
    get:
      responses:
        '200': {}
""", encoding="utf-8")

    code = main(["fix", str(f), "--dry-run", "--no-color"])
    assert code == 0
    captured = capsys.readouterr()
    assert "[DRY RUN]" in captured.out


def test_cli_fix_in_place(tmp_path, capsys):
    f = tmp_path / "spec.yaml"
    f.write_text("""openapi: 3.0.3
paths:
  /ping:
    get:
      responses:
        '200': {}
""", encoding="utf-8")

    code = main(["fix", str(f), "--backup", "--no-color"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Applied" in captured.out
    assert "Created backup" in captured.out

    # Spec should now be clean
    check_code = main(["check", str(f), "--no-color"])
    _ = capsys.readouterr()
    assert check_code == 0


def test_cli_fix_json_format(tmp_path, capsys):
    f = tmp_path / "spec.yaml"
    f.write_text("""openapi: 3.0.3
paths:
  /ping:
    get:
      responses:
        '200': {}
""", encoding="utf-8")

    code = main(["fix", str(f), "--format", "json", "--dry-run"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["summary"]["dry_run"] is True
    assert data["summary"]["total_fixes_applied"] >= 1


def test_cli_fix_output_multi_file_error(tmp_path, capsys):
    f1 = tmp_path / "s1.yaml"
    f2 = tmp_path / "s2.yaml"
    f1.write_text("openapi: 3.0.0\npaths: {}\n", encoding="utf-8")
    f2.write_text("openapi: 3.0.0\npaths: {}\n", encoding="utf-8")

    code = main(["fix", str(f1), str(f2), "-o", str(tmp_path / "out.yaml")])
    assert code == 2
    captured = capsys.readouterr()
    assert "--output can only be used with a single specification file" in captured.err
