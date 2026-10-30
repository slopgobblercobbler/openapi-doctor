"""Tests for UnusedComponentRule."""

from openapi_doctor.models import RuleId, Severity
from openapi_doctor.parser import load_spec_from_text
from openapi_doctor.rules import get_default_rules, RULE_REGISTRY
from openapi_doctor.rules.components import (
    UnusedComponentRule,
    collect_used_references_and_security,
)


def test_collect_used_references_and_security():
    doc = {
        "security": [{"GlobalKey": []}],
        "paths": {
            "/users": {
                "get": {
                    "security": [{"LocalKey": []}],
                    "responses": {
                        "200": {"$ref": "#/components/responses/UserResp"}
                    }
                }
            }
        }
    }
    refs, sec_schemes = collect_used_references_and_security(doc)
    assert "#/components/responses/UserResp" in refs
    assert "GlobalKey" in sec_schemes
    assert "LocalKey" in sec_schemes


def test_unused_component_rule_detection_and_fix():
    rule = UnusedComponentRule()
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /users:
    get:
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UsedSchema'
components:
  schemas:
    UsedSchema:
      type: object
    UnusedSchema:
      type: string
  responses:
    UnusedResp:
      description: Unused
  securitySchemes:
    UnusedSec:
      type: http
      scheme: bearer
""")
    diags = rule.check(spec, {})
    assert len(diags) == 3

    unused_names = [d.pointer for d in diags]
    assert "/components/schemas/UnusedSchema" in unused_names
    assert "/components/responses/UnusedResp" in unused_names
    assert "/components/securitySchemes/UnusedSec" in unused_names

    applied = rule.fix(spec, diags)
    assert applied == 3

    comps = spec.data["components"]
    assert "UsedSchema" in comps["schemas"]
    assert "UnusedSchema" not in comps["schemas"]
    assert "UnusedResp" not in comps["responses"]
    assert "UnusedSec" not in comps["securitySchemes"]


def test_get_default_rules_and_registry():
    rules = get_default_rules()
    assert len(rules) == 6
    assert RuleId.MISSING_RESPONSE_DESCRIPTION in RULE_REGISTRY
    assert RuleId.BROKEN_REF in RULE_REGISTRY
    assert RuleId.MISSING_OPERATION_ID in RULE_REGISTRY
    assert RuleId.MISSING_PATH_PARAMETER in RULE_REGISTRY
