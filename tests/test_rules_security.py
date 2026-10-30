"""Tests for SecuritySchemeMismatchRule."""

from openapi_doctor.models import RuleId, Severity
from openapi_doctor.parser import load_spec_from_text
from openapi_doctor.rules.security import (
    SecuritySchemeMismatchRule,
    generate_security_scheme_stub,
)


def test_generate_security_scheme_stub():
    api_key_stub = generate_security_scheme_stub("MyApiKey")
    assert api_key_stub["type"] == "apiKey"
    assert api_key_stub["name"] == "X-API-Key"

    basic_stub = generate_security_scheme_stub("basicAuth")
    assert basic_stub["type"] == "http"
    assert basic_stub["scheme"] == "basic"

    oauth_stub = generate_security_scheme_stub("myOauth2Scheme")
    assert oauth_stub["type"] == "oauth2"
    assert "flows" in oauth_stub

    bearer_stub = generate_security_scheme_stub("jwtToken")
    assert bearer_stub["type"] == "http"
    assert bearer_stub["scheme"] == "bearer"


def test_undefined_security_scheme_root_and_operation():
    rule = SecuritySchemeMismatchRule()
    spec = load_spec_from_text("""
openapi: 3.0.3
security:
  - GlobalApiKey: []
paths:
  /secure:
    get:
      security:
        - CustomBearer: []
      responses:
        '200':
          description: ok
components:
  securitySchemes: {}
""")
    diags = rule.check(spec, {})
    assert len(diags) == 2
    for diag in diags:
        assert diag.rule_id == RuleId.UNDEFINED_SECURITY_SCHEME
        assert diag.severity == Severity.ERROR
        assert diag.fixable is True

    applied = rule.fix(spec, diags)
    assert applied == 2

    schemes = spec.data["components"]["securitySchemes"]
    assert "GlobalApiKey" in schemes
    assert schemes["GlobalApiKey"]["type"] == "apiKey"
    assert "CustomBearer" in schemes
    assert schemes["CustomBearer"]["scheme"] == "bearer"


def test_oauth_scope_validation_and_fix():
    rule = SecuritySchemeMismatchRule()
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /admin:
    get:
      security:
        - OAuth2Auth:
            - read:users
            - write:users
      responses:
        '200':
          description: ok
components:
  securitySchemes:
    OAuth2Auth:
      type: oauth2
      flows:
        clientCredentials:
          tokenUrl: https://example.com/token
          scopes:
            read:users: Read all users
""")
    diags = rule.check(spec, {})
    assert len(diags) == 1
    assert diags[0].rule_id == RuleId.INVALID_SECURITY_SCOPE
    assert diags[0].severity == Severity.WARNING
    assert "write:users" in diags[0].message
    assert diags[0].fixable is True

    applied = rule.fix(spec, diags)
    assert applied == 1
    scopes = spec.data["components"]["securitySchemes"]["OAuth2Auth"]["flows"]["clientCredentials"]["scopes"]
    assert "write:users" in scopes
