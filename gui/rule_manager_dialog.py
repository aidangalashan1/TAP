# gui/rule_manager_dialog.py

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from gui.rule_wizard_dialog import RuleWizardDialog
from rules.custom_rule_models import CustomRuleType


class RuleManagerDialog:
    """
    Lists saved custom rules and lets the user create new ones
    (via the Rule Wizard), enable/disable them, or delete them.

    Changes are saved to disk immediately as they happen, so
    closing the window (including via the X button) never loses
    a change made in this dialog.
    """

    def __init__(
        self,
        parent,
        custom_rules_service,
        fields,
        threshold_settings=None,
        sheet_names=None,
    ):
        self.parent = parent
        self.custom_rules_service = custom_rules_service
        self.fields = fields
        self.threshold_settings = threshold_settings
        self.sheet_names = sheet_names or []

        self.rules = list(custom_rules_service.load_rules())

        self.rule_lookup = {}

        self.window = tk.Toplevel(parent)
        self.window.title("Manage Rules")
        self.window.geometry("800x500")
        self.window.transient(parent)
        self.window.grab_set()

        self.rule_tree = None

        self._build_ui()
        self._load_rules()

    def show(self):
        self.parent.wait_window(self.window)
        return self.rules

    # ==================================================
    # UI
    # ==================================================

    def _build_ui(self):
        main = ttk.Frame(self.window, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        self.rule_tree = ttk.Treeview(
            main,
            columns=("type", "severity", "status"),
            show="headings",
            height=15,
        )

        self.rule_tree.heading("type", text="Name / Type")
        self.rule_tree.heading("severity", text="Severity")
        self.rule_tree.heading("status", text="Status")

        self.rule_tree.column("type", width=380)
        self.rule_tree.column("severity", width=120)
        self.rule_tree.column("status", width=120)

        self.rule_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        button_row = ttk.Frame(main)
        button_row.pack(fill=tk.X)

        ttk.Button(
            button_row,
            text="New Rule...",
            command=self._new_rule,
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            button_row,
            text="Edit Rule...",
            command=self._edit_rule,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_row,
            text="Enable / Disable",
            command=self._toggle_enabled,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_row,
            text="Delete Rule",
            command=self._delete_rule,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_row,
            text="Close",
            command=self._close,
        ).pack(side=tk.RIGHT)

    # ==================================================
    # Rule List
    # ==================================================

    def _load_rules(self):
        for item in self.rule_tree.get_children():
            self.rule_tree.delete(item)

        self.rule_lookup.clear()

        for rule in self.rules:

            rule_type_label = self._rule_type_label(rule)

            item = self.rule_tree.insert(
                "",
                tk.END,
                values=(
                    f"{rule.name} ({rule_type_label})",
                    rule.severity.value
                    if hasattr(rule.severity, "value")
                    else rule.severity,
                    "Enabled" if rule.enabled else "Disabled",
                ),
            )

            self.rule_lookup[item] = rule

    def _rule_type_label(self, rule):
        if rule.rule_type == CustomRuleType.QUICK_RULES:
            return "Quick Rules"

        if rule.rule_type == CustomRuleType.COMPARISON_RULE:
            basis = rule.comparison_basis

            if basis is not None and hasattr(basis, "value"):
                basis = basis.value

            if basis == "BENCHMARK":
                return "Comparison Rule (vs Benchmark)"

            if basis == "BETWEEN_RESPONSES":
                return "Comparison Rule (Between Responses)"

            return "Comparison Rule"

        return "Advanced Rule"

    def _selected_rule(self):
        selection = self.rule_tree.selection()

        if not selection:
            return None

        return self.rule_lookup.get(selection[0])

    def _save_and_reload(self):
        self.custom_rules_service.save_rules(self.rules)
        self._load_rules()

    # ==================================================
    # Actions
    # ==================================================

    def _new_rule(self):
        default_outlier_tolerance_percent = None

        if self.threshold_settings is not None:
            default_outlier_tolerance_percent = (
                self.threshold_settings.default_outlier_tolerance_percent
            )

        dialog = RuleWizardDialog(
            self.window,
            self.fields,
            sheet_names=self.sheet_names,
            default_outlier_tolerance_percent=default_outlier_tolerance_percent,
        )

        result = dialog.show()

        if result is None:
            return

        self.rules.append(result)

        self._save_and_reload()

    def _edit_rule(self):
        rule = self._selected_rule()

        if rule is None:
            messagebox.showinfo("No Rule Selected", "Select a rule first.")
            return

        dialog = RuleWizardDialog(
            self.window,
            self.fields,
            existing_rule=rule,
            sheet_names=self.sheet_names,
        )

        result = dialog.show()

        if result is None:
            return

        self._save_and_reload()

    def _toggle_enabled(self):
        rule = self._selected_rule()

        if rule is None:
            messagebox.showinfo("No Rule Selected", "Select a rule first.")
            return

        rule.enabled = not rule.enabled

        self._save_and_reload()

    def _delete_rule(self):
        rule = self._selected_rule()

        if rule is None:
            messagebox.showinfo("No Rule Selected", "Select a rule first.")
            return

        confirmed = messagebox.askyesno(
            "Delete Rule",
            f"Delete rule '{rule.name}'? This cannot be undone.",
        )

        if not confirmed:
            return

        self.rules = [r for r in self.rules if r is not rule]

        self._save_and_reload()

    def _close(self):
        self.window.destroy()
