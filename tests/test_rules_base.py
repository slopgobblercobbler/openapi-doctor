"""Tests for openapi_doctor.rules.base."""

import pytest
from openapi_doctor.models import Diagnostic, FixAction, Severity
from openapi_doctor.parser import load_spec_from_text
from openapi_doctor.rules.base import (
    BaseRule,
    get_default_status_description,
    iter_operations,
)


class DummyRule(BaseRule):
    rule_id = "dummy-rule"
    default_severity = Severity.WARNING
    description = "Dummy rule for base testing"

    def check(self, spec, context):
        return []


def test_get_default_status_description():
    assert get_default_status_description("200") == "OK"
    assert get_default_status_description("404") == "Not Found"
    assert get_default_status_description("500") == "Internal Server Error"
    assert get_default_status_description("default") == "Default response"
    assert get_default_status_description("2XX") == "Successful response"
    assert get_default_status_description("3XX") == "Redirection response"
    assert get_default_status_description("4XX") == "Client error"
    assert get_default_status_description("5XX") == "Server error"
    assert get_default_status_description("207") == "Successful operation (207)"
    assert get_default_status_description("418") == "Client error (418)"
    assert get_default_status_description("509") == "Server error (509)"
    assert get_default_status_description("unknown") == "Response for status unknown"


def test_iter_operations():
    yaml_text = """
openapi: 3.0.0
paths:
  /users:
    get:
      summary: List
    post:
      summary: Create
  /users/{id}:
    delete:
      summary: Delete
  /empty: {}
"""
    spec = load_spec_from_text(yaml_text)
    ops = list(iter_operations(spec.data))
    assert len(ops) == 3

    paths = [op[0] for op in ops]
    methods = [op[1] for op in ops]
    assert "/users" in paths
    assert "/users/{id}" in paths
    assert "get" in methods
    assert "post" in methods
    assert "delete" in methods


def test_base_rule_apply_action():
    rule = DummyRule()
    doc = {"info": {"title": "Test"}}

    # Test "set"
    action_set = FixAction(
        rule_id="dummy",
        description="set desc",
        target_pointer="/info/description",
        action_type="set",
        value="A new description",
    )
    assert rule.apply_action(doc, action_set) is True
    assert doc["info"]["description"] == "A new description"

    # Test "delete"
    action_del = FixAction(
        rule_id="dummy",
        description="del desc",
        target_pointer="/info/description",
        action_type="delete",
    )
    assert rule.apply_action(doc, action_del) is True
    assert "description" not in doc["info"]

    # Delete non-existent
    assert rule.apply_action(doc, action_del) is False

    # Test "append"
    action_append_new = FixAction(
        rule_id="dummy",
        description="append tags",
        target_pointer="/tags",
        action_type="append",
        value={"name": "tag1"},
    )
    assert rule.apply_action(doc, action_append_new) is True
    assert doc["tags"] == [{"name": "tag1"}]

    action_append_existing = FixAction(
        rule_id="dummy",
        description="append tags 2",
        target_pointer="/tags",
        action_type="append",
        value={"name": "tag2"},
    )
    assert rule.apply_action(doc, action_append_existing) is True
    assert len(doc["tags"]) == 2

    # Test "merge"
    action_merge_new = FixAction(
        rule_id="dummy",
        description="merge new",
        target_pointer="/components/schemas",
        action_type="merge",
        value={"User": {"type": "object"}},
    )
    assert rule.apply_action(doc, action_merge_new) is True
    assert "User" in doc["components"]["schemas"]

    action_merge_existing = FixAction(
        rule_id="dummy",
        description="merge existing",
        target_pointer="/components/schemas",
        action_type="merge",
        value={"Role": {"type": "string"}},
    )
    assert rule.apply_action(doc, action_merge_existing) is True
    assert "User" in doc["components"]["schemas"]
    assert "Role" in doc["components"]["schemas"]

    # Invalid empty pointer
    action_empty = FixAction(
        rule_id="dummy",
        description="empty",
        target_pointer="",
        action_type="set",
        value="x",
    )
    assert rule.apply_action(doc, action_empty) is False

    # Invalid action type
    action_unknown = FixAction(
        rule_id="dummy",
        description="unknown",
        target_pointer="/info/title",
        action_type="unknown_action",
        value="x",
    )
    assert rule.apply_action(doc, action_unknown) is False


def test_base_rule_fix_method():
    rule = DummyRule()
    spec = load_spec_from_text("openapi: 3.0.0\ninfo:\n  title: Old\n")
    diag = Diagnostic(
        rule_id="dummy-rule",
        message="title issue",
        fixable=True,
        fix_action=FixAction(
            rule_id="dummy-rule",
            description="Update title",
            target_pointer="/info/title",
            action_type="set",
            value="New Title",
        ),
    )
    unrelated_diag = Diagnostic(
        rule_id="other-rule",
        message="other issue",
        fixable=True,
    )

    applied = rule.fix(spec, [diag, unrelated_diag])
    assert applied == 1
    assert spec.data["info"]["title"] == "New Title"
