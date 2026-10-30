"""Tests for MissingResponseDescriptionRule."""

from openapi_doctor.models import RuleId, Severity
from openapi_doctor.parser import load_spec_from_text
from openapi_doctor.rules.responses import MissingResponseDescriptionRule


def test_missing_response_description_detection():
    rule = MissingResponseDescriptionRule()
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /users:
    get:
      responses:
        '200':
          content:
            application/json: {}
        '404':
          description: "   "
        '500':
          description: "Internal Server Error"
        'default':
          $ref: '#/components/responses/DefaultError'
components:
  responses:
    DefaultError:
      description: "Default error response"
    MissingDescComp:
      content:
        application/json: {}
""")
    diags = rule.check(spec, {})
    assert len(diags) == 3

    # Check 200 (missing description)
    diag_200 = next(d for d in diags if "200" in d.message)
    assert diag_200.rule_id == RuleId.MISSING_RESPONSE_DESCRIPTION
    assert diag_200.severity == Severity.ERROR
    assert diag_200.fixable is True
    assert diag_200.fix_action is not None
    assert diag_200.fix_action.value == "OK"

    # Check 404 (empty whitespace description)
    diag_404 = next(d for d in diags if "404" in d.message)
    assert diag_404.fix_action.value == "Not Found"

    # Check component response
    diag_comp = next(d for d in diags if "MissingDescComp" in d.message)
    assert diag_comp.fixable is True
    assert diag_comp.fix_action.value == "Response MissingDescComp"


def test_missing_response_description_autofix():
    rule = MissingResponseDescriptionRule()
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /ping:
    get:
      responses:
        '200': {}
""")
    diags = rule.check(spec, {})
    assert len(diags) == 1

    applied = rule.fix(spec, diags)
    assert applied == 1
    assert spec.data["paths"]["/ping"]["get"]["responses"]["200"]["description"] == "OK"

    # Re-checking should produce zero diagnostics
    new_diags = rule.check(spec, {})
    assert len(new_diags) == 0


def test_clean_spec_passes():
    rule = MissingResponseDescriptionRule()
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /health:
    get:
      responses:
        '200':
          description: Healthy
""")
    diags = rule.check(spec, {})
    assert len(diags) == 0
