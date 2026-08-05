# parsers/header_detector.py

from collections import defaultdict


class HeaderDetector:
    """
    Detects potential column headers from a parsed workbook.

    The output is used by the GUI rule builder so users can
    select fields such as:

        Weekday Rate
        Weekend Rate
        Hire Rate
        Benchmark Rate

    when creating custom validation rules.
    """

    def extract_headers(self, workbook):
        """
        Returns:

        {
            "Sheet Name": [
                "Header 1",
                "Header 2"
            ]
        }
        """

        results = {}

        for worksheet in workbook.worksheets.values():

            headers = self._extract_sheet_headers(
                worksheet
            )

            results[
                worksheet.worksheet_name
            ] = headers

        return results

    def extract_unique_headers(self, workbook):
        """
        Returns a sorted list of all unique headers
        across all worksheets.
        """

        unique_headers = set()

        sheet_headers = self.extract_headers(
            workbook
        )

        for headers in sheet_headers.values():
            unique_headers.update(headers)

        return sorted(unique_headers)

    def _extract_sheet_headers(
        self,
        worksheet
    ):
        row_map = defaultdict(list)

        for cell in worksheet.cells:

            if not isinstance(
                cell.value,
                str
            ):
                continue

            text = cell.value.strip()

            if not text:
                continue

            row_map[
                cell.row_number
            ].append(text)

        best_row = None
        highest_count = 0

        for row_number, values in row_map.items():

            count = len(values)

            if count > highest_count:
                highest_count = count
                best_row = row_number

        if best_row is None:
            return []

        headers = []

        for cell in worksheet.cells:

            if cell.row_number != best_row:
                continue

            if not isinstance(
                cell.value,
                str
            ):
                continue

            text = cell.value.strip()

            if not text:
                continue

            headers.append(text)

        return headers