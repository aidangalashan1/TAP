# gui/rule_manager_dialog.py

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from rules.custom_rule_models import CustomRule
from rules.custom_rule_models import CustomRuleCondition
from rules.custom_rule_models import CustomRuleMatchMode
from rules.custom_rule_models import CustomRuleOperator
from rules.custom_rule_models import CustomRuleRightValueType
from rules.custom_rule_models import CustomRuleSeverity


class RuleBuilderDialog:
    # Modal dialog for creating or editing user-defined rules.
    #
    # The dialog uses headers detected from the selected workbook.
    # Users can create rules such as:
    #
    # Weekday Rate <= Weekend Rate
    # AND
    # Weekday Rate <= 50

    OPERATOR_LABELS = {
        "equals": CustomRuleOperator.EQUALS,
        "does not equal": CustomRuleOperator.NOT_EQUALS,
        "is greater than": CustomRuleOperator.GREATER_THAN,
        "is greater than or equal to": CustomRuleOperator.GREATER_THAN_OR_EQUAL,
        "is less than": CustomRuleOperator.LESS_THAN,
        "is less than or equal to": CustomRuleOperator.LESS_THAN_OR_EQUAL,
        "is not greater than": CustomRuleOperator.LESS_THAN_OR_EQUAL,
        "is not less than": CustomRuleOperator.GREATER_THAN_OR_EQUAL,
        "contains": CustomRuleOperator.CONTAINS,
        "does not contain": CustomRuleOperator.NOT_CONTAINS,
        "is blank": CustomRuleOperator.IS_BLANK,
        "is not blank": CustomRuleOperator.IS_NOT_BLANK,
    }

    RIGHT_TYPE_LABELS = {
        "Field": CustomRuleRightValueType.FIELD,
        "Fixed Value": CustomRuleRightValueType.VALUE,
        "Blank": CustomRuleRightValueType.BLANK,
    }

    SEVERITY_LABELS = {
        "High": CustomRuleSeverity.HIGH,
        "Medium": CustomRuleSeverity.MEDIUM,
        "Low": CustomRuleSeverity.LOW,
        "Info": CustomRuleSeverity.INFO,
    }

    MATCH_MODE_LABELS = {
        "All conditions must be true": CustomRuleMatchMode.ALL,
        "Any condition can be true": CustomRuleMatchMode.ANY,
    }

    def __init__(
        self,
        parent,
        headers,
        sheet_names=None,
        existing_rule=None
    ):
        self.parent = parent
        self.headers = list(headers)

        if sheet_names is None:
            sheet_names = []

        self.sheet_names = list(sheet_names)
        self.existing_rule = existing_rule
        self.result = None
        self.condition_rows = []

        self.window = tk.Toplevel(parent)
        self.window.title("Custom Rule Builder")
        self.window.geometry("900x650")
        self.window.transient(parent)
        self.window.grab_set()

        self.rule_name_var = tk.StringVar()
        self.severity_var = tk.StringVar(value="Medium")
        self.match_mode_var = tk.StringVar(value="All conditions must be true")
        self.sheet_name_var = tk.StringVar(value="")
        self.enabled_var = tk.BooleanVar(value=True)
        self.message_var = tk.StringVar()

        self._build_ui()

        if existing_rule is not None:
            self._load_existing_rule(existing_rule)
        else:
            self._add_condition_row()

    def show(self):
        self.parent.wait_window(self.window)
        return self.result

    def _build_ui(self):
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self._build_rule_details_section(main_frame)
        self._build_conditions_section(main_frame)
        self._build_message_section(main_frame)
        self._build_button_section(main_frame)

    def _build_rule_details_section(self, parent):
        frame = ttk.LabelFrame(
            parent,
            text="Rule Details",
            padding=10
        )

        frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame, text="Rule Name").grid(
            row=0,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )

        ttk.Entry(
            frame,
            textvariable=self.rule_name_var,
            width=45
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=5,
            pady=5
        )

        ttk.Label(frame, text="Severity").grid(
            row=0,
            column=2,
            sticky="w",
            padx=5,
            pady=5
        )

        ttk.Combobox(
            frame,
            textvariable=self.severity_var,
            values=list(self.SEVERITY_LABELS.keys()),
            state="readonly",
            width=12
        ).grid(
            row=0,
            column=3,
            sticky="w",
            padx=5,
            pady=5
        )

        ttk.Label(frame, text="Match Mode").grid(
            row=1,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )

        ttk.Combobox(
            frame,
            textvariable=self.match_mode_var,
            values=list(self.MATCH_MODE_LABELS.keys()),
            state="readonly",
            width=30
        ).grid(
            row=1,
            column=1,
            sticky="w",
            padx=5,
            pady=5
        )

        ttk.Label(frame, text="Apply to Sheet").grid(
            row=1,
            column=2,
            sticky="w",
            padx=5,
            pady=5
        )

        sheet_values = [""] + self.sheet_names

        ttk.Combobox(
            frame,
            textvariable=self.sheet_name_var,
            values=sheet_values,
            state="readonly",
            width=25
        ).grid(
            row=1,
            column=3,
            sticky="w",
            padx=5,
            pady=5
        )

        ttk.Checkbutton(
            frame,
            text="Enabled",
            variable=self.enabled_var
        ).grid(
            row=2,
            column=1,
            sticky="w",
            padx=5,
            pady=5
        )

    def _build_conditions_section(self, parent):
        frame = ttk.LabelFrame(
            parent,
            text="Conditions",
            padding=10
        )

        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        header_frame = ttk.Frame(frame)
        header_frame.pack(fill=tk.X)

        ttk.Label(header_frame, text="Left Field", width=25).grid(
            row=0,
            column=0,
            sticky="w",
            padx=5
        )

        ttk.Label(header_frame, text="Operator", width=28).grid(
            row=0,
            column=1,
            sticky="w",
            padx=5
        )

        ttk.Label(header_frame, text="Right Type", width=15).grid(
            row=0,
            column=2,
            sticky="w",
            padx=5
        )

        ttk.Label(header_frame, text="Right Field / Value", width=25).grid(
            row=0,
            column=3,
            sticky="w",
            padx=5
        )

        self.conditions_container = ttk.Frame(frame)
        self.conditions_container.pack(fill=tk.BOTH, expand=True, pady=(5, 5))

        ttk.Button(
            frame,
            text="Add Condition",
            command=self._add_condition_row
        ).pack(anchor="w")

    def _build_message_section(self, parent):
        frame = ttk.LabelFrame(
            parent,
            text="Finding Message",
            padding=10
        )

        frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Entry(
            frame,
            textvariable=self.message_var
        ).pack(fill=tk.X)

    def _build_button_section(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X)

        ttk.Button(
            frame,
            text="Save Rule",
            command=self._save_rule
        ).pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(
            frame,
            text="Cancel",
            command=self._cancel
        ).pack(side=tk.RIGHT)

    def _add_condition_row(self, condition=None):
        row_frame = ttk.Frame(self.conditions_container)
        row_frame.pack(fill=tk.X, pady=3)

        left_field_var = tk.StringVar()
        operator_var = tk.StringVar(value="equals")
        right_type_var = tk.StringVar(value="Fixed Value")
        right_value_var = tk.StringVar()

        if condition is not None:
            left_field_var.set(condition.left_field)
            operator_var.set(self._operator_to_label(condition.operator))
            right_type_var.set(
                self._right_type_to_label(condition.right_value_type)
            )

            if condition.right_value is not None:
                right_value_var.set(str(condition.right_value))

        ttk.Combobox(
            row_frame,
            textvariable=left_field_var,
            values=self.headers,
            state="readonly",
            width=25
        ).grid(
            row=0,
            column=0,
            padx=5,
            sticky="w"
        )

        ttk.Combobox(
            row_frame,
            textvariable=operator_var,
            values=list(self.OPERATOR_LABELS.keys()),
            state="readonly",
            width=28
        ).grid(
            row=0,
            column=1,
            padx=5,
            sticky="w"
        )

        ttk.Combobox(
            row_frame,
            textvariable=right_type_var,
            values=list(self.RIGHT_TYPE_LABELS.keys()),
            state="readonly",
            width=15
        ).grid(
            row=0,
            column=2,
            padx=5,
            sticky="w"
        )

        ttk.Entry(
            row_frame,
            textvariable=right_value_var,
            width=25
        ).grid(
            row=0,
            column=3,
            padx=5,
            sticky="w"
        )

        remove_button = ttk.Button(
            row_frame,
            text="Remove",
            command=lambda: self._remove_condition_row(row_frame)
        )

        remove_button.grid(
            row=0,
            column=4,
            padx=5,
            sticky="w"
        )

        condition_data = {
            "frame": row_frame,
            "left_field_var": left_field_var,
            "operator_var": operator_var,
            "right_type_var": right_type_var,
            "right_value_var": right_value_var,
        }

        self.condition_rows.append(condition_data)

    def _remove_condition_row(self, row_frame):
        remaining_rows = []

        for condition_row in self.condition_rows:
            if condition_row["frame"] == row_frame:
                condition_row["frame"].destroy()
                continue

            remaining_rows.append(condition_row)

        self.condition_rows = remaining_rows

    def _save_rule(self):
        rule_name = self.rule_name_var.get().strip()

        if rule_name == "":
            messagebox.showwarning(
                "Missing Rule Name",
                "Please enter a rule name."
            )
            return

        conditions = self._build_conditions_from_rows()

        if not conditions:
            messagebox.showwarning(
                "Missing Conditions",
                "Please add at least one condition."
            )
            return

        sheet_name = self.sheet_name_var.get().strip()

        if sheet_name == "":
            sheet_name = None

        rule = CustomRule(
            name=rule_name,
            severity=self.SEVERITY_LABELS[self.severity_var.get()],
            match_mode=self.MATCH_MODE_LABELS[self.match_mode_var.get()],
            conditions=conditions,
            enabled=self.enabled_var.get(),
            sheet_name=sheet_name,
            message=self.message_var.get().strip(),
        )

        self.result = rule
        self.window.destroy()

    def _build_conditions_from_rows(self):
        conditions = []

        for condition_row in self.condition_rows:
            left_field = condition_row["left_field_var"].get().strip()
            operator_label = condition_row["operator_var"].get().strip()
            right_type_label = condition_row["right_type_var"].get().strip()
            right_value = condition_row["right_value_var"].get().strip()

            if left_field == "":
                continue

            operator = self.OPERATOR_LABELS.get(operator_label)
            right_value_type = self.RIGHT_TYPE_LABELS.get(right_type_label)

            if operator is None or right_value_type is None:
                continue

            if right_value_type == CustomRuleRightValueType.FIELD:
                if right_value == "":
                    continue

            if right_value_type == CustomRuleRightValueType.BLANK:
                right_value = None

            condition = CustomRuleCondition(
                left_field=left_field,
                operator=operator,
                right_value_type=right_value_type,
                right_value=right_value,
            )

            conditions.append(condition)

        return conditions

    def _load_existing_rule(self, rule):
        self.rule_name_var.set(rule.name)
        self.severity_var.set(self._severity_to_label(rule.severity))
        self.match_mode_var.set(self._match_mode_to_label(rule.match_mode))
        self.enabled_var.set(rule.enabled)
        self.message_var.set(rule.message)

        if rule.sheet_name:
            self.sheet_name_var.set(rule.sheet_name)

        for condition in rule.conditions:
            self._add_condition_row(condition)

    def _cancel(self):
        self.result = None
        self.window.destroy()

    def _severity_to_label(self, severity):
        for label, enum_value in self.SEVERITY_LABELS.items():
            if enum_value == severity:
                return label

        return "Medium"

    def _match_mode_to_label(self, match_mode):
        for label, enum_value in self.MATCH_MODE_LABELS.items():
            if enum_value == match_mode:
                return label

        return "All conditions must be true"

    def _operator_to_label(self, operator):
        for label, enum_value in self.OPERATOR_LABELS.items():
            if enum_value == operator:
                return label

        return "equals"

    def _right_type_to_label(self, right_type):
        for label, enum_value in self.RIGHT_TYPE_LABELS.items():
            if enum_value == right_type:
                return label

        return "Fixed Value"