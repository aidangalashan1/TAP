# rules/custom_rule_engine.py

from models.pricing_models import Finding
from models.pricing_models import Severity
from rules.custom_rule_models import CustomRuleMatchMode
from rules.custom_rule_models import CustomRuleOperator
from rules.custom_rule_models import CustomRuleRightValueType


class CustomRuleEngine:
    # Evaluates user-defined rules against row-based workbook data.
    #
    # Rules are expected to be "flag when true".
    #
    # Example:
    # Weekday Rate <= Weekend Rate
    # AND
    # Weekday Rate <= 50
    #
    # If both conditions evaluate to True, the rule creates a Finding.

    def execute(self, workbook_rows, custom_rules):
        findings = []

        for custom_rule in custom_rules:
            if not custom_rule.enabled:
                continue

            rule_findings = self._execute_rule(
                workbook_rows,
                custom_rule
            )

            findings.extend(rule_findings)

        return findings

    def _execute_rule(self, workbook_rows, custom_rule):
        findings = []

        for workbook_row in workbook_rows:
            if custom_rule.sheet_name:
                if workbook_row.sheet_name != custom_rule.sheet_name:
                    continue

            condition_results = []

            for condition in custom_rule.conditions:
                result = self._evaluate_condition(
                    workbook_row,
                    condition
                )

                condition_results.append(result)

            if not condition_results:
                continue

            rule_triggered = self._combine_results(
                condition_results,
                custom_rule.match_mode
            )

            if not rule_triggered:
                continue

            finding = self._create_finding(
                workbook_row,
                custom_rule
            )

            findings.append(finding)

        return findings

    def _evaluate_condition(self, workbook_row, condition):
        left_value = workbook_row.values.get(
            condition.left_field
        )

        right_value = self._resolve_right_value(
            workbook_row,
            condition
        )

        operator_value = self._get_operator_value(
            condition.operator
        )

        if operator_value == CustomRuleOperator.IS_BLANK.value:
            return self._is_blank(left_value)

        if operator_value == CustomRuleOperator.IS_NOT_BLANK.value:
            return not self._is_blank(left_value)

        if operator_value == CustomRuleOperator.CONTAINS.value:
            return self._contains(left_value, right_value)

        if operator_value == CustomRuleOperator.NOT_CONTAINS.value:
            return not self._contains(left_value, right_value)

        left_comparable = self._to_comparable_value(left_value)
        right_comparable = self._to_comparable_value(right_value)

        if operator_value == CustomRuleOperator.EQUALS.value:
            return left_comparable == right_comparable

        if operator_value == CustomRuleOperator.NOT_EQUALS.value:
            return left_comparable != right_comparable

        if left_comparable is None:
            return False

        if right_comparable is None:
            return False

        try:
            if operator_value == CustomRuleOperator.GREATER_THAN.value:
                return left_comparable > right_comparable

            if operator_value == CustomRuleOperator.GREATER_THAN_OR_EQUAL.value:
                return left_comparable >= right_comparable

            if operator_value == CustomRuleOperator.LESS_THAN.value:
                return left_comparable < right_comparable

            if operator_value == CustomRuleOperator.LESS_THAN_OR_EQUAL.value:
                return left_comparable <= right_comparable

        except TypeError:
            return False

        return False

    def _resolve_right_value(self, workbook_row, condition):
        right_type = self._get_right_value_type(
            condition.right_value_type
        )

        if right_type == CustomRuleRightValueType.FIELD.value:
            return workbook_row.values.get(
                condition.right_value
            )

        if right_type == CustomRuleRightValueType.VALUE.value:
            return condition.right_value

        if right_type == CustomRuleRightValueType.BLANK.value:
            return None

        return condition.right_value

    def _combine_results(self, condition_results, match_mode):
        match_mode_value = self._get_match_mode_value(
            match_mode
        )

        if match_mode_value == CustomRuleMatchMode.ANY.value:
            return any(condition_results)

        return all(condition_results)

    def _create_finding(self, workbook_row, custom_rule):
        primary_field = self._get_primary_field(custom_rule)

        cell_reference = workbook_row.cell_references.get(
            primary_field,
            ""
        )

        actual_value = workbook_row.values.get(
            primary_field,
            ""
        )

        message = custom_rule.message

        if not message:
            message = (
                f"Custom rule triggered: {custom_rule.name}"
            )

        item_code = self._get_first_available_value(
            workbook_row,
            [
                "Item Code",
                "Asset Ref",
                "NR Asset Ref for COOM",
                "NR Asset Reference for COOM",
            ]
        )

        item_description = self._get_first_available_value(
            workbook_row,
            [
                "Description",
                "Item Description",
                "Type of Road Rail Vehicle",
                "Attachment Type",
                "Description of attachment",
            ]
        )

        if not item_description:
            item_description = f"Row {workbook_row.row_number}"

        finding = Finding(
            supplier_name="Custom Rule",
            severity=self._map_severity(custom_rule.severity),
            worksheet_name=workbook_row.sheet_name,
            cell_reference=cell_reference,
            item_code=str(item_code),
            item_description=str(item_description),
            actual_value=str(actual_value),
            reason=message,
            comparator_value=None,
            deviation_percent=None,
            suggested_clarification=(
                "Please review and confirm this entry. "
                f"The user-defined rule '{custom_rule.name}' "
                "was triggered."
            )
        )

        return finding

    def _get_primary_field(self, custom_rule):
        if not custom_rule.conditions:
            return ""

        return custom_rule.conditions[0].left_field

    def _get_first_available_value(self, workbook_row, field_names):
        for field_name in field_names:
            value = workbook_row.values.get(field_name)

            if value is None:
                continue

            if isinstance(value, str):
                if value.strip() == "":
                    continue

            return value

        return ""

    def _map_severity(self, custom_rule_severity):
        severity_value = str(custom_rule_severity)

        if "." in severity_value:
            severity_value = severity_value.split(".")[-1]

        severity_value = severity_value.replace("'", "")
        severity_value = severity_value.upper()

        if severity_value == "HIGH":
            return Severity.HIGH

        if severity_value == "MEDIUM":
            return Severity.MEDIUM

        if severity_value == "LOW":
            return Severity.LOW

        return Severity.INFO

    def _get_operator_value(self, operator):
        if isinstance(operator, CustomRuleOperator):
            return operator.value

        return str(operator)

    def _get_right_value_type(self, right_value_type):
        if isinstance(right_value_type, CustomRuleRightValueType):
            return right_value_type.value

        return str(right_value_type)

    def _get_match_mode_value(self, match_mode):
        if isinstance(match_mode, CustomRuleMatchMode):
            return match_mode.value

        return str(match_mode)

    def _to_comparable_value(self, value):
        if value is None:
            return None

        if isinstance(value, bool):
            return value

        if isinstance(value, int):
            return float(value)

        if isinstance(value, float):
            return float(value)

        if isinstance(value, str):
            cleaned_value = value.strip()

            if cleaned_value == "":
                return ""

            numeric_value = self._to_float_or_none(cleaned_value)

            if numeric_value is not None:
                return numeric_value

            return cleaned_value.lower()

        return value

    def _to_float_or_none(self, value):
        if value is None:
            return None

        if isinstance(value, bool):
            return None

        if isinstance(value, int):
            return float(value)

        if isinstance(value, float):
            return float(value)

        if isinstance(value, str):
            cleaned_value = value.strip()

            if cleaned_value == "":
                return None

            cleaned_value = cleaned_value.replace(",", "")
            cleaned_value = cleaned_value.replace("£", "")
            cleaned_value = cleaned_value.replace("%", "")

            try:
                return float(cleaned_value)
            except ValueError:
                return None

        return None

    def _contains(self, left_value, right_value):
        if left_value is None:
            return False

        if right_value is None:
            return False

        return (
            str(right_value).lower()
            in str(left_value).lower()
        )

    def _is_blank(self, value):
        if value is None:
            return True

        if isinstance(value, str):
            return value.strip() == ""

        return False