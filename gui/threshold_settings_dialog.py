# gui/threshold_settings_dialog.py

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from rules.threshold_settings import ThresholdSettings


class ThresholdSettingsDialog:
    """
    Lets the user set the global default thresholds used to flag
    findings, unless a rule overrides them with its own settings.

    Both bases use the same raw % difference logic: benchmark
    comparison measures against a single known reference value,
    between-response comparison measures against the group average
    of every supplier's response to that same field.
    """

    def __init__(self, parent, settings):
        self.parent = parent
        self.settings = settings
        self.result = None

        self.window = tk.Toplevel(parent)
        self.window.title("Threshold Settings")
        self.window.geometry("420x200")
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
        ).pack(anchor="w", pady=(0, 5))

        benchmark_row = ttk.Frame(main)
        benchmark_row.pack(anchor="w", pady=(0, 15))

        ttk.Label(
            benchmark_row, text="Threshold vs benchmark rate (%):"
        ).pack(side=tk.LEFT)

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
        ).pack(anchor="w", pady=(0, 5))

        tolerance_row = ttk.Frame(main)
        tolerance_row.pack(anchor="w")

        ttk.Label(
            tolerance_row, text="Tolerance around group average (%):"
        ).pack(side=tk.LEFT)

        self.outlier_tolerance_var = tk.StringVar(
            value=str(self.settings.default_outlier_tolerance_percent)
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

    def _save(self):
        try:
            benchmark_threshold_percent = float(
                self.benchmark_percent_var.get()
            )
            outlier_tolerance_percent = float(
                self.outlier_tolerance_var.get()
            )
        except ValueError:
            messagebox.showerror(
                "Invalid Value",
                "Threshold and tolerance must be numbers.",
            )
            return

        self.result = ThresholdSettings(
            benchmark_threshold_percent=benchmark_threshold_percent,
            default_outlier_tolerance_percent=outlier_tolerance_percent,
        )

        self.window.destroy()
