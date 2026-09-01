# tests/test_schema_rule_engine.py

from models.pricing_models import FindingCategory, Severity
from rules.custom_rule_models import (
    CustomRule,
    CustomRuleCondition,
    CustomRuleMatchMode,
    CustomRuleOperator,
    CustomRuleRightValueType,
    CustomRuleSeverity,
    CustomRuleType,
)
from rules.schema_rule_engine import SchemaRuleEngine
from schema.workbook_schema import DataRecord


def _record(sheet, ref, values):
    record = DataRecord(sheet_name=sheet, region_name=sheet, record_reference=ref)

    for field_name, value in values.items():
        record.set_value(field_name, value, f"{field_name}!{ref}")

    return record


def test_quick_rule_flags_blank_zero_and_negative():
    records = [
        _record("Labour", "Row 2", {"Day Rate": None}),
        _record("Labour", "Row 3", {"Day Rate": 0}),
        _record("Labour", "Row 4", {"Day Rate": -5}),
        _record("Labour", "Row 5", {"Day Rate": 120}),
    ]

    rule = CustomRule(
        name="Quick Rules",
        severity=CustomRuleSeverity.MEDIUM,
        rule_type=CustomRuleType.QUICK_RULES,
        check_blanks=True,
        check_zeroes=True,
        check_negative_values=True,
    )

    findings = SchemaRuleEngine().execute(records, [rule])

    reasons = {f.reason for f in findings}
    assert "Blank value detected." in reasons
    assert "Zero value detected." in reasons
    assert "Negative value detected." in reasons
    assert len(findings) == 3
    assert all(
        f.category == FindingCategory.TENDER_RESPONSE_CHECK.value
        for f in findings
    )


def test_quick_rule_disabled_checks_are_skipped():
    records = [_record("Labour", "Row 2", {"Day Rate": None})]

    rule = CustomRule(
        name="Quick Rules",
        severity=CustomRuleSeverity.MEDIUM,
        rule_type=CustomRuleType.QUICK_RULES,
        check_blanks=False,
    )

    findings = SchemaRuleEngine().execute(records, [rule])
    assert findings == []


def test_quick_rule_duplicate_detection():
    records = [
        _record("Labour", "Row 2", {"Reference": "ABC-1"}),
        _record("Labour", "Row 3", {"Reference": "abc-1"}),
        _record("Labour", "Row 4", {"Reference": "XYZ-2"}),
    ]

    rule = CustomRule(
        name="Quick Rules",
        severity=CustomRuleSeverity.LOW,
        rule_type=CustomRuleType.QUICK_RULES,
        check_duplicates=True,
    )

    findings = SchemaRuleEngine().execute(records, [rule])

    # Case-insensitive match: ABC-1 vs abc-1 counts as a duplicate
    # pair, XYZ-2 is unique and not flagged.
    assert len(findings) == 2
    assert {f.item_description for f in findings} == {
        "Labour | Reference",
    }


def test_quick_rule_outlier_detection_against_average():
    """
    9 rows at 100, 1 row at 300. Average is 120, so the normal rows
    sit ~17% away from it (under a 25% tolerance) while the outlier
    sits 150% away (clearly over).
    """

    records = [
        _record("Labour", f"Row {i}", {"Day Rate": 100})
        for i in range(2, 11)
    ]
    records.append(_record("Labour", "Row 11", {"Day Rate": 300}))

    rule = CustomRule(
        name="Quick Rules",
        severity=CustomRuleSeverity.MEDIUM,
        rule_type=CustomRuleType.QUICK_RULES,
        check_outliers=True,
        outlier_tolerance_percent=25.0,
    )

    findings = SchemaRuleEngine().execute(records, [rule])

    assert len(findings) == 1
    assert findings[0].actual_value == "300.0"

    # The average and deviation figures must not leak into the
    # supplier-facing clarification text.
    assert "120" not in findings[0].suggested_clarification
    assert "150" not in findings[0].suggested_clarification


def test_advanced_rule_and_match_mode_requires_all_conditions():
    matching = _record("Labour", "Row 2", {"Day Rate": None, "Call-Out Fee": 500})
    non_matching = _record("Labour", "Row 3", {"Day Rate": 100, "Call-Out Fee": 500})

    rule = CustomRule(
        name="Blank day rate with high call-out",
        severity=CustomRuleSeverity.HIGH,
        rule_type=CustomRuleType.ADVANCED_RULE,
        match_mode=CustomRuleMatchMode.ALL,
        conditions=[
            CustomRuleCondition(
                left_field="Day Rate",
                operator=CustomRuleOperator.IS_BLANK,
                right_value_type=CustomRuleRightValueType.BLANK,
            ),
            CustomRuleCondition(
                left_field="Call-Out Fee",
                operator=CustomRuleOperator.GREATER_THAN,
                right_value_type=CustomRuleRightValueType.VALUE,
                right_value=100,
            ),
        ],
    )

    findings = SchemaRuleEngine().execute([matching, non_matching], [rule])

    assert len(findings) == 1
    assert findings[0].severity == Severity.HIGH


def test_advanced_rule_any_match_mode_and_field_to_field_comparison():
    over_benchmark = _record(
        "Labour", "Row 2", {"Day Rate": 150, "Benchmark Rate": 100}
    )
    under_benchmark = _record(
        "Labour", "Row 3", {"Day Rate": 90, "Benchmark Rate": 100}
    )

    rule = CustomRule(
        name="Above benchmark",
        severity=CustomRuleSeverity.MEDIUM,
        rule_type=CustomRuleType.ADVANCED_RULE,
        match_mode=CustomRuleMatchMode.ANY,
        conditions=[
            CustomRuleCondition(
                left_field="Day Rate",
                operator=CustomRuleOperator.GREATER_THAN,
                right_value_type=CustomRuleRightValueType.FIELD,
                right_value="Benchmark Rate",
            ),
        ],
    )

    findings = SchemaRuleEngine().execute(
        [over_benchmark, under_benchmark], [rule]
    )

    assert len(findings) == 1
    assert findings[0].actual_value == "150"


def test_disabled_rule_is_skipped_entirely():
    records = [_record("Labour", "Row 2", {"Day Rate": None})]

    rule = CustomRule(
        name="Quick Rules",
        severity=CustomRuleSeverity.MEDIUM,
        rule_type=CustomRuleType.QUICK_RULES,
        check_blanks=True,
        enabled=False,
    )

    assert SchemaRuleEngine().execute(records, [rule]) == []


def test_comparison_rule_is_not_executed_by_schema_rule_engine():
    """
    COMPARISON_RULE rules compare across supplier workbooks and are
    executed separately by CrossSupplierComparator - SchemaRuleEngine
    must not treat them as advanced field-logic rules against a
    single supplier's own records.
    """

    records = [_record("Labour", "Row 2", {"Day Rate": 100})]

    rule = CustomRule(
        name="Benchmark scoped rule",
        severity=CustomRuleSeverity.MEDIUM,
        rule_type=CustomRuleType.COMPARISON_RULE,
        conditions=[],
    )

    assert SchemaRuleEngine().execute(records, [rule]) == []
