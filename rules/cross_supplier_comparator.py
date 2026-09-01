# rules/cross_supplier_comparator.py

import math
from statistics import mean
from statistics import pstdev

import config
from models.pricing_models import BenchmarkCoverage
from models.pricing_models import Finding
from models.pricing_models import FindingCategory
from models.pricing_models import Severity
from rules.custom_rule_models import ComparisonBasis
from rules.custom_rule_models import OutlierMethod

# Cap on how many distinct field names are reported by name in a
# coverage breakdown - beyond this it's more useful as "N other
# fields" than a wall of individual entries.
MAX_REPORTED_UNMATCHED_FIELDS = 15


class CrossSupplierComparator:
    """
    Compares the same confirmed field/row across supplier
    workbooks, either against a benchmark workbook or
    statistically against the other suppliers' responses.

    Records passed in must share the same field/row identity
    across suppliers, i.e. they were built from the same
    (template-derived) WorkbookSchema via SchemaBuilder.build_records.
    """

    def __init__(
        self,
        benchmark_threshold_percent=config.DEFAULT_BENCHMARK_THRESHOLD_PERCENT,
        outlier_method=OutlierMethod.Z_SCORE,
        outlier_tolerance=config.DEFAULT_STANDARD_DEVIATION_THRESHOLD,
    ):
        self.benchmark_threshold_percent = benchmark_threshold_percent
        self.outlier_method = outlier_method
        self.outlier_tolerance = outlier_tolerance

    # ==================================================
    # Benchmark Coverage
    # ==================================================

    def compute_benchmark_coverage(self, supplier_records, benchmark_records):
        """
        For every supplier, how many of their submitted fields could
        actually be checked against the benchmark workbook - i.e. the
        benchmark has a numeric value at the same (sheet, row, field)
        identity - regardless of whether the value differed enough to
        be flagged. Lets the user confirm benchmark attachment is
        complete before trusting the comparison findings.

        supplier_records: dict[supplier_name, list[DataRecord]]
        benchmark_records: list[DataRecord] or None

        Returns dict[supplier_name, BenchmarkCoverage].
        """

        benchmark_lookup = self._index_by_key(benchmark_records or [])

        coverage_by_supplier = {}

        for supplier_name, records in supplier_records.items():

            coverage = BenchmarkCoverage()
            unmatched_by_sheet = {}
            unmatched_by_field = {}

            for record in records:
                for field_name, raw_value in record.values.items():

                    if self._is_blank(raw_value):
                        continue

                    coverage.total_fields += 1

                    key = self._key(record, field_name)
                    benchmark_value = benchmark_lookup.get(key)
                    benchmark_number = self._to_float_or_none(
                        benchmark_value
                    )

                    if benchmark_number is not None:
                        coverage.matched_fields += 1
                        continue

                    unmatched_by_sheet[record.sheet_name] = (
                        unmatched_by_sheet.get(record.sheet_name, 0) + 1
                    )

                    unmatched_by_field[field_name] = (
                        unmatched_by_field.get(field_name, 0) + 1
                    )

            coverage.unmatched_by_sheet = unmatched_by_sheet
            coverage.unmatched_by_field = dict(
                sorted(
                    unmatched_by_field.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )[:MAX_REPORTED_UNMATCHED_FIELDS]
            )

            coverage_by_supplier[supplier_name] = coverage

        return coverage_by_supplier

    def _is_blank(self, value):
        if value is None:
            return True

        if isinstance(value, str):
            return value.strip() == ""

        return False

    # ==================================================
    # Rule-Driven Comparison
    # ==================================================

    def compare_using_rules(
        self,
        supplier_records,
        benchmark_records,
        comparison_rules,
        use_benchmark_default,
    ):
        """
        Runs each enabled COMPARISON_RULE rule's own scoped comparison
        (its sheet/field scope, with its own threshold/tolerance
        override where set), then runs the default comparison for
        every field not covered by one of those rules.

        comparison_rules: CustomRule list already filtered to enabled,
        rule_type == COMPARISON_RULE.
        use_benchmark_default: whether the uncovered-field default
        pass should compare to the benchmark (True) or statistically
        between responses (False) - mirrors the existing behaviour of
        picking one when no rule says otherwise.
        """

        benchmark_rules = [
            rule
            for rule in comparison_rules
            if rule.comparison_basis == ComparisonBasis.BENCHMARK
        ]

        between_response_rules = [
            rule
            for rule in comparison_rules
            if rule.comparison_basis == ComparisonBasis.BETWEEN_RESPONSES
        ]

        findings = []

        if benchmark_records is not None:
            for rule in benchmark_rules:
                findings.extend(
                    self.compare_to_benchmark(
                        supplier_records,
                        benchmark_records,
                        threshold_percent=rule.comparison_threshold_percent,
                        sheet_name=rule.sheet_name,
                        field_names=rule.target_fields or None,
                        rule_label=rule.name,
                    )
                )

        for rule in between_response_rules:
            findings.extend(
                self.compare_statistical(
                    supplier_records,
                    outlier_method=rule.outlier_method,
                    outlier_tolerance=rule.outlier_tolerance,
                    sheet_name=rule.sheet_name,
                    field_names=rule.target_fields or None,
                    rule_label=rule.name,
                )
            )

        if use_benchmark_default and benchmark_records is not None:
            findings.extend(
                self.compare_to_benchmark(
                    supplier_records,
                    benchmark_records,
                    excluded_rules=benchmark_rules,
                )
            )
        elif not use_benchmark_default:
            findings.extend(
                self.compare_statistical(
                    supplier_records,
                    excluded_rules=between_response_rules,
                )
            )

        return findings

    # ==================================================
    # Benchmark Comparison
    # ==================================================

    def compare_to_benchmark(
        self,
        supplier_records,
        benchmark_records,
        threshold_percent=None,
        sheet_name=None,
        field_names=None,
        excluded_rules=None,
        rule_label=None,
    ):
        """
        supplier_records: dict[supplier_name, list[DataRecord]]
        benchmark_records: list[DataRecord]

        threshold_percent/sheet_name/field_names: when given, scopes
        this call to a single comparison rule - only that sheet
        and/or those fields are compared, using this threshold
        instead of the comparator's default.

        excluded_rules: comparison rules (already run separately via
        their own scoped call) to skip here, so the default pass
        doesn't double-flag fields a rule already covers.
        """

        benchmark_lookup = self._index_by_key(benchmark_records)

        threshold = (
            threshold_percent
            if threshold_percent is not None
            else self.benchmark_threshold_percent
        )

        findings = []

        for supplier_name, records in supplier_records.items():
            for record in records:
                for field_name, raw_value in record.values.items():

                    if not self._matches_scope(
                        record.sheet_name, field_name, sheet_name, field_names
                    ):
                        continue

                    if excluded_rules and self._covered_by_any(
                        excluded_rules, record.sheet_name, field_name
                    ):
                        continue

                    key = self._key(record, field_name)
                    benchmark_value = benchmark_lookup.get(key)

                    if benchmark_value is None:
                        continue

                    actual = self._to_float_or_none(raw_value)
                    benchmark_number = self._to_float_or_none(benchmark_value)

                    if actual is None or benchmark_number is None:
                        continue

                    if benchmark_number == 0:
                        continue

                    deviation_percent = (
                        abs(actual - benchmark_number) / benchmark_number
                    ) * 100

                    if deviation_percent < threshold:
                        continue

                    comparator_label = "Benchmark Rate"

                    if rule_label:
                        comparator_label = f"Benchmark Rate (rule: {rule_label})"

                    findings.append(
                        Finding(
                            supplier_name=supplier_name,
                            severity=self._severity_for_deviation(
                                deviation_percent
                            ),
                            worksheet_name=record.sheet_name,
                            cell_reference=record.get_cell_reference(
                                field_name
                            ),
                            item_description=(
                                f"{record.record_reference} | {field_name}"
                            ),
                            actual_value=str(round(actual, 2)),
                            category=FindingCategory.BENCHMARK_COMPARISON.value,
                            comparator_value=str(round(benchmark_number, 2)),
                            comparator_label=comparator_label,
                            deviation_percent=round(deviation_percent, 2),
                            reason=(
                                f"Value differs from benchmark by "
                                f"{deviation_percent:.2f}%"
                            ),
                            suggested_clarification=(
                                f"Please confirm the submitted value for "
                                f"'{field_name}' ({record.record_reference}). "
                                f"It differs from the benchmark value of "
                                f"{benchmark_number:.2f} by "
                                f"{deviation_percent:.2f}%."
                            ),
                        )
                    )

        return findings

    # ==================================================
    # Cross-Supplier Statistical Comparison
    # ==================================================

    def compare_statistical(
        self,
        supplier_records,
        outlier_method=None,
        outlier_tolerance=None,
        sheet_name=None,
        field_names=None,
        excluded_rules=None,
        rule_label=None,
    ):
        """
        supplier_records: dict[supplier_name, list[DataRecord]]

        outlier_method/outlier_tolerance/sheet_name/field_names: when
        given, scopes this call to a single comparison rule - only
        that sheet and/or those fields are compared, using this
        method/tolerance instead of the comparator's default.

        excluded_rules: comparison rules (already run separately via
        their own scoped call) to skip here, so the default pass
        doesn't double-flag fields a rule already covers.
        """

        method = (
            outlier_method
            if outlier_method is not None
            else self.outlier_method
        )

        tolerance = (
            outlier_tolerance
            if outlier_tolerance is not None
            else self.outlier_tolerance
        )

        groups = {}

        for supplier_name, records in supplier_records.items():
            for record in records:
                for field_name, raw_value in record.values.items():

                    if not self._matches_scope(
                        record.sheet_name, field_name, sheet_name, field_names
                    ):
                        continue

                    if excluded_rules and self._covered_by_any(
                        excluded_rules, record.sheet_name, field_name
                    ):
                        continue

                    numeric_value = self._to_float_or_none(raw_value)

                    if numeric_value is None:
                        continue

                    key = self._key(record, field_name)

                    groups.setdefault(key, []).append(
                        (supplier_name, record, field_name, numeric_value)
                    )

        findings = []

        for entries in groups.values():

            if len(entries) < 3:
                continue

            if method == OutlierMethod.Z_SCORE:
                findings.extend(
                    self._z_score_outliers(entries, tolerance, rule_label)
                )
            else:
                findings.extend(
                    self._iqr_outliers(entries, tolerance, rule_label)
                )

        return findings

    def _z_score_outliers(self, entries, tolerance, rule_label=None):
        values = [entry[3] for entry in entries]

        average = mean(values)
        standard_deviation = pstdev(values)

        if standard_deviation == 0:
            return []

        findings = []

        comparator_label = "Supplier Group Average (Z-Score)"

        if rule_label:
            comparator_label = (
                f"Supplier Group Average (Z-Score, rule: {rule_label})"
            )

        for supplier_name, record, field_name, value in entries:

            z_score = abs((value - average) / standard_deviation)

            if z_score < tolerance:
                continue

            findings.append(
                self._build_statistical_finding(
                    supplier_name=supplier_name,
                    record=record,
                    field_name=field_name,
                    value=value,
                    comparator_value=average,
                    comparator_label=comparator_label,
                    severity=self._severity_for_z_score(z_score, tolerance),
                    reason=(
                        f"Value differs from the supplier group average "
                        f"({round(average, 2)}) by a Z score of "
                        f"{round(z_score, 2)}."
                    ),
                )
            )

        return findings

    def _iqr_outliers(self, entries, tolerance, rule_label=None):
        values = sorted(entry[3] for entry in entries)

        if len(values) < 4:
            return []

        q1 = self._percentile(values, 25)
        q3 = self._percentile(values, 75)

        iqr = q3 - q1

        if iqr == 0:
            return []

        lower_bound = q1 - (tolerance * iqr)
        upper_bound = q3 + (tolerance * iqr)

        findings = []

        comparator_label = "Supplier Group Median (IQR)"

        if rule_label:
            comparator_label = f"Supplier Group Median (IQR, rule: {rule_label})"

        for supplier_name, record, field_name, value in entries:

            if lower_bound <= value <= upper_bound:
                continue

            findings.append(
                self._build_statistical_finding(
                    supplier_name=supplier_name,
                    record=record,
                    field_name=field_name,
                    value=value,
                    comparator_value=(q1 + q3) / 2,
                    comparator_label=comparator_label,
                    severity=Severity.MEDIUM,
                    reason=(
                        f"Value is outside the expected supplier group "
                        f"range of {round(lower_bound, 2)} to "
                        f"{round(upper_bound, 2)} (IQR method)."
                    ),
                )
            )

        return findings

    def _build_statistical_finding(
        self,
        supplier_name,
        record,
        field_name,
        value,
        comparator_value,
        severity,
        reason,
        comparator_label="Comparator Value",
    ):
        return Finding(
            supplier_name=supplier_name,
            severity=severity,
            worksheet_name=record.sheet_name,
            cell_reference=record.get_cell_reference(field_name),
            item_description=f"{record.record_reference} | {field_name}",
            actual_value=str(round(value, 2)),
            category=FindingCategory.BETWEEN_RESPONSE_COMPARISON.value,
            comparator_value=str(round(comparator_value, 2)),
            comparator_label=comparator_label,
            deviation_percent=None,
            reason=reason,
            suggested_clarification=(
                f"Please confirm the submitted value for '{field_name}' "
                f"({record.record_reference}). {reason}"
            ),
        )

    # ==================================================
    # Utility
    # ==================================================

    def _index_by_key(self, records):
        lookup = {}

        for record in records:
            for field_name, value in record.values.items():
                lookup[self._key(record, field_name)] = value

        return lookup

    def _key(self, record, field_name):
        return (record.sheet_name, record.record_reference, field_name)

    def _severity_for_deviation(self, deviation_percent):
        if deviation_percent >= config.HIGH_SEVERITY_DEVIATION_PERCENT:
            return Severity.HIGH

        if deviation_percent >= config.MEDIUM_SEVERITY_DEVIATION_PERCENT:
            return Severity.MEDIUM

        if deviation_percent >= config.LOW_SEVERITY_DEVIATION_PERCENT:
            return Severity.LOW

        return Severity.INFO

    def _severity_for_z_score(self, z_score, tolerance):
        if z_score >= tolerance * 1.5:
            return Severity.HIGH

        return Severity.MEDIUM

    def _matches_scope(self, sheet_name, field_name, scope_sheet_name, scope_field_names):
        if scope_sheet_name and sheet_name != scope_sheet_name:
            return False

        if scope_field_names and field_name not in scope_field_names:
            return False

        return True

    def _covered_by_any(self, rules, sheet_name, field_name):
        for rule in rules:
            if rule.sheet_name and rule.sheet_name != sheet_name:
                continue

            if rule.target_fields and field_name not in rule.target_fields:
                continue

            return True

        return False

    def _to_float_or_none(self, value):
        if value is None:
            return None

        if isinstance(value, bool):
            return None

        if isinstance(value, (int, float)):
            if math.isnan(value):
                return None

            return float(value)

        text = str(value).strip()

        if text == "":
            return None

        cleaned = text.replace(",", "").replace("£", "").replace("%", "")

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
