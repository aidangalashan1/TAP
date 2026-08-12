# gui/threshold_settings_dialog.py

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from rules.custom_rule_models import OutlierMethod
from rules.threshold_settings import ThresholdSettings


class ThresholdSettingsDialog:
    """
    Lets the user set the global default thresholds used to flag
    findings, unless a rule overrides them with its own settings:

    - Benchmark comparison always uses raw % difference, since it
      compares a supplier value against a single known reference
      value.
    - Between-response (cross-supplier) outlier detection can be
      based on the group mean/standard deviation (Z Score) or the
      group median/quartile range (IQR).
    """

    OUTLIER_METHODS = {
        "Mean / Standard Deviation (Z Score)": OutlierMethod.Z_SCORE,
        "Median / Quartile Range (IQR)": OutlierMethod.IQR,
    }

    def __init__(self, parent, settings):
        self.parent = parent
        self.settings = settings
        self.result = None

        self.window = tk.Toplevel(parent)
        self.window.title("Threshold Settings")
        self.window.geometry("520x320")
        self.window.transient(parent)
        self.window.grab_set()

        self._build_ui()

    def show(self):
        self.parent.wait_window(self.window)
        return self.result

    def _build_ui(self):
        main = ttk.Frame(self.window, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            main,
            text="Benchmark Comparison",
            font=("", 10, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            main,
            text=(
                "Raw % difference from the benchmark rate at which a "
                "supplier value is flagged."
            ),
            wraplength=470,
            foreground="#555555",
        ).pack(anchor="w", pady=(0, 5))

        benchmark_row = ttk.Frame(main)
        benchmark_row.pack(anchor="w", pady=(0, 15))

        ttk.Label(benchmark_row, text="Threshold (%):").pack(side=tk.LEFT)

        self.benchmark_percent_var = tk.StringVar(
            value=str(self.settings.benchmark_threshold_percent)
        )

        ttk.Entry(
            benchmark_row,
            textvariable=self.benchmark_percent_var,
            width=10,
        ).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Separator(main).pack(fill=tk.X, pady=10)

        ttk.Label(
            main,
            text="Between-Response Outlier Detection",
            font=("", 10, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            main,
            text=(
                "Default basis used to flag one supplier's response "
                "as an outlier compared to the other suppliers' "
                "responses to the same field (no benchmark involved). "
                "Individual rules in the Rule Wizard can override this."
            ),
            wraplength=470,
            foreground="#555555",
        ).pack(anchor="w", pady=(0, 5))

        method_row = ttk.Frame(main)
        method_row.pack(anchor="w", pady=(0, 8))

        ttk.Label(method_row, text="Method:").pack(side=tk.LEFT)

        self.outlier_method_var = tk.StringVar(
            value=self._method_label(self.settings.default_outlier_method)
        )

        ttk.Combobox(
            method_row,
            textvariable=self.outlier_method_var,
            values=list(self.OUTLIER_METHODS.keys()),
            state="readonly",
            width=35,
        ).pack(side=tk.LEFT, padx=(8, 0))

        tolerance_row = ttk.Frame(main)
        tolerance_row.pack(anchor="w")

        ttk.Label(tolerance_row, text="Tolerance:").pack(side=tk.LEFT)

        self.outlier_tolerance_var = tk.StringVar(
            value=str(self.settings.default_outlier_tolerance)
        )

        ttk.Entry(
            tolerance_row,
            textvariable=self.outlier_tolerance_var,
            width=10,
        ).pack(side=tk.LEFT, padx=(8, 0))

        footer = ttk.Frame(main)
        footer.pack(fill=tk.X, pady=(20, 0), side=tk.BOTTOM)

        ttk.Button(
            footer, text="Save", command=self._save
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            footer, text="Cancel", command=self.window.destroy
        ).pack(side=tk.RIGHT)

    def _method_label(self, method):
        for label, value in self.OUTLIER_METHODS.items():
            if value == method:
                return label

        return list(self.OUTLIER_METHODS.keys())[0]

    def _save(self):
        try:
            benchmark_threshold_percent = float(
                self.benchmark_percent_var.get()
            )
            outlier_tolerance = float(self.outlier_tolerance_var.get())
        except ValueError:
            messagebox.showerror(
                "Invalid Value",
                "Threshold and tolerance must be numbers.",
            )
            return

        outlier_method = self.OUTLIER_METHODS.get(
            self.outlier_method_var.get(), OutlierMethod.Z_SCORE
        )

        self.result = ThresholdSettings(
            benchmark_threshold_percent=benchmark_threshold_percent,
            default_outlier_method=outlier_method,
            default_outlier_tolerance=outlier_tolerance,
        )

        self.window.destroy()
