# tests/test_custom_rule_store.py

from rules.custom_rule_models import (
    ComparisonBasis,
    CustomRule,
    CustomRuleCondition,
    CustomRuleMatchMode,
    CustomRuleOperator,
    CustomRuleRightValueType,
    CustomRuleSeverity,
    CustomRuleType,
    OutlierMethod,
)
from rules.custom_rule_store import CustomRuleStore


def test_round_trips_a_quick_rule(tmp_path):
    store = CustomRuleStore(file_path=str(tmp_path / "rules.json"))

    rule = CustomRule(
        name="Quick Rules",
        severity=CustomRuleSeverity.HIGH,
        rule_type=CustomRuleType.QUICK_RULES,
        check_blanks=True,
        check_outliers=True,
        outlier_method=OutlierMethod.Z_SCORE,
        outlier_tolerance=2.5,
        target_fields=["Day Rate"],
    )

    store.save_rules([rule])
    loaded = store.load_rules()

    assert len(loaded) == 1
    assert loaded[0].name == "Quick Rules"
    assert loaded[0].severity == CustomRuleSeverity.HIGH
    assert loaded[0].rule_type == CustomRuleType.QUICK_RULES
    assert loaded[0].check_blanks is True
    assert loaded[0].outlier_method == OutlierMethod.Z_SCORE
    assert loaded[0].outlier_tolerance == 2.5
    assert loaded[0].target_fields == ["Day Rate"]


def test_round_trips_an_advanced_rule_with_conditions(tmp_path):
    store = CustomRuleStore(file_path=str(tmp_path / "rules.json"))

    rule = CustomRule(
        name="Blank with high call-out",
        severity=CustomRuleSeverity.MEDIUM,
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

    store.save_rules([rule])
    loaded = store.load_rules()[0]

    assert loaded.match_mode == CustomRuleMatchMode.ALL
    assert len(loaded.conditions) == 2
    assert loaded.conditions[0].operator == CustomRuleOperator.IS_BLANK
    assert loaded.conditions[1].right_value == 100
    assert loaded.conditions[1].right_value_type == (
        CustomRuleRightValueType.VALUE
    )


def test_round_trips_a_comparison_rule(tmp_path):
    store = CustomRuleStore(file_path=str(tmp_path / "rules.json"))

    rule = CustomRule(
        name="Labour Rate vs Benchmark",
        severity=CustomRuleSeverity.HIGH,
        rule_type=CustomRuleType.COMPARISON_RULE,
        sheet_name="Labour",
        target_fields=["Day Rate"],
        comparison_basis=ComparisonBasis.BENCHMARK,
        comparison_threshold_percent=15.0,
    )

    store.save_rules([rule])
    loaded = store.load_rules()[0]

    assert loaded.rule_type == CustomRuleType.COMPARISON_RULE
    assert loaded.comparison_basis == ComparisonBasis.BENCHMARK
    assert loaded.comparison_threshold_percent == 15.0
    assert loaded.sheet_name == "Labour"
    assert loaded.target_fields == ["Day Rate"]


def test_load_rules_returns_empty_list_when_file_missing(tmp_path):
    store = CustomRuleStore(file_path=str(tmp_path / "does_not_exist.json"))
    assert store.load_rules() == []


def test_load_rules_returns_empty_list_on_corrupt_file(tmp_path):
    file_path = tmp_path / "rules.json"
    file_path.write_text("not valid json{{{")

    store = CustomRuleStore(file_path=str(file_path))
    assert store.load_rules() == []


def test_delete_all_rules(tmp_path):
    file_path = tmp_path / "rules.json"
    store = CustomRuleStore(file_path=str(file_path))

    store.save_rules(
        [CustomRule(name="A rule", severity=CustomRuleSeverity.LOW)]
    )
    assert file_path.exists()

    store.delete_all_rules()
    assert not file_path.exists()
    assert store.load_rules() == []
