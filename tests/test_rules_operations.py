"""Tests for OperationIdRule."""

from openapi_doctor.models import RuleId, Severity
from openapi_doctor.parser import load_spec_from_text
from openapi_doctor.rules.operations import (
    OperationIdRule,
    generate_operation_id,
    sanitize_operation_id,
)


def test_generate_operation_id():
    existing = set()
    op1 = generate_operation_id("get", "/users", existing)
    assert op1 == "getUsers"

    op2 = generate_operation_id("get", "/users/{userId}/repos", existing)
    assert op2 == "getUsersReposByUserid"

    op3 = generate_operation_id("delete", "/files/{folderId}/{fileId}", existing)
    assert op3 == "deleteFilesByFolderidAndFileid"

    # Root endpoint
    op4 = generate_operation_id("get", "/", existing)
    assert op4 == "getEndpoint"

    # Collision deduplication
    existing.add("getUsers")
    op5 = generate_operation_id("get", "/users", existing)
    assert op5 == "getUsers_1"


def test_sanitize_operation_id():
    assert sanitize_operation_id("get-user-by-id") == "get-user-by-id"
    assert sanitize_operation_id("get users @ home!") == "get_users_home"
    assert sanitize_operation_id("###") == "operation"


def test_missing_operation_id_check_and_fix():
    rule = OperationIdRule()
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /orders/{orderId}:
    get:
      responses:
        '200':
          description: ok
""")
    diags = rule.check(spec, {})
    assert len(diags) == 1
    assert diags[0].rule_id == RuleId.MISSING_OPERATION_ID
    assert diags[0].severity == Severity.WARNING
    assert diags[0].fixable is True
    assert diags[0].fix_action.value == "getOrdersByOrderid"

    applied = rule.fix(spec, diags)
    assert applied == 1
    assert spec.data["paths"]["/orders/{orderId}"]["get"]["operationId"] == "getOrdersByOrderid"


def test_duplicate_operation_id_check_and_fix():
    rule = OperationIdRule()
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /users:
    get:
      operationId: findUsers
      responses:
        '200':
          description: ok
    post:
      operationId: findUsers
      responses:
        '201':
          description: ok
""")
    diags = rule.check(spec, {})
    assert len(diags) == 1
    assert diags[0].rule_id == RuleId.DUPLICATE_OPERATION_ID
    assert diags[0].severity == Severity.ERROR
    assert diags[0].fixable is True
    assert diags[0].fix_action.value == "findUsers_2"

    applied = rule.fix(spec, diags)
    assert applied == 1
    assert spec.data["paths"]["/users"]["post"]["operationId"] == "findUsers_2"


def test_invalid_operation_id_check_and_fix():
    rule = OperationIdRule()
    spec = load_spec_from_text("""
openapi: 3.0.3
paths:
  /items:
    get:
      operationId: "get items (all)!"
      responses:
        '200':
          description: ok
""")
    diags = rule.check(spec, {})
    assert len(diags) == 1
    assert diags[0].rule_id == RuleId.INVALID_OPERATION_ID
    assert diags[0].severity == Severity.WARNING
    assert diags[0].fixable is True
    assert diags[0].fix_action.value == "get_items_all"

    applied = rule.fix(spec, diags)
    assert applied == 1
    assert spec.data["paths"]["/items"]["get"]["operationId"] == "get_items_all"
