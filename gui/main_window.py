# gui/main_window.py

import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

import config
from gui.workbook_mapper_dialog import WorkbookMapperDialog
from gui.mapping_profile_dialog import MappingProfileDialog
from gui.rule_manager_dialog import RuleManagerDialog

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
                "input fields, or load a saved mapping profile. If a "
                "benchmark workbook is loaded, reopen this step to see "
                "the benchmark rate for each cell in the inspector."
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
                "Create, edit, enable/disable, or delete rules that "
                "catch blanks, zeroes, duplicates, and outliers in "
                "supplier responses."
            ),
            buttons=[("Manage Rules...", self._manage_rules)],
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
                "Compare each supplier's confirmed field values "
                "against the benchmark (if loaded) or statistically "
                "against the other suppliers, and generate a "
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

        # Step 6: Run Analysis (needs mapping and suppliers)
        ready_for_analysis = (
            self.workbook_schema is not None
            and bool(self.supplier_files)
        )

        self._set_step_enabled("analysis", ready_for_analysis)

        if self.workbook_schema is None:
            self._set_step_status("analysis", "Review mapping first")
        elif not self.supplier_files:
            self._set_step_status("analysis", "Load supplier workbooks first")
        else:
            self._set_step_status("analysis", "Ready")

    # ==================================================
    # Error Handling
    # ==================================================

    def _handle_error(self, title, error):
        """
        Show a clear error dialog and log the failure, instead of
        letting an unhandled exception (bad/corrupt/locked file,
        unexpected workbook layout, etc.) crash the whole app.
        """

        message = str(error) or error.__class__.__name__

        self._log(f"{title}: {message}")

        messagebox.showerror(title, message)

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

        try:

            template_workbook = (
                self.workbook_loader_service.load_workbook(
                    file_path
                )
            )

        except Exception as error:

            self._handle_error(
                "Failed to Load Template", error
            )

            return

        self.template_file = file_path
        self.template_workbook = template_workbook

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

        try:

            benchmark_workbook = (
                self.workbook_loader_service.load_workbook(
                    file_path
                )
            )

        except Exception as error:

            self._handle_error(
                "Failed to Load Benchmark", error
            )

            return

        self.benchmark_file = file_path
        self.benchmark_workbook = benchmark_workbook

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

        try:

            self.workbook_schema = (
                self.schema_service.build_schema(
                    self.template_workbook
                )
            )

        except Exception as error:

            self._handle_error(
                "Failed to Build Schema", error
            )

            return

        dialog = WorkbookMapperDialog(
            parent=self.root,
            workbook=self.template_workbook,
            workbook_schema=self.workbook_schema,
            benchmark_workbook=self.benchmark_workbook,
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

            try:

                self.workbook_schema = (
                    self.mapping_profile_service.apply_profile(
                        self.workbook_schema,
                        result["profile_data"],
                    )
                )

            except Exception as error:

                self._handle_error(
                    "Failed to Apply Profile", error
                )

                return

            self._refresh_state()

            self._log(
                f"Applied profile: {result['profile_name']}"
            )

    # ==================================================
    # Rules
    # ==================================================

    def _manage_rules(self):

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

        dialog = RuleManagerDialog(
            self.root,
            self.custom_rules_service,
            fields,
        )

        self.custom_rules = dialog.show()

        self._refresh_state()

        self._log(
            f"{len(self.custom_rules)} rule(s) saved"
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

        if self.workbook_schema is None:

            messagebox.showwarning(
                "Mapping Required",
                "Please review the template's field mapping first.",
            )

            return

        supplier_workbooks = []

        for supplier_file in self.supplier_files:

            try:

                workbook = (
                    self.workbook_loader_service.load_workbook(
                        supplier_file
                    )
                )

            except Exception as error:

                self._log(
                    f"Skipped {Path(supplier_file).name}: {error}"
                )

                continue

            supplier_workbooks.append(
                (Path(supplier_file).stem, workbook)
            )

        if not supplier_workbooks:

            self._handle_error(
                "Failed to Load Supplier Workbooks",
                "None of the selected supplier workbooks could be loaded.",
            )

            return

        comparison_mode = (
            "against the benchmark workbook"
            if self.benchmark_workbook is not None
            else "statistically across suppliers"
        )

        if self.benchmark_workbook is not None:

            missing_sheets = self.analysis_service.get_missing_sheets(
                self.benchmark_workbook, self.workbook_schema
            )

            if missing_sheets:

                self._log(
                    "Warning: benchmark workbook is missing "
                    f"worksheet(s) {', '.join(missing_sheets)} - "
                    "benchmark comparison for fields on those sheets "
                    "will be skipped."
                )

        self._log(
            f"Running analysis on {len(supplier_workbooks)} "
            f"supplier workbook(s), comparing {comparison_mode}."
        )

        try:

            results = self.analysis_service.analyse_suppliers(
                workbook_schema=self.workbook_schema,
                supplier_workbooks=supplier_workbooks,
                benchmark_workbook=self.benchmark_workbook,
                custom_rules=self.custom_rules,
                output_folder=config.DEFAULT_OUTPUT_FOLDER,
            )

        except Exception as error:

            self._handle_error(
                "Analysis Failed", error
            )

            return

        for result in results:

            self._log(
                f"{result.supplier_name}: "
                f"{len(result.findings)} findings"
            )

        messagebox.showinfo(
            "Complete",
            (
                f"Analysis complete.\n\n"
                f"Reports generated: "
                f"{len(results)}"
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
