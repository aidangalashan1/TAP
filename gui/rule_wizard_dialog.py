# gui/rule_wizard_dialog.py

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

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


class RuleWizardDialog:
    OPERATOR_OPTIONS = {
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
    }

    SEVERITY_OPTIONS = {
        "High": CustomRuleSeverity.HIGH,
        "Medium": CustomRuleSeverity.MEDIUM,
        "Low": CustomRuleSeverity.LOW,
        "Info": CustomRuleSeverity.INFO,
    }

    ADVANCED_RULE_TYPES = [
        "Compare Two Fields",
        "Compare Field To Fixed Value",
        "Check For Blank Values",
        "Range Check",
    ]

    OUTLIER_METHODS = {
        "IQR": OutlierMethod.IQR,
        "Z Score": OutlierMethod.Z_SCORE,
    }

    def __init__(self, parent, fields):
        self.parent = parent
        self.fields = sorted(list(fields))
        self.result = None

        self.window = tk.Toplevel(parent)
        self.window.title("Rule Wizard")
        self.window.geometry("900x650")
        self.window.transient(parent)
        self.window.grab_set()

        self.mode_var = tk.StringVar(value="Quick Rules")

        self.rule_name_var = tk.StringVar()
        self.severity_var = tk.StringVar(value="Medium")
        self.message_var = tk.StringVar()

        self.quick_blanks_var = tk.BooleanVar(value=True)
        self.quick_zeroes_var = tk.BooleanVar(value=True)
        self.quick_negatives_var = tk.BooleanVar(value=True)
        self.quick_duplicates_var = tk.BooleanVar(value=False)
        self.quick_outliers_var = tk.BooleanVar(value=True)

        self.outlier_method_var = tk.StringVar(value="IQR")
        self.outlier_tolerance_var = tk.StringVar(value="1.5")

        self.advanced_type_var = tk.StringVar(value=self.ADVANCED_RULE_TYPES[0])
        self.left_field_var = tk.StringVar()
        self.operator_var = tk.StringVar(value="is greater than")
        self.right_field_var = tk.StringVar()
        self.fixed_value_var = tk.StringVar()
        self.minimum_value_var = tk.StringVar()
        self.maximum_value_var = tk.StringVar()

        self.body_frame = None

        self._build_ui()
        self._refresh_body()

    def show(self):
        self.parent.wait_window(self.window)
        return self.result

    def _build_ui(self):
        main = ttk.Frame(self.window, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            main,
            text="Rule Wizard",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        self._build_mode_section(main)
        self._build_common_details_section(main)

        self.body_frame = ttk.LabelFrame(
            main,
            text="Rule Configuration",
            padding=10,
        )
        self.body_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self._build_buttons(main)

    def _build_mode_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Mode", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Radiobutton(
            frame,
            text="Quick Rules",
            variable=self.mode_var,
            value="Quick Rules",
            command=self._refresh_body,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            frame,
            text="Advanced Rule",
            variable=self.mode_var,
            value="Advanced Rule",
            command=self._refresh_body,
        ).pack(side=tk.LEFT, padx=5)

    def _build_common_details_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Rule Details", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame, text="Rule Name").grid(
            row=0,
            column=0,
            sticky="w",
            padx=5,
            pady=4,
        )

        ttk.Entry(
            frame,
            textvariable=self.rule_name_var,
            width=45,
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=5,
            pady=4,
        )

        ttk.Label(frame, text="Severity").grid(
            row=0,
            column=2,
            sticky="w",
            padx=5,
            pady=4,
        )

        ttk.Combobox(
            frame,
            textvariable=self.severity_var,
            values=list(self.SEVERITY_OPTIONS.keys()),
            state="readonly",
            width=12,
        ).grid(
            row=0,
            column=3,
            sticky="w",
            padx=5,
            pady=4,
        )

        ttk.Label(frame, text="Finding Message").grid(
            row=1,
            column=0,
            sticky="w",
            padx=5,
            pady=4,
        )

        ttk.Entry(
            frame,
            textvariable=self.message_var,
            width=80,
        ).grid(
            row=1,
            column=1,
            columnspan=3,
            sticky="w",
            padx=5,
            pady=4,
        )

    def _build_buttons(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X)

        ttk.Button(
            frame,
            text="Create Rule",
            command=self._create_rule,
        ).pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(
            frame,
            text="Cancel",
            command=self._cancel,
        ).pack(side=tk.RIGHT)

    def _refresh_body(self):
        if self.body_frame is None:
            return

        for widget in self.body_frame.winfo_children():
            widget.destroy()

        if self.mode_var.get() == "Quick Rules":
            self._build_quick_rules_body()
        else:
            self._build_advanced_rules_body()

    # ==================================================
    # Quick Rules UI
    # ==================================================

    def _build_quick_rules_body(self):
        ttk.Label(
            self.body_frame,
            text=(
                "Quick rules run across detected workbook fields. "
                "Use Advanced Rule for bespoke field-to-field logic."
            ),
            wraplength=780,
        ).pack(anchor="w", pady=(0, 10))

        ttk.Checkbutton(
            self.body_frame,
            text="Check blank values",
            variable=self.quick_blanks_var,
        ).pack(anchor="w", pady=2)

        ttk.Checkbutton(
            self.body_frame,
            text="Check zero values",
            variable=self.quick_zeroes_var,
        ).pack(anchor="w", pady=2)

        ttk.Checkbutton(
            self.body_frame,
            text="Check negative values",
            variable=self.quick_negatives_var,
        ).pack(anchor="w", pady=2)

        ttk.Checkbutton(
            self.body_frame,
            text="Check duplicate values",
            variable=self.quick_duplicates_var,
        ).pack(anchor="w", pady=2)

        ttk.Checkbutton(
            self.body_frame,
            text="Check outliers",
            variable=self.quick_outliers_var,
        ).pack(anchor="w", pady=(10, 2))

        outlier_frame = ttk.Frame(self.body_frame)
        outlier_frame.pack(anchor="w", pady=(8, 0))

        ttk.Label(outlier_frame, text="Outlier method").grid(
            row=0,
            column=0,
            sticky="w",
            padx=5,
            pady=5,
        )

        ttk.Combobox(
            outlier_frame,
            textvariable=self.outlier_method_var,
            values=list(self.OUTLIER_METHODS.keys()),
            state="readonly",
            width=20,
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=5,
            pady=5,
        )

        ttk.Label(outlier_frame, text="Tolerance").grid(
            row=0,
            column=2,
            sticky="w",
            padx=5,
            pady=5,
        )

        ttk.Combobox(
            outlier_frame,
            textvariable=self.outlier_tolerance_var,
            values=["1.5", "2", "2.5", "3"],
            width=10,
        ).grid(
            row=0,
            column=3,
            sticky="w",
            padx=5,
            pady=5,
        )

    # ==================================================
    # Advanced Rules UI
    # ==================================================

    def _build_advanced_rules_body(self):
        type_frame = ttk.Frame(self.body_frame)
        type_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(type_frame, text="Advanced rule type").pack(side=tk.LEFT)

        advanced_combo = ttk.Combobox(
            type_frame,
            textvariable=self.advanced_type_var,
            values=self.ADVANCED_RULE_TYPES,
            state="readonly",
            width=35,
        )
        advanced_combo.pack(side=tk.LEFT, padx=(10, 0))
        advanced_combo.bind("<<ComboboxSelected>>", self._refresh_advanced_body)

        self.advanced_body_frame = ttk.Frame(self.body_frame)
        self.advanced_body_frame.pack(fill=tk.BOTH, expand=True)

        self._refresh_advanced_body()

    def _refresh_advanced_body(self, event=None):
        for widget in self.advanced_body_frame.winfo_children():
            widget.destroy()

        rule_type = self.advanced_type_var.get()

        if rule_type == "Compare Two Fields":
            self._build_compare_two_fields_body()
        elif rule_type == "Compare Field To Fixed Value":
            self._build_compare_fixed_value_body()
        elif rule_type == "Check For Blank Values":
            self._build_blank_check_body()
        elif rule_type == "Range Check":
            self._build_range_check_body()

    def _build_compare_two_fields_body(self):
        self._field_combo(self.advanced_body_frame, 0, 0, self.left_field_var)
        self._operator_combo(self.advanced_body_frame, 0, 1)
        self._field_combo(self.advanced_body_frame, 0, 2, self.right_field_var)

    def _build_compare_fixed_value_body(self):
        self._field_combo(self.advanced_body_frame, 0, 0, self.left_field_var)
        self._operator_combo(self.advanced_body_frame, 0, 1)

        ttk.Entry(
            self.advanced_body_frame,
            textvariable=self.fixed_value_var,
            width=20,
        ).grid(row=0, column=2, sticky="w", padx=5, pady=5)

    def _build_blank_check_body(self):
        ttk.Label(
            self.advanced_body_frame,
            text="Flag when this field is blank:",
        ).grid(row=0, column=0, sticky="w", padx=5, pady=5)

        self._field_combo(self.advanced_body_frame, 0, 1, self.left_field_var)

    def _build_range_check_body(self):
        ttk.Label(
            self.advanced_body_frame,
            text="Field",
        ).grid(row=0, column=0, sticky="w", padx=5, pady=5)

        self._field_combo(self.advanced_body_frame, 0, 1, self.left_field_var)

        ttk.Label(
            self.advanced_body_frame,
            text="Minimum",
        ).grid(row=1, column=0, sticky="w", padx=5, pady=5)

        ttk.Entry(
            self.advanced_body_frame,
            textvariable=self.minimum_value_var,
            width=20,
        ).grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(
            self.advanced_body_frame,
            text="Maximum",
        ).grid(row=2, column=0, sticky="w", padx=5, pady=5)

        ttk.Entry(
            self.advanced_body_frame,
            textvariable=self.maximum_value_var,
            width=20,
        ).grid(row=2, column=1, sticky="w", padx=5, pady=5)

    def _field_combo(self, parent, row, column, variable):
        ttk.Combobox(
            parent,
            textvariable=variable,
            values=self.fields,
            state="readonly",
            width=32,
        ).grid(row=row, column=column, sticky="w", padx=5, pady=5)

    def _operator_combo(self, parent, row, column):
        ttk.Combobox(
            parent,
            textvariable=self.operator_var,
            values=list(self.OPERATOR_OPTIONS.keys()),
            state="readonly",
            width=28,
        ).grid(row=row, column=column, sticky="w", padx=5, pady=5)

    # ==================================================
    # Rule creation
    # ==================================================

    def _create_rule(self):
        if self.mode_var.get() == "Quick Rules":
            self.result = self._create_quick_rule()
        else:
            self.result = self._create_advanced_rule()

        if self.result is None:
            return

        self.window.destroy()

    def _create_quick_rule(self):
        rule_name = self.rule_name_var.get().strip()

        if rule_name == "":
            rule_name = "Quick Rules"

        try:
            tolerance = float(self.outlier_tolerance_var.get())
        except ValueError:
            messagebox.showwarning(
                "Invalid tolerance",
                "Please enter a valid numeric outlier tolerance.",
            )
            return None

        return CustomRule(
            name=rule_name,
            severity=self._current_severity(),
            conditions=[],
            enabled=True,
            match_mode=CustomRuleMatchMode.ALL,
            sheet_name=None,
            message=self.message_var.get().strip(),
            rule_type=CustomRuleType.QUICK_RULES,
            check_blanks=self.quick_blanks_var.get(),
            check_zeroes=self.quick_zeroes_var.get(),
            check_negative_values=self.quick_negatives_var.get(),
            check_duplicates=self.quick_duplicates_var.get(),
            check_outliers=self.quick_outliers_var.get(),
            outlier_method=self.OUTLIER_METHODS[self.outlier_method_var.get()],
            outlier_tolerance=tolerance,
            target_fields=[],
        )

    def _create_advanced_rule(self):
        rule_type = self.advanced_type_var.get()
        rule_name = self.rule_name_var.get().strip()

        if rule_name == "":
            rule_name = self._default_advanced_name(rule_type)

        if rule_type == "Compare Two Fields":
            return self._create_compare_two_fields_rule(rule_name)

        if rule_type == "Compare Field To Fixed Value":
            return self._create_compare_fixed_value_rule(rule_name)

        if rule_type == "Check For Blank Values":
            return self._create_blank_check_rule(rule_name)

        if rule_type == "Range Check":
            return self._create_range_check_rule(rule_name)

        return None

    def _create_compare_two_fields_rule(self, rule_name):
        left_field = self.left_field_var.get().strip()
        right_field = self.right_field_var.get().strip()
        operator = self.OPERATOR_OPTIONS.get(self.operator_var.get())

        if left_field == "" or right_field == "" or operator is None:
            messagebox.showwarning(
                "Missing rule detail",
                "Please complete all advanced rule fields.",
            )
            return None

        condition = CustomRuleCondition(
            left_field=left_field,
            operator=operator,
            right_value_type=CustomRuleRightValueType.FIELD,
            right_value=right_field,
        )

        return self._build_advanced_rule(rule_name, [condition])

    def _create_compare_fixed_value_rule(self, rule_name):
        left_field = self.left_field_var.get().strip()
        operator = self.OPERATOR_OPTIONS.get(self.operator_var.get())
        value = self._parse_value(self.fixed_value_var.get())

        if left_field == "" or operator is None:
            messagebox.showwarning(
                "Missing rule detail",
                "Please complete all advanced rule fields.",
            )
            return None

        if value is None:
            messagebox.showwarning(
                "Invalid value",
                "Please enter a valid fixed value.",
            )
            return None

        condition = CustomRuleCondition(
            left_field=left_field,
            operator=operator,
            right_value_type=CustomRuleRightValueType.VALUE,
            right_value=value,
        )

        return self._build_advanced_rule(rule_name, [condition])

    def _create_blank_check_rule(self, rule_name):
        left_field = self.left_field_var.get().strip()

        if left_field == "":
            messagebox.showwarning(
                "Missing field",
                "Please select a field.",
            )
            return None

        condition = CustomRuleCondition(
            left_field=left_field,
            operator=CustomRuleOperator.IS_BLANK,
            right_value_type=CustomRuleRightValueType.BLANK,
            right_value=None,
        )

        return self._build_advanced_rule(rule_name, [condition])

    def _create_range_check_rule(self, rule_name):
        left_field = self.left_field_var.get().strip()
        minimum_value = self._parse_value(self.minimum_value_var.get())
        maximum_value = self._parse_value(self.maximum_value_var.get())

        if left_field == "":
            messagebox.showwarning(
                "Missing field",
                "Please select a field.",
            )
            return None

        if minimum_value is None or maximum_value is None:
            messagebox.showwarning(
                "Invalid range",
                "Please enter valid minimum and maximum values.",
            )
            return None

        lower_condition = CustomRuleCondition(
            left_field=left_field,
            operator=CustomRuleOperator.LESS_THAN,
            right_value_type=CustomRuleRightValueType.VALUE,
            right_value=minimum_value,
        )

        upper_condition = CustomRuleCondition(
            left_field=left_field,
            operator=CustomRuleOperator.GREATER_THAN,
            right_value_type=CustomRuleRightValueType.VALUE,
            right_value=maximum_value,
        )

        return self._build_advanced_rule(
            rule_name,
            [lower_condition, upper_condition],
            match_mode=CustomRuleMatchMode.ANY,
        )

    def _build_advanced_rule(
        self,
        rule_name,
        conditions,
        match_mode=CustomRuleMatchMode.ALL,
    ):
        return CustomRule(
            name=rule_name,
            severity=self._current_severity(),
            conditions=conditions,
            enabled=True,
            match_mode=match_mode,
            sheet_name=None,
            message=self.message_var.get().strip(),
            rule_type=CustomRuleType.ADVANCED_RULE,
        )

    def _current_severity(self):
        return self.SEVERITY_OPTIONS.get(
            self.severity_var.get(),
            CustomRuleSeverity.MEDIUM,
        )

    def _default_advanced_name(self, rule_type):
        field_name = self.left_field_var.get().strip()

        if field_name:
            return f"{field_name} - {rule_type}"

        return rule_type

    def _parse_value(self, value):
        text = str(value).strip()

        if text == "":
            return None

        cleaned = text.replace(",", "")
        cleaned = cleaned.replace("£", "")
        cleaned = cleaned.replace("%", "")

        try:
            return float(cleaned)
        except ValueError:
            return text

    def _cancel(self):
        self.result = None
        self.window.destroy()