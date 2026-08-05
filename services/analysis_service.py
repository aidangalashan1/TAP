# services/analysis_service.py

from dataclasses import dataclass
from pathlib import Path

from reporting.report_writer import ReportWriter
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

    # --------------------------------------------------
    # Single Workbook Analysis
    # --------------------------------------------------

    def analyse_workbook(
        self,
        supplier_name,
        workbook,
        custom_rules=None,
        output_folder=None,
    ):
        workbook_schema, records = (
            self.schema_service.build_schema_and_records(
                workbook
            )
        )

        findings = (
            self.custom_rules_service.execute_rules_against_records(
                records=records,
                rules=custom_rules,
            )
        )

        supplier_result = self._build_supplier_result(
            supplier_name=supplier_name,
            findings=findings,
        )

        report_path = ""

        if output_folder is not None:

            report_path = self._write_report(
                supplier_result=supplier_result,
                output_folder=output_folder,
            )

        return AnalysisResult(
            supplier_name=supplier_name,
            workbook_schema=workbook_schema,
            records=records,
            findings=findings,
            report_path=report_path,
        )

    # --------------------------------------------------
    # Batch Analysis
    # --------------------------------------------------

    def analyse_workbooks(
        self,
        workbooks,
        custom_rules=None,
        output_folder=None,
    ):
        results = []

        for supplier_name, workbook in workbooks:

            result = self.analyse_workbook(
                supplier_name=supplier_name,
                workbook=workbook,
                custom_rules=custom_rules,
                output_folder=output_folder,
            )

            results.append(result)

        return results

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

    def build_schema_and_records(
        self,
        workbook
    ):
        return (
            self.schema_service.build_schema_and_records(
                workbook
            )
        )

    def get_available_fields(
        self,
        workbook
    ):
        workbook_schema = (
            self.schema_service.build_schema(
                workbook
            )
        )

        return (
            workbook_schema.get_unique_field_names()
        )

    def get_available_regions(
        self,
        workbook
    ):
        workbook_schema = (
            self.schema_service.build_schema(
                workbook
            )
        )

        return (
            workbook_schema.get_all_regions()
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

    def _build_supplier_result(
        self,
        supplier_name,
        findings,
    ):
        class SupplierResult:
            pass

        result = SupplierResult()

        result.supplier_name = supplier_name
        result.findings = findings

        return result

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