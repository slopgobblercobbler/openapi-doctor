"""Rule registry for openapi-doctor."""

from __future__ import annotations

from typing import Dict, List, Type

from openapi_doctor.models import RuleId
from openapi_doctor.rules.base import BaseRule
from openapi_doctor.rules.components import UnusedComponentRule
from openapi_doctor.rules.operations import OperationIdRule
from openapi_doctor.rules.parameters import PathParameterRule
from openapi_doctor.rules.references import UndefinedSchemaRule
from openapi_doctor.rules.responses import MissingResponseDescriptionRule
from openapi_doctor.rules.security import SecuritySchemeMismatchRule

DEFAULT_RULES: List[BaseRule] = [
    MissingResponseDescriptionRule(),
    UndefinedSchemaRule(),
    UnusedComponentRule(),
    OperationIdRule(),
    SecuritySchemeMismatchRule(),
    PathParameterRule(),
]

RULE_REGISTRY: Dict[str, BaseRule] = {
    RuleId.MISSING_RESPONSE_DESCRIPTION: MissingResponseDescriptionRule(),
    RuleId.BROKEN_REF: UndefinedSchemaRule(),
    RuleId.UNDEFINED_SCHEMA: UndefinedSchemaRule(),
    RuleId.UNUSED_COMPONENT: UnusedComponentRule(),
    RuleId.MISSING_OPERATION_ID: OperationIdRule(),
    RuleId.DUPLICATE_OPERATION_ID: OperationIdRule(),
    RuleId.INVALID_OPERATION_ID: OperationIdRule(),
    RuleId.UNDEFINED_SECURITY_SCHEME: SecuritySchemeMismatchRule(),
    RuleId.INVALID_SECURITY_SCOPE: SecuritySchemeMismatchRule(),
    RuleId.MISSING_PATH_PARAMETER: PathParameterRule(),
    RuleId.UNUSED_PATH_PARAMETER: PathParameterRule(),
}


def get_default_rules() -> List[BaseRule]:
    """Returns a fresh list of default rules."""
    return [
        MissingResponseDescriptionRule(),
        UndefinedSchemaRule(),
        UnusedComponentRule(),
        OperationIdRule(),
        SecuritySchemeMismatchRule(),
        PathParameterRule(),
    ]
