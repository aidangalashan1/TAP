# rules/custom_rule_models.py

from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any


class CustomRuleSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class CustomRuleMatchMode(str, Enum):
    ALL = "ALL"
    ANY = "ANY"


class CustomRuleOperator(str, Enum):
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"

    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"

    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"

    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"

    IS_BLANK = "IS_BLANK"
    IS_NOT_BLANK = "IS_NOT_BLANK"


class CustomRuleRightValueType(str, Enum):
    FIELD = "FIELD"
    VALUE = "VALUE"
    BLANK = "BLANK"


class CustomRuleType(str, Enum):
    QUICK_RULES = "QUICK_RULES"
    ADVANCED_RULE = "ADVANCED_RULE"


class OutlierMethod(str, Enum):
    IQR = "IQR"
    Z_SCORE = "Z_SCORE"


@dataclass
class CustomRuleCondition:
    left_field: str
    operator: CustomRuleOperator
    right_value_type: CustomRuleRightValueType
    right_value: Any = None


@dataclass
class CustomRule:
    name: str
    severity: CustomRuleSeverity
    conditions: list[CustomRuleCondition] = field(default_factory=list)

    enabled: bool = True
    match_mode: CustomRuleMatchMode = CustomRuleMatchMode.ALL
    sheet_name: str | None = None

    message: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)

    rule_type: CustomRuleType = CustomRuleType.ADVANCED_RULE

    # Quick-rule settings
    check_blanks: bool = False
    check_zeroes: bool = False
    check_negative_values: bool = False
    check_duplicates: bool = False
    check_outliers: bool = False

    outlier_method: OutlierMethod = OutlierMethod.IQR
    outlier_tolerance: float = 1.5

    # If empty, applies to all fields detected in records.
    target_fields: list[str] = field(default_factory=list)