# rules/rule_factory.py

from rules.custom_rule_models import (
    CustomRule,
    CustomRuleCondition,
    CustomRuleMatchMode,
    CustomRuleOperator,
    CustomRuleRightValueType,
    CustomRuleSeverity,
)


class RuleFactory:

    @staticmethod
    def create_blank_check(
        field_name,
        severity=CustomRuleSeverity.MEDIUM,
    ):
        return CustomRule(
            name=f"{field_name} Blank Check",
            severity=severity,
            enabled=True,
            match_mode=CustomRuleMatchMode.ALL,
            conditions=[
                CustomRuleCondition(
                    left_field=field_name,
                    operator=CustomRuleOperator.IS_BLANK,
                    right_value_type=CustomRuleRightValueType.BLANK,
                    right_value=None,
                )
            ],
            message=f"{field_name} is blank.",
        )

    @staticmethod
    def create_field_comparison(
        *,
        rule_name,
        left_field,
        operator,
        right_field,
        severity=CustomRuleSeverity.MEDIUM,
        message="",
    ):
        return CustomRule(
            name=rule_name,
            severity=severity,
            enabled=True,
            match_mode=CustomRuleMatchMode.ALL,
            conditions=[
                CustomRuleCondition(
                    left_field=left_field,
                    operator=operator,
                    right_value_type=(
                        CustomRuleRightValueType.FIELD
                    ),
                    right_value=right_field,
                )
            ],
            message=message,
        )

    @staticmethod
    def create_value_comparison(
        *,
        rule_name,
        left_field,
        operator,
        value,
        severity=CustomRuleSeverity.MEDIUM,
        message="",
    ):
        return CustomRule(
            name=rule_name,
            severity=severity,
            enabled=True,
            match_mode=CustomRuleMatchMode.ALL,
            conditions=[
                CustomRuleCondition(
                    left_field=left_field,
                    operator=operator,
                    right_value_type=(
                        CustomRuleRightValueType.VALUE
                    ),
                    right_value=value,
                )
            ],
            message=message,
        )

    @staticmethod
    def create_range_check(
        *,
        field_name,
        minimum_value,
        maximum_value,
        severity=CustomRuleSeverity.MEDIUM,
    ):
        return CustomRule(
            name=f"{field_name} Range Check",
            severity=severity,
            enabled=True,
            match_mode=CustomRuleMatchMode.ANY,
            conditions=[
                CustomRuleCondition(
                    left_field=field_name,
                    operator=CustomRuleOperator.LESS_THAN,
                    right_value_type=(
                        CustomRuleRightValueType.VALUE
                    ),
                    right_value=minimum_value,
                ),
                CustomRuleCondition(
                    left_field=field_name,
                    operator=CustomRuleOperator.GREATER_THAN,
                    right_value_type=(
                        CustomRuleRightValueType.VALUE
                    ),
                    right_value=maximum_value,
                ),
            ],
            message=(
                f"{field_name} is outside the "
                f"allowed range."
            ),
        )

    @staticmethod
    def create_benchmark_variance_check(
        *,
        price_field,
        benchmark_field,
        variance_percent,
        severity=CustomRuleSeverity.MEDIUM,
    ):
        return CustomRule(
            name=f"{price_field} Benchmark Variance",
            severity=severity,
            enabled=True,
            match_mode=CustomRuleMatchMode.ALL,
            conditions=[
                CustomRuleCondition(
                    left_field=price_field,
                    operator=CustomRuleOperator.GREATER_THAN,
                    right_value_type=(
                        CustomRuleRightValueType.FIELD
                    ),
                    right_value=benchmark_field,
                )
            ],
            message=(
                f"{price_field} exceeds benchmark "
                f"by more than {variance_percent}%."
            ),
        )