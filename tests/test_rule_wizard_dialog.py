# tests/test_rule_wizard_dialog.py
#
# Exercises RuleWizardDialog's pure condition-building/loading logic
# without opening a real window. tkinter's Toplevel/widgets are
# never instantiated - a bare instance is built via __new__ with
# just the tk.StringVar-backed attributes the logic under test
# actually reads, sidestepping the widget-building __init__ entirely.

import tkinter as tk

from gui.rule_wizard_dialog import RuleWizardDialog
from rules.custom_rule_models import (
    CustomRule,
    CustomRuleCondition,
    CustomRuleMatchMode,
    CustomRuleOperator,
    CustomRuleRightValueType,
    CustomRuleSeverity,
    CustomRuleType,
)


def _bare_dialog():
    dialog = object.__new__(RuleWizardDialog)
    dialog.rule_name_var = tk.StringVar()
    dialog.severity_var = tk.StringVar(value="Medium")
    dialog.message_var = tk.StringVar()
    dialog.advanced_match_mode_var = tk.StringVar(
        value="Match ALL conditions (AND)"
    )
    dialog.advanced_conditions = []
    return dialog


def _condition_row(
    left_field="",
    operator="equals",
    right_type="a fixed value",
    right_field="",
    right_value="",
):
    return {
        "left_field": tk.StringVar(value=left_field),
        "operator": tk.StringVar(value=operator),
        "right_type": tk.StringVar(value=right_type),
        "right_field": tk.StringVar(value=right_field),
        "right_value": tk.StringVar(value=right_value),
    }


def test_create_advanced_rule_with_field_comparison():
    dialog = _bare_dialog()
    dialog.advanced_conditions = [
        _condition_row(
            left_field="Day Rate",
            operator="is greater than",
            right_type="another field",
            right_field="Benchmark Day Rate",
        )
    ]

    rule = dialog._create_advanced_rule()

    assert rule is not None
    assert rule.rule_type == CustomRuleType.ADVANCED_RULE
    assert rule.match_mode == CustomRuleMatchMode.ALL
    assert len(rule.conditions) == 1

    condition = rule.conditions[0]
    assert condition.left_field == "Day Rate"
    assert condition.operator == CustomRuleOperator.GREATER_THAN
    assert condition.right_value_type == CustomRuleRightValueType.FIELD
    assert condition.right_value == "Benchmark Day Rate"


def test_create_advanced_rule_with_fixed_value():
    dialog = _bare_dialog()
    dialog.advanced_conditions = [
        _condition_row(
            left_field="Day Rate",
            operator="is less than",
            right_type="a fixed value",
            right_value="50",
        )
    ]

    rule = dialog._create_advanced_rule()

    condition = rule.conditions[0]
    assert condition.right_value_type == CustomRuleRightValueType.VALUE
    assert condition.right_value == 50.0


def test_create_advanced_rule_blank_operator_ignores_right_side():
    dialog = _bare_dialog()
    dialog.advanced_conditions = [
        _condition_row(left_field="Day Rate", operator="is blank")
    ]

    rule = dialog._create_advanced_rule()

    condition = rule.conditions[0]
    assert condition.operator == CustomRuleOperator.IS_BLANK
    assert condition.right_value_type == CustomRuleRightValueType.BLANK
    assert condition.right_value is None


def test_create_advanced_rule_multi_condition_or_previously_unbuildable():
    """
    The old 4-preset UI could never express "Field A blank OR Field B
    over a fixed value" in one rule - the free-form builder can.
    """
    dialog = _bare_dialog()
    dialog.advanced_match_mode_var.set("Match ANY condition (OR)")
    dialog.advanced_conditions = [
        _condition_row(left_field="Field A", operator="is blank"),
        _condition_row(
            left_field="Field B",
            operator="is greater than",
            right_type="a fixed value",
            right_value="100",
        ),
    ]

    rule = dialog._create_advanced_rule()

    assert rule.match_mode == CustomRuleMatchMode.ANY
    assert len(rule.conditions) == 2


def test_create_advanced_rule_rejects_condition_missing_field():
    dialog = _bare_dialog()
    dialog.advanced_conditions = [_condition_row(left_field="")]

    assert dialog._create_advanced_rule() is None


def test_create_advanced_rule_rejects_no_conditions():
    dialog = _bare_dialog()
    dialog.advanced_conditions = []

    assert dialog._create_advanced_rule() is None


def test_create_advanced_rule_defaults_name_from_first_condition():
    dialog = _bare_dialog()
    dialog.advanced_conditions = [
        _condition_row(
            left_field="Day Rate",
            operator="is blank",
        )
    ]

    rule = dialog._create_advanced_rule()
    assert rule.name == "Day Rate Condition"


def test_load_existing_advanced_rule_populates_condition_rows():
    existing_rule = CustomRule(
        name="Range-style check",
        severity=CustomRuleSeverity.HIGH,
        conditions=[
            CustomRuleCondition(
                "Day Rate", CustomRuleOperator.LESS_THAN,
                CustomRuleRightValueType.VALUE, 50,
            ),
            CustomRuleCondition(
                "Day Rate", CustomRuleOperator.GREATER_THAN,
                CustomRuleRightValueType.VALUE, 500,
            ),
        ],
        match_mode=CustomRuleMatchMode.ANY,
        rule_type=CustomRuleType.ADVANCED_RULE,
    )

    dialog = _bare_dialog()
    dialog._load_existing_advanced_rule(existing_rule)

    assert dialog.advanced_match_mode_var.get() == "Match ANY condition (OR)"
    assert len(dialog.advanced_conditions) == 2
    assert dialog.advanced_conditions[0]["left_field"].get() == "Day Rate"
    assert dialog.advanced_conditions[0]["right_value"].get() == "50"

    # Rebuilding from the loaded rows reproduces the original rule -
    # editing and re-saving a pre-existing rule is lossless.
    rebuilt = dialog._create_advanced_rule()
    assert rebuilt.match_mode == CustomRuleMatchMode.ANY
    assert [c.right_value for c in rebuilt.conditions] == [50.0, 500.0]
