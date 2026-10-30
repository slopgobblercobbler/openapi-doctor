"""Tests for UndefinedSchemaRule."""

from openapi_doctor.models import RuleId, Severity
from openapi_doctor.parser import load_spec_from_text
from openapi_doctor.rules.references import UndefinedSchemaRule, walk_references


def test_walk_references():
    doc = {
        "paths": {
            "/item": {
                "get": {
                    "responses": {
                        "200": {"$ref": "#/components/responses/Success"},
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "properties": {
                        "address": {"$ref": "#/components/schemas/Address"}
                    }
                }
            }
        }
    }
    refs = list(walk_references(doc, []))
    assert len(refs) == 2
    ref_vals = [r[0] for r in refs]
    assert "#/components/responses/Success" in ref_vals
    assert "#/components/schemas/Address" in ref_vals


def test_undefined_schema_rule_detection():
    rule = UndefinedSchemaRule()
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /users:
    get:
      responses:
        '200':
          $ref: '#/components/responses/UserResponse'
        '400':
          $ref: 'https://example.com/schemas/remote.json'
        '500':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorPayload'
    parameters:
      - $ref: '#/components/parameters/PageQuery'
components:
  schemas:
    Existing:
      type: string
""")
    diags = rule.check(spec, {})
    # Remote reference should be ignored; 3 broken internal refs
    assert len(diags) == 3

    schema_diag = next(d for d in diags if "ErrorPayload" in d.message)
    assert schema_diag.rule_id == RuleId.BROKEN_REF
    assert schema_diag.severity == Severity.ERROR
    assert schema_diag.fixable is True
    assert schema_diag.fix_action.target_pointer == "/components/schemas/ErrorPayload"
    assert schema_diag.fix_action.value["type"] == "object"

    resp_diag = next(d for d in diags if "UserResponse" in d.message)
    assert resp_diag.fixable is True
    assert resp_diag.fix_action.target_pointer == "/components/responses/UserResponse"
    assert "description" in resp_diag.fix_action.value

    param_diag = next(d for d in diags if "PageQuery" in d.message)
    assert param_diag.fixable is True
    assert param_diag.fix_action.target_pointer == "/components/parameters/PageQuery"
    assert param_diag.fix_action.value["in"] == "query"


def test_undefined_schema_rule_autofix():
    rule = UndefinedSchemaRule()
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /data:
    get:
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MissingModel'
""")
    diags = rule.check(spec, {})
    assert len(diags) == 1

    applied = rule.fix(spec, diags)
    assert applied == 1

    # MissingModel should now be in components.schemas
    assert "MissingModel" in spec.data["components"]["schemas"]
    assert spec.data["components"]["schemas"]["MissingModel"]["type"] == "object"

    # Re-checking produces no diagnostics
    new_diags = rule.check(spec, {})
    assert len(new_diags) == 0


def test_valid_references_pass():
    rule = UndefinedSchemaRule()
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /data:
    get:
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ValidModel'
components:
  schemas:
    ValidModel:
      type: object
""")
    diags = rule.check(spec, {})
    assert len(diags) == 0
