# rules/cross_supplier_comparator.py

import math
from statistics import mean
from statistics import pstdev

import config
from models.pricing_models import Finding
from models.pricing_models import Severity
from rules.custom_rule_models import OutlierMethod


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
    # Benchmark Comparison
    # ==================================================

    def compare_to_benchmark(self, supplier_records, benchmark_records):
        """
        supplier_records: dict[supplier_name, list[DataRecord]]
        benchmark_records: list[DataRecord]
        """

        benchmark_lookup = self._index_by_key(benchmark_records)

        findings = []

        for supplier_name, records in supplier_records.items():
            for record in records:
                for field_name, raw_value in record.values.items():

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

                    if deviation_percent < self.benchmark_threshold_percent:
                        continue

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
                            comparator_value=str(round(benchmark_number, 2)),
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

    def compare_statistical(self, supplier_records):
        """
        supplier_records: dict[supplier_name, list[DataRecord]]
        """

        groups = {}

        for supplier_name, records in supplier_records.items():
            for record in records:
                for field_name, raw_value in record.values.items():

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

            if self.outlier_method == OutlierMethod.Z_SCORE:
                findings.extend(self._z_score_outliers(entries))
            else:
                findings.extend(self._iqr_outliers(entries))

        return findings

    def _z_score_outliers(self, entries):
        values = [entry[3] for entry in entries]

        average = mean(values)
        standard_deviation = pstdev(values)

        if standard_deviation == 0:
            return []

        findings = []

        for supplier_name, record, field_name, value in entries:

            z_score = abs((value - average) / standard_deviation)

            if z_score < self.outlier_tolerance:
                continue

            findings.append(
                self._build_statistical_finding(
                    supplier_name=supplier_name,
                    record=record,
                    field_name=field_name,
                    value=value,
                    comparator_value=average,
                    severity=self._severity_for_z_score(z_score),
                    reason=(
                        f"Value differs from the supplier group average "
                        f"({round(average, 2)}) by a Z score of "
                        f"{round(z_score, 2)}."
                    ),
                )
            )

        return findings

    def _iqr_outliers(self, entries):
        values = sorted(entry[3] for entry in entries)

        if len(values) < 4:
            return []

        q1 = self._percentile(values, 25)
        q3 = self._percentile(values, 75)

        iqr = q3 - q1

        if iqr == 0:
            return []

        lower_bound = q1 - (self.outlier_tolerance * iqr)
        upper_bound = q3 + (self.outlier_tolerance * iqr)

        findings = []

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
    ):
        return Finding(
            supplier_name=supplier_name,
            severity=severity,
            worksheet_name=record.sheet_name,
            cell_reference=record.get_cell_reference(field_name),
            item_description=f"{record.record_reference} | {field_name}",
            actual_value=str(round(value, 2)),
            comparator_value=str(round(comparator_value, 2)),
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

    def _severity_for_z_score(self, z_score):
        if z_score >= self.outlier_tolerance * 1.5:
            return Severity.HIGH

        return Severity.MEDIUM

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
