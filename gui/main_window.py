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
        self.root.geometry("1300x850")

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

        self._build_ui()

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

        self._build_file_section(main)
        self._build_action_section(main)
        self._build_status_section(main)
        self._build_log_section(main)

    def _build_file_section(self, parent):

        frame = ttk.LabelFrame(
            parent,
            text="Workbooks",
            padding=10,
        )

        frame.pack(
            fill=tk.X,
            pady=(0, 10),
        )

        ttk.Button(
            frame,
            text="Template",
            command=self._select_template,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            frame,
            text="Benchmark",
            command=self._select_benchmark,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            frame,
            text="Suppliers",
            command=self._select_suppliers,
        ).pack(side=tk.LEFT, padx=5)

    def _build_action_section(self, parent):

        frame = ttk.LabelFrame(
            parent,
            text="Actions",
            padding=10,
        )

        frame.pack(
            fill=tk.X,
            pady=(0, 10),
        )

        ttk.Button(
            frame,
            text="Review Mapping",
            command=self._review_mapping,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            frame,
            text="Profiles",
            command=self._manage_profiles,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            frame,
            text="Rule Wizard",
            command=self._open_rule_wizard,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            frame,
            text="Run Analysis",
            command=self._run_analysis,
        ).pack(side=tk.LEFT, padx=5)

    def _build_status_section(self, parent):

        frame = ttk.LabelFrame(
            parent,
            text="Status",
            padding=10,
        )

        frame.pack(
            fill=tk.X,
            pady=(0, 10),
        )

        self.template_label = ttk.Label(
            frame,
            text="Template: Not loaded",
        )

        self.template_label.pack(
            anchor="w"
        )

        self.benchmark_label = ttk.Label(
            frame,
            text="Benchmark: Not loaded",
        )

        self.benchmark_label.pack(
            anchor="w"
        )

        self.rules_label = ttk.Label(
            frame,
            text=(
                f"Rules: "
                f"{len(self.custom_rules)}"
            )
        )

        self.rules_label.pack(
            anchor="w"
        )

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
        )

        self.log_text.pack(
            fill=tk.BOTH,
            expand=True,
        )

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

        self.template_label.configure(
            text=f"Template: {Path(file_path).name}"
        )

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

        self.benchmark_label.configure(
            text=f"Benchmark: {Path(file_path).name}"
        )

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

        self.rules_label.configure(
            text=(
                f"Rules: "
                f"{len(self.custom_rules)}"
            )
        )

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
