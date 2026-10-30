"""Tests for openapi_doctor.config."""

import json
from pathlib import Path
import pytest
import yaml

from openapi_doctor.config import (
    Config,
    find_config_file,
    load_config,
)
from openapi_doctor.models import Severity


def test_config_rules_enablement_and_severity():
    cfg = Config(
        rules={
            "rule-1": "off",
            "rule-2": "disabled",
            "rule-3": "ignore",
            "rule-4": "false",
            "rule-5": "error",
            "rule-6": "warning",
            "rule-7": "info",
        }
    )
    assert cfg.is_rule_enabled("rule-1") is False
    assert cfg.is_rule_enabled("rule-2") is False
    assert cfg.is_rule_enabled("rule-3") is False
    assert cfg.is_rule_enabled("rule-4") is False
    assert cfg.is_rule_enabled("rule-5") is True

    assert cfg.get_rule_severity("rule-5", Severity.WARNING) == Severity.ERROR
    assert cfg.get_rule_severity("rule-6", Severity.ERROR) == Severity.WARNING
    assert cfg.get_rule_severity("rule-7", Severity.ERROR) == Severity.INFO
    assert cfg.get_rule_severity("unconfigured-rule", Severity.WARNING) == Severity.WARNING


def test_load_config_from_yaml(tmp_path):
    cfg_file = tmp_path / ".openapi-doctor.yaml"
    cfg_data = {
        "strict": True,
        "format": "json",
        "rules": {
            "missing-response-description": "error",
            "unused-component": "off",
        },
        "ignore_paths": ["vendor/**"],
    }
    cfg_file.write_text(yaml.dump(cfg_data), encoding="utf-8")

    loaded = load_config(str(cfg_file))
    assert loaded.strict is True
    assert loaded.format == "json"
    assert loaded.rules["unused-component"] == "off"
    assert "vendor/**" in loaded.ignore_paths


def test_load_config_from_json(tmp_path):
    cfg_file = tmp_path / ".openapi-doctor.json"
    cfg_data = {
        "strict": False,
        "format": "markdown",
        "rules": {"broken-ref": "warning"},
    }
    cfg_file.write_text(json.dumps(cfg_data), encoding="utf-8")

    loaded = load_config(str(cfg_file))
    assert loaded.strict is False
    assert loaded.format == "markdown"
    assert loaded.rules["broken-ref"] == "warning"


def test_load_config_from_pyproject_toml(tmp_path):
    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text("""
[project]
name = "my-app"

[tool.openapi-doctor]
strict = true
format = "github"
""", encoding="utf-8")

    loaded = load_config(str(toml_file))
    assert loaded.strict is True
    assert loaded.format == "github"


def test_load_config_nonexistent():
    cfg = load_config("nonexistent_cfg_file_123.yaml")
    assert cfg.strict is False
    assert cfg.format == "text"


def test_find_config_file(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()

    cfg_file = tmp_path / ".openapi-doctor.yaml"
    cfg_file.write_text("strict: true", encoding="utf-8")

    found = find_config_file(str(sub))
    assert found == str(cfg_file)


def test_find_config_file_none(tmp_path):
    assert find_config_file(str(tmp_path)) is None
