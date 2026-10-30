"""Tests for openapi_doctor.parser."""

import os
import tempfile
import pytest
import yaml

from openapi_doctor.parser import (
    LineInfoDict,
    LineInfoList,
    ParsedSpec,
    escape_pointer_token,
    find_line_col_for_pointer,
    get_node_location,
    load_spec_file,
    load_spec_from_text,
    pointer_to_tokens,
    resolve_pointer,
    tokens_to_pointer,
    unescape_pointer_token,
)


def test_escape_and_unescape_pointer_tokens():
    assert escape_pointer_token("foo/bar") == "foo~1bar"
    assert escape_pointer_token("foo~bar") == "foo~0bar"
    assert escape_pointer_token("a/b~c") == "a~1b~0c"
    assert unescape_pointer_token("foo~1bar") == "foo/bar"
    assert unescape_pointer_token("foo~0bar") == "foo~bar"
    assert unescape_pointer_token("a~1b~0c") == "a/b~c"


def test_pointer_to_tokens_and_tokens_to_pointer():
    assert pointer_to_tokens("") == []
    assert pointer_to_tokens("/") == []
    assert pointer_to_tokens("#") == []
    assert pointer_to_tokens("#/") == []
    assert pointer_to_tokens("/paths/~1users/get") == ["paths", "/users", "get"]
    assert pointer_to_tokens("#/components/schemas/Pet") == ["components", "schemas", "Pet"]

    assert tokens_to_pointer([]) == "/"
    assert tokens_to_pointer([], uri_fragment=True) == "#/"
    assert tokens_to_pointer(["paths", "/users", "get"]) == "/paths/~1users/get"
    assert tokens_to_pointer(["components", "schemas", "Pet"], uri_fragment=True) == "#/components/schemas/Pet"


def test_resolve_pointer():
    doc = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0"},
        "tags": [{"name": "tag1"}, {"name": "tag2"}],
        "nested": {"items": [10, 20, 30]},
    }

    found, val = resolve_pointer(doc, "/info/title")
    assert found is True
    assert val == "Test"

    found, val = resolve_pointer(doc, "/tags/1/name")
    assert found is True
    assert val == "tag2"

    found, val = resolve_pointer(doc, "#/nested/items/0")
    assert found is True
    assert val == 10

    # Non-existent key
    found, val = resolve_pointer(doc, "/info/description")
    assert found is False
    assert val is None

    # Out of bounds index
    found, val = resolve_pointer(doc, "/tags/5")
    assert found is False
    assert val is None

    # Invalid list index (non-integer)
    found, val = resolve_pointer(doc, "/tags/not_a_number")
    assert found is False
    assert val is None

    # Traversing into a non-dict non-list
    found, val = resolve_pointer(doc, "/openapi/subprop")
    assert found is False
    assert val is None


def test_load_spec_from_text_yaml():
    yaml_content = """
openapi: 3.0.0
info:
  title: Sample
  version: 1.0.0
paths:
  /ping:
    get:
      responses:
        '200':
          description: ok
"""
    spec = load_spec_from_text(yaml_content, "sample.yaml")
    assert spec.format_type == "yaml"
    assert spec.openapi_version == "3.0.0"
    assert spec.data["info"]["title"] == "Sample"

    # Line info check
    assert isinstance(spec.data, LineInfoDict)
    line, col = spec.get_location("/info/title")
    assert line is not None
    assert col is not None


def test_load_spec_from_text_json():
    json_content = """{
  "openapi": "3.1.0",
  "info": {
    "title": "JSON API",
    "version": "1.0.0"
  },
  "paths": {}
}"""
    spec = load_spec_from_text(json_content, "sample.json")
    assert spec.format_type == "json"
    assert spec.openapi_version == "3.1.0"
    assert spec.data["info"]["title"] == "JSON API"

    serialized = spec.serialize()
    assert '"openapi": "3.1.0"' in serialized


def test_load_spec_from_text_swagger():
    yaml_content = """
swagger: '2.0'
info:
  title: Swagger 2 API
  version: 1.0.0
paths: {}
"""
    spec = load_spec_from_text(yaml_content, "swagger.yaml")
    assert spec.openapi_version == "2.0"


def test_load_spec_invalid_json():
    with pytest.raises(ValueError, match="JSON parsing error"):
        load_spec_from_text('{"openapi": "3.0.0", invalid}', "bad.json")


def test_load_spec_invalid_yaml():
    with pytest.raises(ValueError, match="YAML parsing error"):
        load_spec_from_text("openapi: 3.0.0\n  bad_indent:\n- 1\n - 2", "bad.yaml")


def test_load_spec_non_mapping_root():
    with pytest.raises(ValueError, match="OpenAPI root must be a mapping/object"):
        load_spec_from_text("- item1\n- item2", "bad.yaml")


def test_load_spec_empty_yaml():
    spec = load_spec_from_text("", "empty.yaml")
    assert spec.data == {}
    assert spec.openapi_version is None


def test_load_spec_file(tmp_path):
    f = tmp_path / "spec.yaml"
    f.write_text("openapi: 3.0.1\ninfo:\n  title: File API\n  version: 1.0\npaths: {}\n", encoding="utf-8")

    spec = load_spec_file(str(f))
    assert spec.file_path == str(f)
    assert spec.openapi_version == "3.0.1"


def test_load_spec_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_spec_file("non_existent_file_abc123.yaml")


def test_parsed_spec_resolve_and_serialize():
    yaml_content = "openapi: 3.0.0\npaths:\n  /test:\n    get:\n      summary: Test\n"
    spec = load_spec_from_text(yaml_content, "test.yaml")

    found, node = spec.resolve("/paths/~1test/get/summary")
    assert found is True
    assert node == "Test"

    dumped = spec.serialize()
    assert "paths:" in dumped
    assert "/test:" in dumped


def test_find_line_col_for_pointer():
    raw_yaml = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get users
"""
    line, col = find_line_col_for_pointer(raw_yaml, "/paths/~1users/get/summary")
    assert line == 8

    # Empty pointer returns 1, 1
    assert find_line_col_for_pointer(raw_yaml, "") == (1, 1)

    # Missing token returns last found line
    line, _ = find_line_col_for_pointer(raw_yaml, "/paths/nonexistent/field")
    assert line == 5


def test_safe_dumper_representers():
    d = LineInfoDict({"key": "value"})
    l = LineInfoList([1, 2, 3])
    data = {"dict": d, "list": l}

    dumped = yaml.safe_dump(data)
    assert "key: value" in dumped
    assert "- 1" in dumped
