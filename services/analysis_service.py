# services/analysis_service.py

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from models.pricing_models import Finding
from models.pricing_models import FindingCategory
from models.pricing_models import Severity
from models.pricing_models import SupplierAnalysisResult
from reporting.report_writer import ReportWriter
from rules.cross_supplier_comparator import CrossSupplierComparator
from rules.custom_rule_models import CustomRuleType
from services.custom_rules_service import CustomRulesService
from services.schema_service import SchemaService


@dataclass
class AnalysisResult:
    supplier_name: str
    workbook_schema: object
    records: list
    findings: list
    report_path: str


class AnalysisService:

    def __init__(
        self,
        custom_rules_service=None,
        schema_service=None,
        report_writer=None,
        cross_supplier_comparator=None,
    ):
        self.custom_rules_service = (
            custom_rules_service
            or CustomRulesService()
        )

        self.schema_service = (
            schema_service
            or SchemaService()
        )

        self.report_writer = (
            report_writer
            or ReportWriter()
        )

        self.cross_supplier_comparator = (
            cross_supplier_comparator
            or CrossSupplierComparator()
        )

    # --------------------------------------------------
    # Multi-Supplier Analysis
    # --------------------------------------------------

    def analyse_suppliers(
        self,
        workbook_schema,
        supplier_workbooks,
        benchmark_workbook=None,
        custom_rules=None,
        output_folder=None,
    ):
        """
        workbook_schema: the confirmed WorkbookSchema built from the
            template, shared by every supplier so the same field/row
            identifies the same thing in every workbook.
        supplier_workbooks: list of (supplier_name, WorkbookInfo).
        benchmark_workbook: optional WorkbookInfo compared against
            each supplier's values. When omitted, suppliers are
            compared statistically against each other instead.
        """

        missing_sheets_by_supplier = {
            supplier_name: self.schema_service.get_missing_sheets(
                workbook,
                workbook_schema,
            )
            for supplier_name, workbook in supplier_workbooks
        }

        supplier_records = {
            supplier_name: self.schema_service.build_records(
                workbook,
                workbook_schema,
            )
            for supplier_name, workbook in supplier_workbooks
        }

        comparison_findings_by_supplier = (
            self._run_cross_supplier_comparison(
                supplier_records=supplier_records,
                benchmark_workbook=benchmark_workbook,
                workbook_schema=workbook_schema,
                custom_rules=custom_rules,
            )
        )

        results = []

        for supplier_name, workbook in supplier_workbooks:

            records = supplier_records[supplier_name]

            quick_findings = (
                self.custom_rules_service.execute_rules_against_records(
                    records=records,
                    rules=custom_rules,
                )
            )

            for finding in quick_findings:
                finding.supplier_name = supplier_name

            findings = (
                self._build_missing_sheet_findings(
                    supplier_name,
                    missing_sheets_by_supplier[supplier_name],
                )
                + quick_findings
                + comparison_findings_by_supplier.get(supplier_name, [])
            )

            self._flag_expected_discrepancies(findings, workbook_schema)

            supplier_result = SupplierAnalysisResult(
                supplier_name=supplier_name,
                findings=findings,
            )

            report_path = ""

            if output_folder is not None:

                report_path = self._write_report(
                    supplier_result=supplier_result,
                    output_folder=output_folder,
                )

            results.append(
                AnalysisResult(
                    supplier_name=supplier_name,
                    workbook_schema=workbook_schema,
                    records=records,
                    findings=findings,
                    report_path=report_path,
                )
            )

        return results

    def _build_missing_sheet_findings(self, supplier_name, missing_sheets):
        if not missing_sheets:
            return []

        sheet_list = ", ".join(missing_sheets)

        return [
            Finding(
                supplier_name=supplier_name,
                severity=Severity.HIGH,
                worksheet_name=sheet_list,
                cell_reference="",
                item_description="Missing worksheet(s)",
                actual_value="",
                category=FindingCategory.MISSING_WORKSHEET.value,
                reason=(
                    f"This workbook is missing worksheet(s) the template "
                    f"expects: {sheet_list}. Fields on those sheets could "
                    f"not be read."
                ),
                suggested_clarification=(
                    f"Please confirm this is the correct workbook for "
                    f"{supplier_name}, and that it includes the "
                    f"worksheet(s): {sheet_list}."
                ),
            )
        ]

    def _flag_expected_discrepancies(self, findings, workbook_schema):
        for finding in findings:
            worksheet_schema = workbook_schema.get_worksheet(
                finding.worksheet_name
            )

            if worksheet_schema is not None and worksheet_schema.expect_discrepancies:
                finding.expected_discrepancy = True

    def get_missing_sheets(self, workbook, workbook_schema):
        return self.schema_service.get_missing_sheets(
            workbook,
            workbook_schema,
        )

    def _run_cross_supplier_comparison(
        self,
        supplier_records,
        benchmark_workbook,
        workbook_schema,
        custom_rules=None,
    ):
        benchmark_records = None

        if benchmark_workbook is not None:
            benchmark_records = self.schema_service.build_records(
                benchmark_workbook,
                workbook_schema,
            )

        comparison_rules = [
            rule
            for rule in (custom_rules or [])
            if rule.enabled
            and rule.rule_type == CustomRuleType.COMPARISON_RULE
        ]

        comparison_findings = (
            self.cross_supplier_comparator.compare_using_rules(
                supplier_records=supplier_records,
                benchmark_records=benchmark_records,
                comparison_rules=comparison_rules,
                use_benchmark_default=benchmark_workbook is not None,
            )
        )

        findings_by_supplier = defaultdict(list)

        for finding in comparison_findings:
            findings_by_supplier[finding.supplier_name].append(finding)

        return findings_by_supplier

    # --------------------------------------------------
    # Schema Helpers
    # --------------------------------------------------

    def build_schema(
        self,
        workbook
    ):
        return self.schema_service.build_schema(
            workbook
        )

    def get_available_sheets(
        self,
        workbook
    ):
        workbook_schema = (
            self.schema_service.build_schema(
                workbook
            )
        )

        return sorted(
            workbook_schema.worksheets.keys()
        )

    # --------------------------------------------------
    # Reporting
    # --------------------------------------------------

    def _write_report(
        self,
        supplier_result,
        output_folder,
    ):
        output_folder = Path(output_folder)

        output_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        safe_name = self._safe_filename(
            supplier_result.supplier_name
        )

        report_path = (
            output_folder
            / f"{safe_name}_analysis.xlsx"
        )

        self.report_writer.write_report(
            supplier_result=supplier_result,
            output_file_path=str(report_path),
        )

        return str(report_path)

    def _safe_filename(
        self,
        value
    ):
        invalid_characters = (
            "\\/:*?<>|"
        )

        output = str(value)

        for character in invalid_characters:
            output = output.replace(
                character,
                "_"
            )

        output = output.strip()

        if output == "":
            return "supplier"

        return output
