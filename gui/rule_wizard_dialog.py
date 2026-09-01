# gui/rule_wizard_dialog.py

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from rules.custom_rule_models import (
    ComparisonBasis,
    CustomRule,
    CustomRuleCondition,
    CustomRuleMatchMode,
    CustomRuleOperator,
    CustomRuleRightValueType,
    CustomRuleSeverity,
    CustomRuleType,
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
        "is blank": CustomRuleOperator.IS_BLANK,
        "is not blank": CustomRuleOperator.IS_NOT_BLANK,
    }

    # Operators that don't compare against a right-hand side at all -
    # the row's right-side widgets are hidden for these.
    NO_RIGHT_SIDE_OPERATORS = {
        "is blank",
        "is not blank",
    }

    RIGHT_TYPE_OPTIONS = {
        "a fixed value": CustomRuleRightValueType.VALUE,
        "another field": CustomRuleRightValueType.FIELD,
    }

    MATCH_MODE_OPTIONS = {
        "Match ALL conditions (AND)": CustomRuleMatchMode.ALL,
        "Match ANY condition (OR)": CustomRuleMatchMode.ANY,
    }

    SEVERITY_OPTIONS = {
        "High": CustomRuleSeverity.HIGH,
        "Medium": CustomRuleSeverity.MEDIUM,
        "Low": CustomRuleSeverity.LOW,
        "Info": CustomRuleSeverity.INFO,
    }

    COMPARISON_BASIS_OPTIONS = {
        "Compare vs Benchmark Rate": ComparisonBasis.BENCHMARK,
        "Compare Between Supplier Responses": ComparisonBasis.BETWEEN_RESPONSES,
    }

    ALL_SHEETS_LABEL = "All Sheets"

    def __init__(
        self,
        parent,
        fields,
        existing_rule=None,
        default_outlier_tolerance_percent=None,
        sheet_names=None,
    ):
        self.parent = parent
        self.fields = sorted(list(fields))
        self.sheet_names = [self.ALL_SHEETS_LABEL] + sorted(
            list(sheet_names or [])
        )
        self.result = None
        self.existing_rule = existing_rule

        self.window = tk.Toplevel(parent)
        self.window.title(
            "Edit Rule" if existing_rule is not None else "Rule Wizard"
        )
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

        self.outlier_tolerance_var = tk.StringVar(
            value=str(
                default_outlier_tolerance_percent
                if default_outlier_tolerance_percent is not None
                else 25.0
            )
        )

        self.advanced_match_mode_var = tk.StringVar(
            value=list(self.MATCH_MODE_OPTIONS.keys())[0]
        )

        # Each entry: {"left_field", "operator", "right_type",
        # "right_field", "right_value"} tk.StringVars for one
        # condition row in the free-form Advanced Rule builder.
        self.advanced_conditions = []
        self.advanced_conditions_container = None

        self.comparison_basis_var = tk.StringVar(
            value=list(self.COMPARISON_BASIS_OPTIONS.keys())[0]
        )
        self.comparison_sheet_var = tk.StringVar(value=self.ALL_SHEETS_LABEL)
        self.comparison_threshold_var = tk.StringVar()
        self.comparison_field_listbox = None
        self.comparison_body_frame = None
        self._pending_target_fields = []

        self.body_frame = None

        if existing_rule is not None:
            self._load_existing_rule(existing_rule)

        self._build_ui()
        self._refresh_body()

    # ==================================================
    # Editing an existing rule
    # ==================================================

    def _load_existing_rule(self, rule):
        self.rule_name_var.set(rule.name)
        self.message_var.set(rule.message or "")

        severity_value = (
            rule.severity.value
            if hasattr(rule.severity, "value")
            else str(rule.severity)
        )

        for label, value in self.SEVERITY_OPTIONS.items():
            if value.value == severity_value:
                self.severity_var.set(label)
                break

        if rule.rule_type == CustomRuleType.QUICK_RULES:
            self.mode_var.set("Quick Rules")
            self.quick_blanks_var.set(rule.check_blanks)
            self.quick_zeroes_var.set(rule.check_zeroes)
            self.quick_negatives_var.set(rule.check_negative_values)
            self.quick_duplicates_var.set(rule.check_duplicates)
            self.quick_outliers_var.set(rule.check_outliers)
            self.outlier_tolerance_var.set(
                str(rule.outlier_tolerance_percent)
            )

            return

        if rule.rule_type == CustomRuleType.COMPARISON_RULE:
            self.mode_var.set("Comparison Rule")
            self._load_existing_comparison_rule(rule)
            return

        self.mode_var.set("Advanced Rule")
        self._load_existing_advanced_rule(rule)

    def _load_existing_comparison_rule(self, rule):
        for label, value in self.COMPARISON_BASIS_OPTIONS.items():
            if value == rule.comparison_basis:
                self.comparison_basis_var.set(label)
                break

        self.comparison_sheet_var.set(
            rule.sheet_name or self.ALL_SHEETS_LABEL
        )

        if rule.comparison_threshold_percent is not None:
            self.comparison_threshold_var.set(
                str(rule.comparison_threshold_percent)
            )

        self.outlier_tolerance_var.set(
            str(rule.outlier_tolerance_percent)
        )

        self._pending_target_fields = list(rule.target_fields)

    def _load_existing_advanced_rule(self, rule):
        for label, value in self.MATCH_MODE_OPTIONS.items():
            if value == rule.match_mode:
                self.advanced_match_mode_var.set(label)
                break

        self.advanced_conditions = [
            self._condition_to_row_vars(condition)
            for condition in rule.conditions
        ]

    def _condition_to_row_vars(self, condition):
        operator_label = "equals"

        for label, value in self.OPERATOR_OPTIONS.items():
            if value == condition.operator:
                operator_label = label
                break

        right_type_label = "a fixed value"

        for label, value in self.RIGHT_TYPE_OPTIONS.items():
            if value == condition.right_value_type:
                right_type_label = label
                break

        right_field_value = ""
        right_value_value = ""

        if condition.right_value_type == CustomRuleRightValueType.FIELD:
            right_field_value = str(condition.right_value or "")
        elif condition.right_value_type == CustomRuleRightValueType.VALUE:
            right_value_value = str(
                condition.right_value
                if condition.right_value is not None
                else ""
            )

        return {
            "left_field": tk.StringVar(value=condition.left_field),
            "operator": tk.StringVar(value=operator_label),
            "right_type": tk.StringVar(value=right_type_label),
            "right_field": tk.StringVar(value=right_field_value),
            "right_value": tk.StringVar(value=right_value_value),
        }

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

        ttk.Radiobutton(
            frame,
            text="Comparison Rule",
            variable=self.mode_var,
            value="Comparison Rule",
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
            text="Save Rule" if self.existing_rule is not None else "Create Rule",
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

        mode = self.mode_var.get()

        if mode == "Quick Rules":
            self._build_quick_rules_body()
        elif mode == "Comparison Rule":
            self._build_comparison_rule_body()
        else:
            self._build_advanced_rules_body()

    # ==================================================
    # Quick Rules UI
    # ==================================================

    def _build_quick_rules_body(self):
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

        ttk.Label(
            outlier_frame,
            text=(
                "Flags a value that differs from the average of this "
                "supplier's other entries for that field by more than:"
            ),
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=5,
            pady=(5, 0),
        )

        ttk.Label(outlier_frame, text="Tolerance (%)").grid(
            row=1,
            column=0,
            sticky="w",
            padx=5,
            pady=5,
        )

        ttk.Combobox(
            outlier_frame,
            textvariable=self.outlier_tolerance_var,
            values=["10", "15", "25", "35", "50"],
            width=10,
        ).grid(
            row=1,
            column=1,
            sticky="w",
            padx=5,
            pady=5,
        )

    # ==================================================
    # Comparison Rule UI
    # ==================================================

    def _build_comparison_rule_body(self):
        basis_row = ttk.Frame(self.body_frame)
        basis_row.pack(anchor="w", pady=(0, 8), fill=tk.X)

        ttk.Label(basis_row, text="Compare:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )

        basis_combo = ttk.Combobox(
            basis_row,
            textvariable=self.comparison_basis_var,
            values=list(self.COMPARISON_BASIS_OPTIONS.keys()),
            state="readonly",
            width=32,
        )
        basis_combo.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        basis_combo.bind(
            "<<ComboboxSelected>>", self._refresh_comparison_basis_body
        )

        ttk.Label(basis_row, text="Sheet:").grid(
            row=0, column=2, sticky="w", padx=(20, 5), pady=5
        )

        ttk.Combobox(
            basis_row,
            textvariable=self.comparison_sheet_var,
            values=self.sheet_names,
            state="readonly",
            width=25,
        ).grid(row=0, column=3, sticky="w", padx=5, pady=5)

        fields_frame = ttk.LabelFrame(
            self.body_frame,
            text="Target Fields (none selected = all fields)",
            padding=5,
        )
        fields_frame.pack(fill=tk.X, pady=(0, 10))

        self.comparison_field_listbox = tk.Listbox(
            fields_frame,
            selectmode=tk.EXTENDED,
            height=6,
            exportselection=False,
        )
        self.comparison_field_listbox.pack(fill=tk.X)

        for field_name in self.fields:
            self.comparison_field_listbox.insert(tk.END, field_name)

        for index, field_name in enumerate(self.fields):
            if field_name in self._pending_target_fields:
                self.comparison_field_listbox.selection_set(index)

        self.comparison_body_frame = ttk.Frame(self.body_frame)
        self.comparison_body_frame.pack(fill=tk.X)

        self._refresh_comparison_basis_body()

    def _refresh_comparison_basis_body(self, event=None):
        for widget in self.comparison_body_frame.winfo_children():
            widget.destroy()

        basis = self.COMPARISON_BASIS_OPTIONS.get(
            self.comparison_basis_var.get()
        )

        if basis == ComparisonBasis.BENCHMARK:
            ttk.Label(
                self.comparison_body_frame,
                text="Threshold (%, blank = default):",
            ).grid(row=0, column=0, sticky="w", padx=5, pady=5)

            ttk.Entry(
                self.comparison_body_frame,
                textvariable=self.comparison_threshold_var,
                width=10,
            ).grid(row=0, column=1, sticky="w", padx=5, pady=5)

        else:
            ttk.Label(
                self.comparison_body_frame,
                text="Tolerance (%, blank = default):",
            ).grid(row=0, column=0, sticky="w", padx=5, pady=5)

            ttk.Combobox(
                self.comparison_body_frame,
                textvariable=self.outlier_tolerance_var,
                values=["10", "15", "25", "35", "50"],
                width=10,
            ).grid(row=0, column=1, sticky="w", padx=5, pady=5)

    # ==================================================
    # Advanced Rules UI
    # ==================================================

    def _build_advanced_rules_body(self):
        match_row = ttk.Frame(self.body_frame)
        match_row.pack(anchor="w", pady=(0, 10))

        ttk.Label(match_row, text="Combine conditions:").pack(side=tk.LEFT)

        ttk.Combobox(
            match_row,
            textvariable=self.advanced_match_mode_var,
            values=list(self.MATCH_MODE_OPTIONS.keys()),
            state="readonly",
            width=28,
        ).pack(side=tk.LEFT, padx=(8, 0))

        self.advanced_conditions_container = ttk.Frame(self.body_frame)
        self.advanced_conditions_container.pack(fill=tk.X)

        ttk.Button(
            self.body_frame,
            text="+ Add Condition",
            command=self._add_advanced_condition,
        ).pack(anchor="w", pady=(8, 0))

        if not self.advanced_conditions:
            self._add_advanced_condition()
        else:
            self._render_advanced_conditions()

    def _add_advanced_condition(self):
        self.advanced_conditions.append(
            {
                "left_field": tk.StringVar(),
                "operator": tk.StringVar(value="equals"),
                "right_type": tk.StringVar(
                    value=list(self.RIGHT_TYPE_OPTIONS.keys())[0]
                ),
                "right_field": tk.StringVar(),
                "right_value": tk.StringVar(),
            }
        )

        self._render_advanced_conditions()

    def _remove_advanced_condition(self, index):
        del self.advanced_conditions[index]
        self._render_advanced_conditions()

    def _render_advanced_conditions(self):
        for widget in self.advanced_conditions_container.winfo_children():
            widget.destroy()

        for index, condition_vars in enumerate(self.advanced_conditions):
            self._render_advanced_condition_row(index, condition_vars)

    def _render_advanced_condition_row(self, index, condition_vars):
        row = ttk.Frame(self.advanced_conditions_container)
        row.pack(fill=tk.X, pady=3)

        ttk.Combobox(
            row,
            textvariable=condition_vars["left_field"],
            values=self.fields,
            state="readonly",
            width=28,
        ).pack(side=tk.LEFT, padx=(0, 5))

        operator_combo = ttk.Combobox(
            row,
            textvariable=condition_vars["operator"],
            values=list(self.OPERATOR_OPTIONS.keys()),
            state="readonly",
            width=20,
        )
        operator_combo.pack(side=tk.LEFT, padx=5)
        operator_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self._render_advanced_conditions(),
        )

        if condition_vars["operator"].get() not in self.NO_RIGHT_SIDE_OPERATORS:

            right_type_combo = ttk.Combobox(
                row,
                textvariable=condition_vars["right_type"],
                values=list(self.RIGHT_TYPE_OPTIONS.keys()),
                state="readonly",
                width=14,
            )
            right_type_combo.pack(side=tk.LEFT, padx=5)
            right_type_combo.bind(
                "<<ComboboxSelected>>",
                lambda event: self._render_advanced_conditions(),
            )

            if (
                self.RIGHT_TYPE_OPTIONS.get(condition_vars["right_type"].get())
                == CustomRuleRightValueType.FIELD
            ):
                ttk.Combobox(
                    row,
                    textvariable=condition_vars["right_field"],
                    values=self.fields,
                    state="readonly",
                    width=28,
                ).pack(side=tk.LEFT, padx=5)
            else:
                ttk.Entry(
                    row,
                    textvariable=condition_vars["right_value"],
                    width=20,
                ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            row,
            text="Remove",
            command=lambda i=index: self._remove_advanced_condition(i),
        ).pack(side=tk.LEFT, padx=(10, 0))

    # ==================================================
    # Rule creation
    # ==================================================

    def _create_rule(self):
        mode = self.mode_var.get()

        if mode == "Quick Rules":
            new_rule = self._create_quick_rule()
        elif mode == "Comparison Rule":
            new_rule = self._create_comparison_rule()
        else:
            new_rule = self._create_advanced_rule()

        if new_rule is None:
            return

        if self.existing_rule is not None:
            new_rule.enabled = self.existing_rule.enabled
            self.existing_rule.__dict__.update(new_rule.__dict__)
            self.result = self.existing_rule
        else:
            self.result = new_rule

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
            outlier_tolerance_percent=tolerance,
            target_fields=[],
        )

    def _create_comparison_rule(self):
        rule_name = self.rule_name_var.get().strip()
        basis = self.COMPARISON_BASIS_OPTIONS.get(
            self.comparison_basis_var.get()
        )

        if rule_name == "":
            rule_name = self.comparison_basis_var.get()

        sheet_name = self.comparison_sheet_var.get()

        if sheet_name == self.ALL_SHEETS_LABEL:
            sheet_name = None

        target_fields = [
            self.comparison_field_listbox.get(index)
            for index in self.comparison_field_listbox.curselection()
        ] if self.comparison_field_listbox is not None else []

        threshold_percent = None
        outlier_tolerance_percent = 25.0

        if basis == ComparisonBasis.BENCHMARK:
            threshold_text = self.comparison_threshold_var.get().strip()

            if threshold_text != "":
                try:
                    threshold_percent = float(threshold_text)
                except ValueError:
                    messagebox.showwarning(
                        "Invalid threshold",
                        "Please enter a valid numeric threshold, or "
                        "leave it blank to use the global default.",
                    )
                    return None

        else:
            try:
                outlier_tolerance_percent = float(
                    self.outlier_tolerance_var.get()
                )
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
            sheet_name=sheet_name,
            message=self.message_var.get().strip(),
            rule_type=CustomRuleType.COMPARISON_RULE,
            target_fields=target_fields,
            comparison_basis=basis,
            comparison_threshold_percent=threshold_percent,
            outlier_tolerance_percent=outlier_tolerance_percent,
        )

    def _create_advanced_rule(self):
        if not self.advanced_conditions:
            messagebox.showwarning(
                "No Conditions",
                "Add at least one condition.",
            )
            return None

        conditions = []

        for condition_vars in self.advanced_conditions:

            left_field = condition_vars["left_field"].get().strip()
            operator = self.OPERATOR_OPTIONS.get(
                condition_vars["operator"].get()
            )

            if left_field == "" or operator is None:
                messagebox.showwarning(
                    "Missing Condition Detail",
                    "Every condition needs a field and an operator.",
                )
                return None

            if operator in (
                CustomRuleOperator.IS_BLANK,
                CustomRuleOperator.IS_NOT_BLANK,
            ):
                conditions.append(
                    CustomRuleCondition(
                        left_field=left_field,
                        operator=operator,
                        right_value_type=CustomRuleRightValueType.BLANK,
                        right_value=None,
                    )
                )
                continue

            right_type = self.RIGHT_TYPE_OPTIONS.get(
                condition_vars["right_type"].get()
            )

            if right_type == CustomRuleRightValueType.FIELD:

                right_field = condition_vars["right_field"].get().strip()

                if right_field == "":
                    messagebox.showwarning(
                        "Missing Condition Detail",
                        "Select the field to compare against.",
                    )
                    return None

                conditions.append(
                    CustomRuleCondition(
                        left_field=left_field,
                        operator=operator,
                        right_value_type=CustomRuleRightValueType.FIELD,
                        right_value=right_field,
                    )
                )
                continue

            value = self._parse_value(
                condition_vars["right_value"].get()
            )

            if value is None:
                messagebox.showwarning(
                    "Invalid Value",
                    "Enter a valid comparison value.",
                )
                return None

            conditions.append(
                CustomRuleCondition(
                    left_field=left_field,
                    operator=operator,
                    right_value_type=CustomRuleRightValueType.VALUE,
                    right_value=value,
                )
            )

        rule_name = self.rule_name_var.get().strip()

        if rule_name == "":
            rule_name = f"{conditions[0].left_field} Condition"

        match_mode = self.MATCH_MODE_OPTIONS.get(
            self.advanced_match_mode_var.get(),
            CustomRuleMatchMode.ALL,
        )

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