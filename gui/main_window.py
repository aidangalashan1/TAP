# gui/main_window.py

import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

from gui.workbook_mapper_dialog import WorkbookMapperDialog
from gui.mapping_profile_dialog import MappingProfileDialog
from gui.rule_wizard_dialog import RuleWizardDialog

from services.analysis_service import AnalysisService
from services.custom_rules_service import CustomRulesService
from services.mapping_profile_service import MappingProfileService
from services.schema_service import SchemaService
from services.workbook_loader_service import WorkbookLoaderService


class MainWindow:

    def __init__(self, root):

        self.root = root

        self.root.title("Tender Analysis Platform")
        self.root.geometry("1300x900")

        self.analysis_service = AnalysisService()
        self.schema_service = SchemaService()
        self.custom_rules_service = CustomRulesService()
        self.mapping_profile_service = MappingProfileService()
        self.workbook_loader_service = WorkbookLoaderService()

        self.template_file = ""
        self.benchmark_file = ""

        self.template_workbook = None
        self.benchmark_workbook = None

        self.supplier_files = []

        self.workbook_schema = None

        self.custom_rules = (
            self.custom_rules_service.load_rules()
        )

        # Populated by _build_steps; used by _refresh_state to
        # enable/disable steps and show per-step status text.
        self.step_status_labels = {}
        self.step_buttons = {}

        self._build_ui()
        self._refresh_state()

    # ==================================================
    # UI
    # ==================================================

    def _build_ui(self):

        main = ttk.Frame(
            self.root,
            padding=10,
        )

        main.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self._build_header(main)
        self._build_steps(main)
        self._build_log_section(main)

    def _build_header(self, parent):

        header = ttk.Frame(parent)

        header.pack(
            fill=tk.X,
            pady=(0, 15),
        )

        ttk.Label(
            header,
            text="Tender Analysis Platform",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            header,
            text=(
                "Compare supplier tender workbooks against your "
                "template and rules to automatically flag blanks, "
                "outliers, and pricing anomalies."
            ),
        ).pack(anchor="w")

    def _build_steps(self, parent):

        steps = ttk.Frame(parent)

        steps.pack(
            fill=tk.X,
            pady=(0, 10),
        )

        self._build_step(
            steps,
            key="template",
            number=1,
            title="Load Template Workbook",
            description=(
                "Choose the blank tender template. Its layout "
                "is used to identify where supplier answers go."
            ),
            buttons=[("Choose Template...", self._select_template)],
        )

        self._build_step(
            steps,
            key="mapping",
            number=2,
            title="Review Field Mapping",
            description=(
                "Confirm which cells in the template are supplier "
                "input fields, or load a saved mapping profile."
            ),
            buttons=[
                ("Review Mapping...", self._review_mapping),
                ("Mapping Profiles...", self._manage_profiles),
            ],
        )

        self._build_step(
            steps,
            key="benchmark",
            number=3,
            title="Load Benchmark Workbook (Optional)",
            description=(
                "Choose a benchmark workbook to compare supplier "
                "pricing against known reference values."
            ),
            buttons=[("Choose Benchmark...", self._select_benchmark)],
        )

        self._build_step(
            steps,
            key="rules",
            number=4,
            title="Define Rules (Optional)",
            description=(
                "Add rules to catch blanks, zeroes, duplicates, "
                "and outliers in supplier responses."
            ),
            buttons=[("Rule Wizard...", self._open_rule_wizard)],
        )

        self._build_step(
            steps,
            key="suppliers",
            number=5,
            title="Load Supplier Workbooks",
            description=(
                "Choose one or more completed supplier workbooks "
                "to analyse."
            ),
            buttons=[("Choose Suppliers...", self._select_suppliers)],
        )

        self._build_step(
            steps,
            key="analysis",
            number=6,
            title="Run Analysis",
            description=(
                "Analyse every supplier workbook and generate a "
                "findings report for each one."
            ),
            buttons=[("Run Analysis", self._run_analysis)],
        )

    def _build_step(
        self,
        parent,
        key,
        number,
        title,
        description,
        buttons,
    ):

        frame = ttk.LabelFrame(
            parent,
            text=f"Step {number}: {title}",
            padding=10,
        )

        frame.pack(
            fill=tk.X,
            pady=(0, 6),
        )

        ttk.Label(
            frame,
            text=description,
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))

        row = ttk.Frame(frame)

        row.pack(fill=tk.X)

        self.step_buttons[key] = []

        for label, command in buttons:

            button = ttk.Button(
                row,
                text=label,
                command=command,
            )

            button.pack(side=tk.LEFT, padx=(0, 8))

            self.step_buttons[key].append(button)

        status_label = ttk.Label(
            row,
            text="Not started",
            foreground="#888888",
        )

        status_label.pack(side=tk.LEFT, padx=(12, 0))

        self.step_status_labels[key] = status_label

    def _build_log_section(self, parent):

        frame = ttk.LabelFrame(
            parent,
            text="Activity Log",
            padding=10,
        )

        frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self.log_text = tk.Text(
            frame,
            wrap="word",
            height=8,
        )

        self.log_text.pack(
            fill=tk.BOTH,
            expand=True,
        )

    # ==================================================
    # State / Step Progress
    # ==================================================

    def _set_step_status(self, key, text, done=False):

        label = self.step_status_labels.get(key)

        if label is None:
            return

        label.configure(
            text=(f"✓ {text}" if done else text),
            foreground=("#2e7d32" if done else "#888888"),
        )

    def _set_step_enabled(self, key, enabled):

        state = "normal" if enabled else "disabled"

        for button in self.step_buttons.get(key, []):
            button.configure(state=state)

    def _refresh_state(self):

        # Step 1: Template
        if self.template_workbook is not None:
            self._set_step_status(
                "template",
                Path(self.template_file).name,
                done=True,
            )
        else:
            self._set_step_status("template", "Not started")

        # Step 2: Mapping (needs template)
        self._set_step_enabled(
            "mapping", self.template_workbook is not None
        )

        if self.workbook_schema is not None:
            self._set_step_status("mapping", "Mapping reviewed", done=True)
        elif self.template_workbook is not None:
            self._set_step_status("mapping", "Not reviewed yet")
        else:
            self._set_step_status("mapping", "Load a template first")

        # Step 3: Benchmark (optional, always available)
        if self.benchmark_workbook is not None:
            self._set_step_status(
                "benchmark",
                Path(self.benchmark_file).name,
                done=True,
            )
        else:
            self._set_step_status("benchmark", "Skipped")

        # Step 4: Rules (needs mapping)
        self._set_step_enabled(
            "rules", self.workbook_schema is not None
        )

        if self.custom_rules:
            self._set_step_status(
                "rules",
                f"{len(self.custom_rules)} rule(s) defined",
                done=True,
            )
        elif self.workbook_schema is not None:
            self._set_step_status("rules", "None defined yet")
        else:
            self._set_step_status("rules", "Review mapping first")

        # Step 5: Suppliers
        if self.supplier_files:
            self._set_step_status(
                "suppliers",
                f"{len(self.supplier_files)} workbook(s) selected",
                done=True,
            )
        else:
            self._set_step_status("suppliers", "Not started")

        # Step 6: Run Analysis (needs suppliers)
        self._set_step_enabled(
            "analysis", bool(self.supplier_files)
        )

        if not self.supplier_files:
            self._set_step_status("analysis", "Load supplier workbooks first")
        else:
            self._set_step_status("analysis", "Ready")

    # ==================================================
    # File Selection
    # ==================================================

    def _select_template(self):

        file_path = filedialog.askopenfilename(
            filetypes=[
                ("Excel Files", "*.xlsx *.xlsm *.xls")
            ]
        )

        if not file_path:
            return

        self.template_file = file_path

        self.template_workbook = (
            self.workbook_loader_service.load_workbook(
                file_path
            )
        )

        self._refresh_state()

        self._log(
            f"Loaded template workbook: {Path(file_path).name}"
        )

    def _select_benchmark(self):

        file_path = filedialog.askopenfilename(
            filetypes=[
                ("Excel Files", "*.xlsx *.xlsm *.xls")
            ]
        )

        if not file_path:
            return

        self.benchmark_file = file_path

        self.benchmark_workbook = (
            self.workbook_loader_service.load_workbook(
                file_path
            )
        )

        self._refresh_state()

        self._log(
            f"Loaded benchmark workbook: {Path(file_path).name}"
        )

    def _select_suppliers(self):

        files = filedialog.askopenfilenames(
            filetypes=[
                ("Excel Files", "*.xlsx *.xlsm *.xls")
            ]
        )

        if not files:
            return

        self.supplier_files = list(files)

        self._refresh_state()

        self._log(
            f"{len(self.supplier_files)} supplier workbook(s) selected"
        )

    # ==================================================
    # Mapping
    # ==================================================

    def _review_mapping(self):

        if self.template_workbook is None:

            messagebox.showwarning(
                "Template Required",
                "Please load a template workbook.",
            )

            return

        self.workbook_schema = (
            self.schema_service.build_schema(
                self.template_workbook
            )
        )

        dialog = WorkbookMapperDialog(
            parent=self.root,
            workbook=self.template_workbook,
            workbook_schema=self.workbook_schema,
        )

        result = dialog.show()

        if result is not None:
            self.workbook_schema = result

            self._log(
                "Workbook mapping updated"
            )

        self._refresh_state()

    def _manage_profiles(self):

        dialog = MappingProfileDialog(
            parent=self.root,
            workbook_schema=self.workbook_schema,
        )

        result = dialog.show()

        if not result:
            return

        if result["action"] == "load":

            self.workbook_schema = (
                self.mapping_profile_service.apply_profile(
                    self.workbook_schema,
                    result["profile_data"],
                )
            )

            self._refresh_state()

            self._log(
                f"Applied profile: {result['profile_name']}"
            )

    # ==================================================
    # Rules
    # ==================================================

    def _open_rule_wizard(self):

        if self.workbook_schema is None:

            messagebox.showwarning(
                "Mapping Required",
                "Review workbook mapping first.",
            )

            return

        fields = (
            self.schema_service.get_field_names(
                self.workbook_schema
            )
        )

        dialog = RuleWizardDialog(
            self.root,
            fields,
        )

        result = dialog.show()

        if result is None:
            return

        self.custom_rules.append(result)

        self.custom_rules_service.save_rules(
            self.custom_rules
        )

        self._refresh_state()

        self._log(
            f"Created rule: {result.name}"
        )

    # ==================================================
    # Analysis
    # ==================================================

    def _run_analysis(self):

        if not self.supplier_files:

            messagebox.showwarning(
                "Supplier Files Required",
                "Please select supplier workbooks.",
            )

            return

        reports_generated = 0

        for supplier_file in self.supplier_files:

            workbook = (
                self.workbook_loader_service.load_workbook(
                    supplier_file
                )
            )

            result = (
                self.analysis_service.analyse_workbook(
                    supplier_name=Path(
                        supplier_file
                    ).stem,
                    workbook=workbook,
                    custom_rules=self.custom_rules,
                    output_folder="reports",
                )
            )

            reports_generated += 1

            self._log(
                f"{result.supplier_name}: "
                f"{len(result.findings)} findings"
            )

        messagebox.showinfo(
            "Complete",
            (
                f"Analysis complete.\n\n"
                f"Reports generated: "
                f"{reports_generated}"
            ),
        )

    # ==================================================
    # Logging
    # ==================================================

    def _log(self, message):

        self.log_text.insert(
            tk.END,
            f"{message}\n",
        )

        self.log_text.see(tk.END)
