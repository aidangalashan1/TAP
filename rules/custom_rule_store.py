# rules/custom_rule_store.py

import json
from pathlib import Path

from rules.custom_rule_models import (
    CustomRule,
    CustomRuleCondition,
    CustomRuleMatchMode,
    CustomRuleOperator,
    CustomRuleRightValueType,
    CustomRuleSeverity,
    CustomRuleType,
    OutlierMethod,
)


class CustomRuleStore:
    def __init__(self, file_path="custom_rules.json"):
        self.file_path = Path(file_path)

    def load_rules(self):
        if not self.file_path.exists():
            return []

        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            return []

        rules = []

        for rule_data in data:
            rule = self._rule_from_dict(rule_data)

            if rule is not None:
                rules.append(rule)

        return rules

    def save_rules(self, rules):
        data = [
            self._rule_to_dict(rule)
            for rule in rules
        ]

        parent = self.file_path.parent

        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)

        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    def delete_all_rules(self):
        if self.file_path.exists():
            self.file_path.unlink()

    def rule_count(self):
        return len(self.load_rules())

    def _rule_from_dict(self, data):
        try:
            conditions = []

            for condition_data in data.get("conditions", []):
                conditions.append(
                    CustomRuleCondition(
                        left_field=condition_data.get("left_field", ""),
                        operator=self._parse_operator(
                            condition_data.get("operator", "EQUALS")
                        ),
                        right_value_type=self._parse_right_value_type(
                            condition_data.get("right_value_type", "VALUE")
                        ),
                        right_value=condition_data.get("right_value"),
                    )
                )

            return CustomRule(
                name=data.get("name", "Unnamed Rule"),
                severity=self._parse_severity(data.get("severity", "MEDIUM")),
                conditions=conditions,
                enabled=bool(data.get("enabled", True)),
                match_mode=self._parse_match_mode(data.get("match_mode", "ALL")),
                sheet_name=data.get("sheet_name"),
                message=data.get("message", ""),
                description=data.get("description", ""),
                tags=data.get("tags", []),
                rule_type=self._parse_rule_type(
                    data.get("rule_type", "ADVANCED_RULE")
                ),
                check_blanks=bool(data.get("check_blanks", False)),
                check_zeroes=bool(data.get("check_zeroes", False)),
                check_negative_values=bool(
                    data.get("check_negative_values", False)
                ),
                check_duplicates=bool(data.get("check_duplicates", False)),
                check_outliers=bool(data.get("check_outliers", False)),
                outlier_method=self._parse_outlier_method(
                    data.get("outlier_method", "IQR")
                ),
                outlier_tolerance=float(data.get("outlier_tolerance", 1.5)),
                target_fields=data.get("target_fields", []),
            )

        except Exception:
            return None

    def _rule_to_dict(self, rule):
        return {
            "name": rule.name,
            "severity": self._enum_value(rule.severity),
            "enabled": rule.enabled,
            "match_mode": self._enum_value(rule.match_mode),
            "sheet_name": rule.sheet_name,
            "message": rule.message,
            "description": rule.description,
            "tags": rule.tags,
            "rule_type": self._enum_value(rule.rule_type),
            "check_blanks": rule.check_blanks,
            "check_zeroes": rule.check_zeroes,
            "check_negative_values": rule.check_negative_values,
            "check_duplicates": rule.check_duplicates,
            "check_outliers": rule.check_outliers,
            "outlier_method": self._enum_value(rule.outlier_method),
            "outlier_tolerance": rule.outlier_tolerance,
            "target_fields": rule.target_fields,
            "conditions": [
                {
                    "left_field": condition.left_field,
                    "operator": self._enum_value(condition.operator),
                    "right_value_type": self._enum_value(
                        condition.right_value_type
                    ),
                    "right_value": condition.right_value,
                }
                for condition in rule.conditions
            ],
        }

    def _enum_value(self, value):
        if hasattr(value, "value"):
            return value.value

        return str(value)

    def _parse_severity(self, value):
        try:
            return CustomRuleSeverity(str(value))
        except ValueError:
            return CustomRuleSeverity.MEDIUM

    def _parse_match_mode(self, value):
        try:
            return CustomRuleMatchMode(str(value))
        except ValueError:
            return CustomRuleMatchMode.ALL

    def _parse_operator(self, value):
        try:
            return CustomRuleOperator(str(value))
        except ValueError:
            return CustomRuleOperator.EQUALS

    def _parse_right_value_type(self, value):
        try:
            return CustomRuleRightValueType(str(value))
        except ValueError:
            return CustomRuleRightValueType.VALUE

    def _parse_rule_type(self, value):
        try:
            return CustomRuleType(str(value))
        except ValueError:
            return CustomRuleType.ADVANCED_RULE

    def _parse_outlier_method(self, value):
        try:
            return OutlierMethod(str(value))
        except ValueError:
            return OutlierMethod.IQR