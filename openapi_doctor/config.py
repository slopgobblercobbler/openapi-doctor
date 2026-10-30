"""Configuration loader for openapi-doctor."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from openapi_doctor.models import Severity

CONFIG_FILENAMES = (
    ".openapi-doctor.yaml",
    ".openapi-doctor.yml",
    ".openapi-doctor.json",
    "openapi-doctor.yaml",
    "openapi-doctor.json",
)


@dataclass
class Config:
    """Configuration options for openapi-doctor."""
    rules: Dict[str, str] = field(default_factory=dict)
    ignore_paths: List[str] = field(default_factory=list)
    strict: bool = False
    format: str = "text"  # 'text', 'json', 'github', 'markdown'

    def is_rule_enabled(self, rule_id: str) -> bool:
        setting = self.rules.get(rule_id, "").lower()
        return setting not in ("off", "ignore", "disabled", "false")

    def get_rule_severity(self, rule_id: str, default: Severity) -> Severity:
        setting = self.rules.get(rule_id, "").lower()
        if setting == "error":
            return Severity.ERROR
        elif setting == "warning":
            return Severity.WARNING
        elif setting == "info":
            return Severity.INFO
        return default


def find_config_file(start_dir: Optional[str] = None) -> Optional[str]:
    """Search for configuration file starting from start_dir up to root."""
    curr = Path(start_dir or os.getcwd()).resolve()
    while True:
        for fname in CONFIG_FILENAMES:
            candidate = curr / fname
            if candidate.is_file():
                return str(candidate)

        pyproject = curr / "pyproject.toml"
        if pyproject.is_file():
            try:
                # Basic check for [tool.openapi-doctor] in pyproject.toml
                with open(pyproject, "r", encoding="utf-8") as f:
                    content = f.read()
                if "[tool.openapi-doctor]" in content or "[tool.openapi_doctor]" in content:
                    return str(pyproject)
            except Exception:
                pass

        if curr.parent == curr:
            break
        curr = curr.parent

    return None


def load_config(config_path: Optional[str] = None) -> Config:
    """Loads configuration from file or returns defaults."""
    cfg = Config()

    if config_path is None:
        config_path = find_config_file()

    if not config_path or not os.path.isfile(config_path):
        return cfg

    try:
        if config_path.endswith(".toml"):
            # Simple toml parser or basic extraction
            with open(config_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            in_section = False
            for line in lines:
                line_str = line.strip()
                if line_str in ("[tool.openapi-doctor]", "[tool.openapi_doctor]"):
                    in_section = True
                    continue
                elif line_str.startswith("["):
                    in_section = False
                    continue
                if in_section and "=" in line_str:
                    key, val = [x.strip() for x in line_str.split("=", 1)]
                    if key == "strict":
                        cfg.strict = val.lower() == "true"
                    elif key == "format":
                        cfg.format = val.strip('"\'')
        elif config_path.endswith(".json"):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            _apply_dict_config(cfg, data)
        else:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                _apply_dict_config(cfg, data)
    except Exception:
        # Fall back gracefully to defaults on syntax error
        pass

    return cfg


def _apply_dict_config(cfg: Config, data: Dict[str, Any]) -> None:
    if "rules" in data and isinstance(data["rules"], dict):
        cfg.rules = {str(k): str(v) for k, v in data["rules"].items()}
    if "ignore_paths" in data and isinstance(data["ignore_paths"], list):
        cfg.ignore_paths = [str(p) for p in data["ignore_paths"]]
    if "strict" in data:
        cfg.strict = bool(data["strict"])
    if "format" in data:
        cfg.format = str(data["format"])
