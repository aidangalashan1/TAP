# parsers/row_builder.py

from dataclasses import dataclass, field


@dataclass
class WorkbookRow:
    sheet_name: str
    row_number: int

    values: dict = field(default_factory=dict)
    cell_references: dict = field(default_factory=dict)


class RowBuilder:
    """
    Converts worksheet data into row-based records.

    Example output:

    WorkbookRow(
        sheet_name="Plant Rates",
        row_number=15,
        values={
            "Weekday Rate": 45.0,
            "Weekend Rate": 60.0
        },
        cell_references={
            "Weekday Rate": "H15",
            "Weekend Rate": "I15"
        }
    )
    """

    def build_rows(self, workbook):
        rows = []

        for worksheet in workbook.worksheets.values():
            worksheet_rows = self._build_sheet_rows(
                worksheet
            )

            rows.extend(worksheet_rows)

        return rows

    def _build_sheet_rows(self, worksheet):
        row_map = {}
        header_row_number = self._find_header_row(
            worksheet
        )

        if header_row_number is None:
            return []

        headers = self._extract_headers(
            worksheet,
            header_row_number
        )

        if not headers:
            return []

        max_row = 0

        for cell in worksheet.cells:
            if cell.row_number > max_row:
                max_row = cell.row_number

        for row_number in range(
            header_row_number + 1,
            max_row + 1
        ):
            workbook_row = WorkbookRow(
                sheet_name=worksheet.worksheet_name,
                row_number=row_number
            )

            row_map[row_number] = workbook_row

        for cell in worksheet.cells:

            if cell.row_number <= header_row_number:
                continue

            header = headers.get(
                cell.column_number
            )

            if header is None:
                continue

            workbook_row = row_map.get(
                cell.row_number
            )

            if workbook_row is None:
                continue

            workbook_row.values[header] = cell.value
            workbook_row.cell_references[header] = (
                cell.cell_reference
            )

        results = []

        for workbook_row in row_map.values():

            if self._contains_data(
                workbook_row
            ):
                results.append(workbook_row)

        return results

    def _find_header_row(self, worksheet):
        row_text_counts = {}

        for cell in worksheet.cells:

            if not isinstance(
                cell.value,
                str
            ):
                continue

            text = cell.value.strip()

            if text == "":
                continue

            row_number = cell.row_number

            current_count = row_text_counts.get(
                row_number,
                0
            )

            row_text_counts[row_number] = (
                current_count + 1
            )

        if not row_text_counts:
            return None

        header_row = max(
            row_text_counts,
            key=row_text_counts.get
        )

        return header_row

    def _extract_headers(
        self,
        worksheet,
        header_row_number
    ):
        headers = {}

        for cell in worksheet.cells:

            if cell.row_number != header_row_number:
                continue

            if not isinstance(
                cell.value,
                str
            ):
                continue

            header = cell.value.strip()

            if header == "":
                continue

            headers[cell.column_number] = header

        return headers

    def _contains_data(
        self,
        workbook_row
    ):
        for value in workbook_row.values.values():

            if value is None:
                continue

            if isinstance(value, str):

                if value.strip() == "":
                    continue

            return True

        return False