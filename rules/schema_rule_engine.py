# rules/schema_rule_engine.py

import math
from statistics import mean
from statistics import pstdev

from models.pricing_models import Finding
from models.pricing_models import Severity

from rules.custom_rule_models import (
    CustomRuleMatchMode,
    CustomRuleOperator,
    CustomRuleRightValueType,
    CustomRuleSeverity,
    CustomRuleType,
    OutlierMethod,
)


class SchemaRuleEngine:
    def execute(self, records, custom_rules):
        findings = []

        if not custom_rules:
            return findings

        for rule in custom_rules:
            if not rule.enabled:
                continue

            if rule.rule_type == CustomRuleType.QUICK_RULES:
                findings.extend(
                    self._execute_quick_rules(records, rule)
                )
            else:
                findings.extend(
                    self._execute_advanced_rule(records, rule)
                )

        return findings

    # ==================================================
    # Quick Rules
    # ==================================================

    def _execute_quick_rules(self, records, rule):
        findings = []

        target_fields = self._get_target_fields(records, rule)

        if rule.check_blanks:
            findings.extend(
                self._check_blanks(records, target_fields, rule)
            )

        if rule.check_zeroes:
            findings.extend(
                self._check_zeroes(records, target_fields, rule)
            )

        if rule.check_negative_values:
            findings.extend(
                self._check_negative_values(records, target_fields, rule)
            )

        if rule.check_duplicates:
            findings.extend(
                self._check_duplicates(records, target_fields, rule)
            )

        if rule.check_outliers:
            findings.extend(
                self._check_outliers(records, target_fields, rule)
            )

        return findings

    def _get_target_fields(self, records, rule):
        if rule.target_fields:
            return list(rule.target_fields)

        fields = set()

        for record in records:
            for field_name in record.values.keys():
                fields.add(field_name)

        return sorted(fields)

    def _check_blanks(self, records, fields, rule):
        findings = []

        for record in records:
            for field_name in fields:
                value = record.get_value(field_name)

                if self._is_blank(value):
                    findings.append(
                        self._build_finding(
                            record=record,
                            field_name=field_name,
                            value=value,
                            rule=rule,
                            reason="Blank value detected.",
                        )
                    )

        return findings

    def _check_zeroes(self, records, fields, rule):
        findings = []

        for record in records:
            for field_name in fields:
                value = self._to_float_or_none(
                    record.get_value(field_name)
                )

                if value is None:
                    continue

                if value == 0:
                    findings.append(
                        self._build_finding(
                            record=record,
                            field_name=field_name,
                            value=value,
                            rule=rule,
                            reason="Zero value detected.",
                        )
                    )

        return findings

    def _check_negative_values(self, records, fields, rule):
        findings = []

        for record in records:
            for field_name in fields:
                value = self._to_float_or_none(
                    record.get_value(field_name)
                )

                if value is None:
                    continue

                if value < 0:
                    findings.append(
                        self._build_finding(
                            record=record,
                            field_name=field_name,
                            value=value,
                            rule=rule,
                            reason="Negative value detected.",
                        )
                    )

        return findings

    def _check_duplicates(self, records, fields, rule):
        findings = []

        for field_name in fields:
            values = {}

            for record in records:
                raw_value = record.get_value(field_name)

                if self._is_blank(raw_value):
                    continue

                key = str(raw_value).strip().lower()

                if key not in values:
                    values[key] = []

                values[key].append(record)

            for key, duplicate_records in values.items():
                if len(duplicate_records) <= 1:
                    continue

                for record in duplicate_records:
                    findings.append(
                        self._build_finding(
                            record=record,
                            field_name=field_name,
                            value=record.get_value(field_name),
                            rule=rule,
                            reason=(
                                "Duplicate value detected "
                                f"for field '{field_name}'."
                            ),
                        )
                    )

        return findings

    def _check_outliers(self, records, fields, rule):
        if rule.outlier_method == OutlierMethod.Z_SCORE:
            return self._check_z_score_outliers(records, fields, rule)

        return self._check_iqr_outliers(records, fields, rule)

    def _check_iqr_outliers(self, records, fields, rule):
        findings = []

        for field_name in fields:
            values = self._numeric_values_for_field(records, field_name)

            if len(values) < 4:
                continue

            numeric_values = sorted(value for _, value in values)

            q1 = self._percentile(numeric_values, 25)
            q3 = self._percentile(numeric_values, 75)

            iqr = q3 - q1

            if iqr == 0:
                continue

            lower_bound = q1 - (rule.outlier_tolerance * iqr)
            upper_bound = q3 + (rule.outlier_tolerance * iqr)

            for record, value in values:
                if value < lower_bound or value > upper_bound:
                    findings.append(
                        self._build_finding(
                            record=record,
                            field_name=field_name,
                            value=value,
                            rule=rule,
                            reason=(
                                "Outlier detected using IQR. "
                                f"Value {value} is outside "
                                f"{round(lower_bound, 2)} to "
                                f"{round(upper_bound, 2)}."
                            ),
                        )
                    )

        return findings

    def _check_z_score_outliers(self, records, fields, rule):
        findings = []

        for field_name in fields:
            values = self._numeric_values_for_field(records, field_name)

            if len(values) < 3:
                continue

            number_values = [value for _, value in values]

            average = mean(number_values)
            standard_deviation = pstdev(number_values)

            if standard_deviation == 0:
                continue

            for record, value in values:
                z_score = abs((value - average) / standard_deviation)

                if z_score >= rule.outlier_tolerance:
                    findings.append(
                        self._build_finding(
                            record=record,
                            field_name=field_name,
                            value=value,
                            rule=rule,
                            reason=(
                                "Outlier detected using Z score. "
                                f"Z score: {round(z_score, 2)}."
                            ),
                        )
                    )

        return findings

    def _numeric_values_for_field(self, records, field_name):
        values = []

        for record in records:
            numeric_value = self._to_float_or_none(
                record.get_value(field_name)
            )

            if numeric_value is None:
                continue

            values.append((record, numeric_value))

        return values

    # ==================================================
    # Advanced Rules
    # ==================================================

    def _execute_advanced_rule(self, records, rule):
        findings = []

        for record in records:
            if rule.sheet_name and record.sheet_name != rule.sheet_name:
                continue

            results = []

            for condition in rule.conditions:
                results.append(
                    self._evaluate_condition(record, condition)
                )

            if not results:
                continue

            triggered = self._combine_results(
                results,
                rule.match_mode,
            )

            if not triggered:
                continue

            primary_field = rule.conditions[0].left_field

            findings.append(
                self._build_finding(
                    record=record,
                    field_name=primary_field,
                    value=record.get_value(primary_field),
                    rule=rule,
                    reason=rule.message or f"Rule triggered: {rule.name}",
                )
            )

        return findings

    def _evaluate_condition(self, record, condition):
        left_value = record.get_value(condition.left_field)
        right_value = self._resolve_right_value(record, condition)

        operator_value = self._operator_value(condition.operator)

        if operator_value == CustomRuleOperator.IS_BLANK.value:
            return self._is_blank(left_value)

        if operator_value == CustomRuleOperator.IS_NOT_BLANK.value:
            return not self._is_blank(left_value)

        if operator_value == CustomRuleOperator.CONTAINS.value:
            return self._contains(left_value, right_value)

        if operator_value == CustomRuleOperator.NOT_CONTAINS.value:
            return not self._contains(left_value, right_value)

        left_normalised = self._normalise(left_value)
        right_normalised = self._normalise(right_value)

        if left_normalised is None:
            return False

        if right_normalised is None:
            return False

        try:
            if operator_value == CustomRuleOperator.EQUALS.value:
                return left_normalised == right_normalised

            if operator_value == CustomRuleOperator.NOT_EQUALS.value:
                return left_normalised != right_normalised

            if operator_value == CustomRuleOperator.GREATER_THAN.value:
                return left_normalised > right_normalised

            if operator_value == CustomRuleOperator.GREATER_THAN_OR_EQUAL.value:
                return left_normalised >= right_normalised

            if operator_value == CustomRuleOperator.LESS_THAN.value:
                return left_normalised < right_normalised

            if operator_value == CustomRuleOperator.LESS_THAN_OR_EQUAL.value:
                return left_normalised <= right_normalised

        except TypeError:
            return False

        return False

    def _resolve_right_value(self, record, condition):
        right_type = self._right_type_value(condition.right_value_type)

        if right_type == CustomRuleRightValueType.FIELD.value:
            return record.get_value(condition.right_value)

        if right_type == CustomRuleRightValueType.VALUE.value:
            return condition.right_value

        if right_type == CustomRuleRightValueType.BLANK.value:
            return None

        return condition.right_value

    def _combine_results(self, results, match_mode):
        match_mode_value = self._match_mode_value(match_mode)

        if match_mode_value == CustomRuleMatchMode.ANY.value:
            return any(results)

        return all(results)

    # ==================================================
    # Finding Helpers
    # ==================================================

    def _build_finding(self, record, field_name, value, rule, reason):
        return Finding(
            supplier_name="",
            severity=self._map_severity(rule.severity),
            worksheet_name=record.sheet_name,
            cell_reference=record.get_cell_reference(field_name),
            item_code="",
            item_description=f"{record.region_name} | {field_name}",
            actual_value="" if value is None else str(value),
            reason=reason,
            comparator_value=None,
            deviation_percent=None,
            suggested_clarification=(
                rule.message
                or reason
            ),
        )

    def _map_severity(self, severity):
        value = str(severity).upper()

        if "HIGH" in value:
            return Severity.HIGH

        if "MEDIUM" in value:
            return Severity.MEDIUM

        if "LOW" in value:
            return Severity.LOW

        return Severity.INFO

    # ==================================================
    # Utility
    # ==================================================

    def _is_blank(self, value):
        if value is None:
            return True

        if isinstance(value, str):
            return value.strip() == ""

        return False

    def _contains(self, left_value, right_value):
        if left_value is None or right_value is None:
            return False

        return str(right_value).lower() in str(left_value).lower()

    def _normalise(self, value):
        if value is None:
            return None

        numeric = self._to_float_or_none(value)

        if numeric is not None:
            return numeric

        return str(value).strip().lower()

    def _to_float_or_none(self, value):
        if value is None:
            return None

        if isinstance(value, bool):
            return None

        if isinstance(value, int) or isinstance(value, float):
            if math.isnan(value):
                return None

            return float(value)

        text = str(value).strip()

        if text == "":
            return None

        cleaned = text.replace(",", "")
        cleaned = cleaned.replace("£", "")
        cleaned = cleaned.replace("%", "")

        try:
            return float(cleaned)
        except ValueError:
            return None

    def _percentile(self, values, percentile):
        if not values:
            return 0

        index = (len(values) - 1) * (percentile / 100)
        lower = math.floor(index)
        upper = math.ceil(index)

        if lower == upper:
            return values[int(index)]

        lower_value = values[lower]
        upper_value = values[upper]

        return lower_value + ((upper_value - lower_value) * (index - lower))

    def _operator_value(self, operator):
        return operator.value if hasattr(operator, "value") else str(operator)

    def _right_type_value(self, value):
        return value.value if hasattr(value, "value") else str(value)

    def _match_mode_value(self, value):
        return value.value if hasattr(value, "value") else str(value)