# tests/test_cross_supplier_comparator.py

from models.pricing_models import FindingCategory
from rules.cross_supplier_comparator import CrossSupplierComparator
from rules.custom_rule_models import (
    ComparisonBasis,
    CustomRule,
    CustomRuleSeverity,
    CustomRuleType,
)
from schema.workbook_schema import DataRecord


def _record(sheet, ref, values):
    record = DataRecord(sheet_name=sheet, region_name=sheet, record_reference=ref)

    for field_name, value in values.items():
        record.set_value(field_name, value, f"{field_name}!{ref}")

    return record


def test_compare_to_benchmark_flags_deviation_over_threshold():
    supplier_records = {
        "SupplierA": [_record("Labour", "Row 2", {"Day Rate": 150})],
        "SupplierB": [_record("Labour", "Row 2", {"Day Rate": 101})],
    }
    benchmark_records = [_record("Labour", "Row 2", {"Day Rate": 100})]

    comparator = CrossSupplierComparator(benchmark_threshold_percent=30.0)
    findings = comparator.compare_to_benchmark(supplier_records, benchmark_records)

    assert len(findings) == 1
    assert findings[0].supplier_name == "SupplierA"
    assert findings[0].category == FindingCategory.BENCHMARK_COMPARISON.value
    assert findings[0].comparator_value == "100.0"
    assert findings[0].comparator_label == "Benchmark Rate"
    assert findings[0].deviation_percent == 50.0

    # The clarification is what gets copied out to the supplier - it
    # must never contain the benchmark rate, the deviation %, or any
    # other commercially sensitive figure. Those stay in `reason`,
    # for the buyer's own internal report only.
    clarification = findings[0].suggested_clarification
    assert "100" not in clarification
    assert "50" not in clarification
    assert "benchmark" not in clarification.lower()
    assert "Day Rate" in clarification
    assert "Row 2" in clarification


def test_compare_to_benchmark_skips_fields_with_no_benchmark_value():
    supplier_records = {
        "SupplierA": [_record("Labour", "Row 2", {"Call-Out Fee": 999})],
    }
    benchmark_records = [_record("Labour", "Row 2", {"Day Rate": 100})]

    findings = CrossSupplierComparator().compare_to_benchmark(
        supplier_records, benchmark_records
    )

    assert findings == []


def test_compare_statistical_flags_value_far_from_group_average():
    """
    19 suppliers at 100, 1 at 300. Group average is 110, so the
    normal suppliers sit ~9% away from it (safely under a 25%
    tolerance) while the outlier sits ~173% away (clearly over) -
    demonstrates the average is only meaningfully skewed by a true
    outlier once there's enough of a group behind it.
    """

    supplier_records = {
        f"Supplier{i}": [_record("Labour", "Row 2", {"Day Rate": 100})]
        for i in range(19)
    }
    supplier_records["SupplierOutlier"] = [
        _record("Labour", "Row 2", {"Day Rate": 300})
    ]

    comparator = CrossSupplierComparator(outlier_tolerance_percent=25.0)

    findings = comparator.compare_statistical(supplier_records)

    assert len(findings) == 1
    assert findings[0].supplier_name == "SupplierOutlier"
    assert findings[0].category == (
        FindingCategory.BETWEEN_RESPONSE_COMPARISON.value
    )
    assert findings[0].comparator_label == "Supplier Group Average"
    assert findings[0].comparator_value == "110.0"
    assert round(findings[0].deviation_percent, 1) == 172.7

    # Same requirement as the benchmark case: the group average and
    # deviation figures (derived from other suppliers' submissions)
    # must never appear in the supplier-facing clarification text.
    clarification = findings[0].suggested_clarification
    assert "110" not in clarification
    assert "172" not in clarification
    assert "average" not in clarification.lower()


def test_compare_statistical_requires_at_least_three_values():
    supplier_records = {
        "SupplierA": [_record("Labour", "Row 2", {"Day Rate": 100})],
        "SupplierB": [_record("Labour", "Row 2", {"Day Rate": 999})],
    }

    findings = CrossSupplierComparator().compare_statistical(supplier_records)
    assert findings == []


def test_compare_using_rules_scoped_override_beats_global_default():
    """
    A comparison rule scoped to one field with a tighter threshold
    should flag its field using its own threshold, while every other
    field still falls back to the comparator's global default -
    without being double-flagged by both passes.
    """

    supplier_records = {
        "SupplierA": [
            _record("Sheet1", "Row 2", {"FieldA": 110, "FieldB": 110})
        ],
    }
    benchmark_records = [
        _record("Sheet1", "Row 2", {"FieldA": 100, "FieldB": 100})
    ]

    rule = CustomRule(
        name="FieldA Tight Benchmark",
        severity=CustomRuleSeverity.HIGH,
        rule_type=CustomRuleType.COMPARISON_RULE,
        sheet_name="Sheet1",
        target_fields=["FieldA"],
        comparison_basis=ComparisonBasis.BENCHMARK,
        comparison_threshold_percent=5.0,
    )

    comparator = CrossSupplierComparator(benchmark_threshold_percent=30.0)
    findings = comparator.compare_using_rules(
        supplier_records=supplier_records,
        benchmark_records=benchmark_records,
        comparison_rules=[rule],
        use_benchmark_default=True,
    )

    # FieldA: 10% deviation, flagged by the rule's 5% threshold.
    # FieldB: same 10% deviation, but under the 30% global default -
    # not flagged, and not double-counted by the rule either.
    assert len(findings) == 1
    assert "FieldA" in findings[0].item_description
    assert "rule: FieldA Tight Benchmark" in findings[0].comparator_label


def test_compute_benchmark_coverage_counts_matched_and_unmatched_fields():
    supplier_records = {
        "SupplierA": [
            _record(
                "Labour", "Row 2", {"Day Rate": 120, "Call-Out Fee": 50}
            )
        ],
    }
    # Only Day Rate has a benchmark match - Call-Out Fee doesn't
    # appear in the benchmark workbook at all.
    benchmark_records = [_record("Labour", "Row 2", {"Day Rate": 100})]

    coverage = CrossSupplierComparator().compute_benchmark_coverage(
        supplier_records, benchmark_records
    )

    supplier_coverage = coverage["SupplierA"]
    assert supplier_coverage.total_fields == 2
    assert supplier_coverage.matched_fields == 1
    assert supplier_coverage.unmatched_fields == 1
    assert supplier_coverage.match_rate_percent == 50.0
    assert supplier_coverage.unmatched_by_sheet == {"Labour": 1}
    assert supplier_coverage.unmatched_by_field == {"Call-Out Fee": 1}


def test_compute_benchmark_coverage_ignores_blank_submitted_values():
    supplier_records = {
        "SupplierA": [_record("Labour", "Row 2", {"Day Rate": None})],
    }
    benchmark_records = [_record("Labour", "Row 2", {"Day Rate": 100})]

    coverage = CrossSupplierComparator().compute_benchmark_coverage(
        supplier_records, benchmark_records
    )

    # A blank submitted value isn't a field to compare at all, so it
    # shouldn't count toward the coverage denominator either.
    assert coverage["SupplierA"].total_fields == 0
