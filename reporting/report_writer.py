# reporting/report_writer.py

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.styles import PatternFill


class ReportWriter:

    def write_report(
        self,
        supplier_result,
        output_file_path
    ):
        workbook = Workbook()

        summary_sheet = workbook.active
        summary_sheet.title = "Summary"

        findings_sheet = workbook.create_sheet(
            "Findings"
        )

        self._write_summary_sheet(
            summary_sheet,
            supplier_result
        )

        self._write_findings_sheet(
            findings_sheet,
            supplier_result
        )

        output_path = Path(output_file_path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        workbook.save(
            output_file_path
        )

    def _write_summary_sheet(
        self,
        worksheet,
        supplier_result
    ):
        worksheet["A1"] = "Supplier"
        worksheet["B1"] = supplier_result.supplier_name

        worksheet["A3"] = "Total Findings"
        worksheet["B3"] = len(
            supplier_result.findings
        )

        severity_counts = {
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "INFO": 0,
        }

        for finding in supplier_result.findings:
            severity_name = self._severity_name(
                finding.severity
            )

            severity_counts.setdefault(
                severity_name,
                0
            )

            severity_counts[
                severity_name
            ] += 1

        worksheet["A5"] = "Severity"
        worksheet["B5"] = "Count"

        row = 6

        for severity_name, count in severity_counts.items():

            worksheet.cell(
                row=row,
                column=1
            ).value = severity_name

            worksheet.cell(
                row=row,
                column=2
            ).value = count

            row += 1

        self._bold_row(
            worksheet,
            1
        )

        self._bold_row(
            worksheet,
            5
        )

        worksheet.column_dimensions["A"].width = 25
        worksheet.column_dimensions["B"].width = 20

    def _write_findings_sheet(
        self,
        worksheet,
        supplier_result
    ):
        headers = [
            "Severity",
            "Worksheet",
            "Cell",
            "Region",
            "Actual Value",
            "Reason",
            "Suggested Clarification",
        ]

        for column_index, header in enumerate(
            headers,
            start=1
        ):
            cell = worksheet.cell(
                row=1,
                column=column_index
            )

            cell.value = header
            cell.font = Font(
                bold=True
            )

        row_number = 2

        for finding in supplier_result.findings:

            worksheet.cell(
                row=row_number,
                column=1
            ).value = self._severity_name(
                finding.severity
            )

            worksheet.cell(
                row=row_number,
                column=2
            ).value = getattr(
                finding,
                "worksheet_name",
                ""
            )

            worksheet.cell(
                row=row_number,
                column=3
            ).value = getattr(
                finding,
                "cell_reference",
                ""
            )

            # item_description now stores region/context
            worksheet.cell(
                row=row_number,
                column=4
            ).value = getattr(
                finding,
                "item_description",
                ""
            )

            worksheet.cell(
                row=row_number,
                column=5
            ).value = getattr(
                finding,
                "actual_value",
                ""
            )

            worksheet.cell(
                row=row_number,
                column=6
            ).value = getattr(
                finding,
                "reason",
                ""
            )

            worksheet.cell(
                row=row_number,
                column=7
            ).value = getattr(
                finding,
                "suggested_clarification",
                ""
            )

            self._apply_severity_format(
                worksheet.cell(
                    row=row_number,
                    column=1
                )
            )

            row_number += 1

        widths = {
            "A": 15,
            "B": 25,
            "C": 15,
            "D": 35,
            "E": 20,
            "F": 60,
            "G": 60,
        }

        for column, width in widths.items():
            worksheet.column_dimensions[
                column
            ].width = width

    def _severity_name(
        self,
        severity
    ):
        if hasattr(
            severity,
            "name"
        ):
            return severity.name.upper()

        return str(severity).upper()

    def _apply_severity_format(
        self,
        cell
    ):
        value = str(
            cell.value
        ).upper()

        if value == "HIGH":
            cell.fill = PatternFill(
                fill_type="solid",
                fgColor="FF9999"
            )

        elif value == "MEDIUM":
            cell.fill = PatternFill(
                fill_type="solid",
                fgColor="FFD699"
            )

        elif value == "LOW":
            cell.fill = PatternFill(
                fill_type="solid",
                fgColor="FFF2CC"
            )

        elif value == "INFO":
            cell.fill = PatternFill(
                fill_type="solid",
                fgColor="D9EAD3"
            )

    def _bold_row(
        self,
        worksheet,
        row_number
    ):
        for cell in worksheet[row_number]:
            cell.font = Font(
                bold=True
            )