"""Test fixtures and helpers for openapi-doctor tests."""

import pytest
from openapi_doctor.parser import load_spec_from_text

MINIMAL_OPENAPI_YAML = """
openapi: 3.0.3
info:
  title: Test API
  version: 1.0.0
paths:
  /ping:
    get:
      summary: Ping test
      operationId: getPing
      responses:
        '200':
          description: OK response
"""

MINIMAL_OPENAPI_JSON = """
{
  "openapi": "3.0.3",
  "info": {
    "title": "Test API JSON",
    "version": "1.0.0"
  },
  "paths": {
    "/ping": {
      "get": {
        "summary": "Ping test",
        "operationId": "getPing",
        "responses": {
          "200": {
            "description": "OK response"
          }
        }
      }
    }
  }
}
"""


@pytest.fixture
def minimal_yaml_spec():
    return load_spec_from_text(MINIMAL_OPENAPI_YAML, "test_spec.yaml")


@pytest.fixture
def minimal_json_spec():
    return load_spec_from_text(MINIMAL_OPENAPI_JSON, "test_spec.json")
