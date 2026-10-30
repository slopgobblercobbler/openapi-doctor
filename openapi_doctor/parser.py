"""Parser and serializer for OpenAPI documents (YAML and JSON)."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import yaml


class LineInfoDict(dict):
    """Dictionary that retains line and column numbers."""
    __line__: int = 1
    __column__: int = 1


class LineInfoList(list):
    """List that retains line and column numbers."""
    __line__: int = 1
    __column__: int = 1


class SafeLineLoader(yaml.SafeLoader):
    """YAML SafeLoader that preserves line and column information."""
    pass


def _construct_mapping(loader: SafeLineLoader, node: yaml.MappingNode) -> LineInfoDict:
    loader.flatten_mapping(node)
    mapping = LineInfoDict(loader.construct_pairs(node))
    mapping.__line__ = node.start_mark.line + 1
    mapping.__column__ = node.start_mark.column + 1
    return mapping


def _construct_sequence(loader: SafeLineLoader, node: yaml.SequenceNode) -> LineInfoList:
    seq = LineInfoList(loader.construct_sequence(node))
    seq.__line__ = node.start_mark.line + 1
    seq.__column__ = node.start_mark.column + 1
    return seq


SafeLineLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping
)
SafeLineLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_SEQUENCE_TAG,
    _construct_sequence
)

# Configure SafeDumper to handle LineInfoDict and LineInfoList cleanly
yaml.SafeDumper.add_representer(
    LineInfoDict,
    yaml.representer.SafeRepresenter.represent_dict
)
yaml.SafeDumper.add_representer(
    LineInfoList,
    yaml.representer.SafeRepresenter.represent_list
)


def escape_pointer_token(token: str) -> str:
    """Escape a JSON pointer token according to RFC 6901."""
    return token.replace("~", "~0").replace("/", "~1")


def unescape_pointer_token(token: str) -> str:
    """Unescape a JSON pointer token according to RFC 6901."""
    return token.replace("~1", "/").replace("~0", "~")


def pointer_to_tokens(pointer: str) -> List[str]:
    """Convert a JSON Pointer string to a list of unescaped token strings."""
    if not pointer or pointer in ("/", "#", "#/"):
        return []
    if pointer.startswith("#/"):
        pointer = pointer[1:]
    if not pointer.startswith("/"):
        pointer = "/" + pointer
    tokens = pointer.split("/")[1:]
    return [unescape_pointer_token(t) for t in tokens]


def tokens_to_pointer(tokens: List[Union[str, int]], uri_fragment: bool = False) -> str:
    """Convert a list of tokens to a JSON Pointer string."""
    if not tokens:
        return "#/" if uri_fragment else "/"
    encoded = "/".join(escape_pointer_token(str(t)) for t in tokens)
    prefix = "#/" if uri_fragment else "/"
    return f"{prefix}{encoded}"


def resolve_pointer(doc: Any, pointer: str) -> Tuple[bool, Any]:
    """
    Resolve a JSON Pointer against a document.
    Returns (True, value) if found, or (False, None) if not found.
    """
    tokens = pointer_to_tokens(pointer)
    curr = doc
    for token in tokens:
        if isinstance(curr, dict):
            if token in curr:
                curr = curr[token]
            else:
                return False, None
        elif isinstance(curr, list):
            try:
                idx = int(token)
                if 0 <= idx < len(curr):
                    curr = curr[idx]
                else:
                    return False, None
            except ValueError:
                return False, None
        else:
            return False, None
    return True, curr


def find_line_col_for_pointer(raw_text: str, pointer: str, is_yaml: bool = True) -> Tuple[Optional[int], Optional[int]]:
    """
    Locates the line and column for a given JSON pointer within raw text as a fallback.
    """
    tokens = pointer_to_tokens(pointer)
    if not tokens:
        return 1, 1

    lines = raw_text.splitlines()
    last_line = 1
    last_col = 1

    # Search progressively for tokens
    current_line_idx = 0
    for token in tokens:
        # Search pattern for the token as a key
        # YAML: "token:" or token: or 'token':
        # JSON: "token":
        escaped_tok = re.escape(token)
        pattern = re.compile(rf'["\']?{escaped_tok}["\']?\s*:')
        found = False
        for i in range(current_line_idx, len(lines)):
            match = pattern.search(lines[i])
            if match:
                last_line = i + 1
                last_col = match.start() + 1
                current_line_idx = i
                found = True
                break
        if not found:
            break

    return last_line, last_col


def get_node_location(
    doc: Any,
    pointer: str,
    raw_text: Optional[str] = None,
    is_yaml: bool = True
) -> Tuple[Optional[int], Optional[int]]:
    """
    Returns (line, column) for the given JSON Pointer in the document.
    """
    tokens = pointer_to_tokens(pointer)
    curr = doc

    # Try walking parsed AST to get LineInfoDict / LineInfoList
    target = None
    for token in tokens:
        if isinstance(curr, dict) and token in curr:
            curr = curr[token]
            target = curr
        elif isinstance(curr, list):
            try:
                idx = int(token)
                if 0 <= idx < len(curr):
                    curr = curr[idx]
                    target = curr
                else:
                    target = None
                    break
            except ValueError:
                target = None
                break
        else:
            target = None
            break

    if target is not None:
        if hasattr(target, "__line__") and getattr(target, "__line__", 0) > 0:
            return target.__line__, target.__column__

    # Fallback to textual search
    if raw_text:
        return find_line_col_for_pointer(raw_text, pointer, is_yaml)

    return None, None


class ParsedSpec:
    """Encapsulates a parsed OpenAPI specification file."""

    def __init__(
        self,
        file_path: str,
        data: Dict[str, Any],
        raw_text: str,
        format_type: str,  # 'yaml' or 'json'
    ):
        self.file_path = file_path
        self.data = data
        self.raw_text = raw_text
        self.format_type = format_type

    @property
    def openapi_version(self) -> Optional[str]:
        if isinstance(self.data, dict):
            if "openapi" in self.data:
                return str(self.data["openapi"])
            if "swagger" in self.data:
                return str(self.data["swagger"])
        return None

    def get_location(self, pointer: str) -> Tuple[Optional[int], Optional[int]]:
        return get_node_location(
            self.data,
            pointer,
            raw_text=self.raw_text,
            is_yaml=(self.format_type == "yaml")
        )

    def resolve(self, pointer: str) -> Tuple[bool, Any]:
        return resolve_pointer(self.data, pointer)

    def serialize(self) -> str:
        """Serializes document back to string format."""
        if self.format_type == "json":
            return json.dumps(self.data, indent=2, ensure_ascii=False) + "\n"
        else:
            return yaml.safe_dump(
                self.data,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True
            )


def load_spec_from_text(text: str, file_path: str = "<memory>") -> ParsedSpec:
    """Parses an OpenAPI spec from raw text (auto-detecting JSON vs YAML)."""
    text_stripped = text.strip()
    is_json = text_stripped.startswith("{") or file_path.lower().endswith(".json")

    if is_json:
        try:
            data = json.loads(text)
            return ParsedSpec(file_path=file_path, data=data, raw_text=text, format_type="json")
        except json.JSONDecodeError as err:
            # Fallback to YAML parser if JSON parsing fails on a non-json extension
            if not file_path.lower().endswith(".json"):
                pass
            else:
                raise ValueError(f"JSON parsing error at line {err.lineno}, col {err.colno}: {err.msg}") from err

    try:
        data = yaml.load(text, Loader=SafeLineLoader)
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError(f"OpenAPI root must be a mapping/object, got {type(data).__name__}")
        return ParsedSpec(file_path=file_path, data=data, raw_text=text, format_type="yaml")
    except yaml.YAMLError as err:
        raise ValueError(f"YAML parsing error: {err}") from err


def load_spec_file(file_path: str) -> ParsedSpec:
    """Loads and parses an OpenAPI specification from a file path."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    return load_spec_from_text(content, file_path=file_path)
