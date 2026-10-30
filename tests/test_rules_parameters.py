"""Tests for PathParameterRule."""

from openapi_doctor.models import RuleId, Severity
from openapi_doctor.parser import load_spec_from_text
from openapi_doctor.rules.parameters import PathParameterRule


def test_missing_path_parameter_detection_and_fix():
    rule = PathParameterRule()
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /users/{userId}/posts/{postId}:
    get:
      responses:
        '200':
          description: ok
""")
    diags = rule.check(spec, {})
    assert len(diags) == 2
    for diag in diags:
        assert diag.rule_id == RuleId.MISSING_PATH_PARAMETER
        assert diag.severity == Severity.ERROR
        assert diag.fixable is True

    applied = rule.fix(spec, diags)
    assert applied == 2

    params = spec.data["paths"]["/users/{userId}/posts/{postId}"]["get"]["parameters"]
    param_names = [p["name"] for p in params]
    assert "userId" in param_names
    assert "postId" in param_names
    assert all(p["in"] == "path" for p in params)
    assert all(p["required"] is True for p in params)


def test_path_level_parameter_satisfies_requirement():
    rule = PathParameterRule()
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /users/{userId}:
    parameters:
      - name: userId
        in: path
        required: true
        schema:
          type: string
    get:
      responses:
        '200':
          description: ok
""")
    diags = rule.check(spec, {})
    assert len(diags) == 0


def test_path_parameter_missing_required_true():
    rule = PathParameterRule()
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /users/{userId}:
    get:
      parameters:
        - name: userId
          in: path
          required: false
      responses:
        '200':
          description: ok
""")
    diags = rule.check(spec, {})
    assert len(diags) == 1
    assert "must have 'required: true'" in diags[0].message
    assert diags[0].fixable is True

    applied = rule.fix(spec, diags)
    assert applied == 1
    assert spec.data["paths"]["/users/{userId}"]["get"]["parameters"][0]["required"] is True


def test_unused_path_parameter_warning():
    rule = PathParameterRule()
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /users:
    get:
      parameters:
        - name: ghostParam
          in: path
          required: true
      responses:
        '200':
          description: ok
""")
    diags = rule.check(spec, {})
    assert len(diags) == 1
    assert diags[0].rule_id == RuleId.UNUSED_PATH_PARAMETER
    assert diags[0].severity == Severity.WARNING
    assert "does not exist in URL template" in diags[0].message
