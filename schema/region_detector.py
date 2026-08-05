# schema/region_detector.py

import re
from collections import defaultdict

from schema.workbook_schema import (
    RangeSchema,
    RegionOrientation,
    RegionSchema,
    WorkbookSchema,
    WorksheetSchema,
)


class RegionDetector:
    """
    Detects logical data regions within a parsed workbook.

    This detector supports tender-style worksheets where:
    - tables do not start at A1
    - sheets contain instructions, notes and headings
    - multiple tables exist on one sheet
    - tables are introduced by markers such as "Table 1:"
    - regions may be separated by blank rows

    It does not hardcode any business column names.
    """

    TABLE_MARKER_PATTERN = re.compile(
        r"^\s*table\s+\d+",
        re.IGNORECASE,
    )

    def build_schema(self, workbook):
        workbook_schema = WorkbookSchema(
            workbook_name=getattr(workbook, "file_name", "Workbook"),
            workbook_path=getattr(workbook, "file_path", ""),
        )

        for worksheet in workbook.worksheets.values():
            worksheet_schema = self._analyse_worksheet(worksheet)
            workbook_schema.add_worksheet(worksheet_schema)

        return workbook_schema

    def _analyse_worksheet(self, worksheet):
        worksheet_schema = WorksheetSchema(
            sheet_name=worksheet.worksheet_name,
        )

        regions = self._detect_regions(worksheet)

        for region in regions:
            worksheet_schema.add_region(region)

        return worksheet_schema

    def _detect_regions(self, worksheet):
        row_map = self._build_populated_row_map(worksheet)

        if not row_map:
            return []

        table_marker_rows = self._find_table_marker_rows(row_map)

        if table_marker_rows:
            return self._detect_regions_from_table_markers(
                worksheet=worksheet,
                row_map=row_map,
                table_marker_rows=table_marker_rows,
            )

        return self._detect_regions_from_blank_row_groups(
            worksheet=worksheet,
            row_map=row_map,
        )

    # ==================================================
    # Table-marker based detection
    # ==================================================

    def _detect_regions_from_table_markers(
        self,
        worksheet,
        row_map,
        table_marker_rows,
    ):
        regions = []

        populated_rows = sorted(row_map.keys())
        max_populated_row = max(populated_rows)

        for index, marker_row in enumerate(table_marker_rows):
            if index + 1 < len(table_marker_rows):
                next_marker_row = table_marker_rows[index + 1]
                end_row = next_marker_row - 1
            else:
                end_row = max_populated_row

            candidate_rows = [
                row_number
                for row_number in populated_rows
                if marker_row <= row_number <= end_row
            ]

            region = self._build_region_from_rows(
                worksheet=worksheet,
                row_map=row_map,
                rows=candidate_rows,
                region_index=index + 1,
            )

            if region is not None:
                regions.append(region)

        return regions

    # ==================================================
    # Blank-row based fallback detection
    # ==================================================

    def _detect_regions_from_blank_row_groups(
        self,
        worksheet,
        row_map,
    ):
        regions = []

        populated_rows = sorted(row_map.keys())
        current_group = []

        for row_number in populated_rows:
            if not current_group:
                current_group.append(row_number)
                continue

            previous_row = current_group[-1]

            if row_number - previous_row <= 1:
                current_group.append(row_number)
            else:
                region = self._build_region_from_rows(
                    worksheet=worksheet,
                    row_map=row_map,
                    rows=current_group,
                    region_index=len(regions) + 1,
                )

                if region is not None:
                    regions.append(region)

                current_group = [row_number]

        if current_group:
            region = self._build_region_from_rows(
                worksheet=worksheet,
                row_map=row_map,
                rows=current_group,
                region_index=len(regions) + 1,
            )

            if region is not None:
                regions.append(region)

        return regions

    # ==================================================
    # Region building
    # ==================================================

    def _build_region_from_rows(
        self,
        worksheet,
        row_map,
        rows,
        region_index,
    ):
        if not rows:
            return None

        cells = []

        for row_number in rows:
            cells.extend(row_map.get(row_number, []))

        if not cells:
            return None

        min_row = min(cell.row_number for cell in cells)
        max_row = max(cell.row_number for cell in cells)
        min_col = min(cell.column_number for cell in cells)
        max_col = max(cell.column_number for cell in cells)

        header_row = self._detect_header_row(
            row_map=row_map,
            rows=rows,
        )

        if header_row is None:
            return None

        header_cells = row_map.get(header_row, [])

        if not self._looks_like_table_header(header_cells):
            return None

        header_min_col = min(
            cell.column_number
            for cell in header_cells
            if self._is_header_candidate(cell.value)
        )

        header_max_col = max(
            cell.column_number
            for cell in header_cells
            if self._is_header_candidate(cell.value)
        )

        region_range = RangeSchema(
            sheet_name=worksheet.worksheet_name,
            start_cell=self._cell_reference(min_row, min_col),
            end_cell=self._cell_reference(max_row, max_col),
        )

        header_range = RangeSchema(
            sheet_name=worksheet.worksheet_name,
            start_cell=self._cell_reference(header_row, header_min_col),
            end_cell=self._cell_reference(header_row, header_max_col),
        )

        region_name = self._detect_region_name(
            row_map=row_map,
            rows=rows,
            fallback=f"Region_{region_index}",
        )

        confidence = self._calculate_confidence(
            header_cells=header_cells,
            row_count=len(rows),
        )

        return RegionSchema(
            region_name=region_name,
            sheet_name=worksheet.worksheet_name,
            region_range=region_range,
            header_range=header_range,
            orientation=RegionOrientation.TABLE,
            confidence=confidence,
        )

    def _detect_header_row(
        self,
        row_map,
        rows,
    ):
        best_row = None
        best_score = 0

        for row_number in rows:
            cells = row_map.get(row_number, [])

            score = self._score_header_row(cells)

            if score > best_score:
                best_score = score
                best_row = row_number

        if best_score < 2:
            return None

        return best_row

    def _score_header_row(self, cells):
        score = 0

        for cell in cells:
            if self._is_header_candidate(cell.value):
                score += 1

        return score

    def _looks_like_table_header(self, cells):
        header_candidate_count = 0

        for cell in cells:
            if self._is_header_candidate(cell.value):
                header_candidate_count += 1

        return header_candidate_count >= 2

    def _detect_region_name(
        self,
        row_map,
        rows,
        fallback,
    ):
        for row_number in rows:
            cells = row_map.get(row_number, [])

            for cell in cells:
                value = cell.value

                if not isinstance(value, str):
                    continue

                text = value.strip()

                if self.TABLE_MARKER_PATTERN.match(text):
                    return text

        return fallback

    def _calculate_confidence(
        self,
        header_cells,
        row_count,
    ):
        header_count = 0

        for cell in header_cells:
            if self._is_header_candidate(cell.value):
                header_count += 1

        confidence = 0.5

        if header_count >= 5:
            confidence = 0.95
        elif header_count >= 3:
            confidence = 0.85
        elif header_count >= 2:
            confidence = 0.70

        if row_count < 3:
            confidence -= 0.20

        if confidence < 0:
            confidence = 0.0

        return round(confidence, 2)

    # ==================================================
    # Row / cell helpers
    # ==================================================

    def _build_populated_row_map(self, worksheet):
        row_map = defaultdict(list)

        for cell in worksheet.cells:
            if not self._is_populated(cell.value):
                continue

            row_map[cell.row_number].append(cell)

        return row_map

    def _find_table_marker_rows(self, row_map):
        marker_rows = []

        for row_number, cells in row_map.items():
            for cell in cells:
                value = cell.value

                if not isinstance(value, str):
                    continue

                if self.TABLE_MARKER_PATTERN.match(value.strip()):
                    marker_rows.append(row_number)
                    break

        return sorted(marker_rows)

    def _is_populated(self, value):
        if value is None:
            return False

        if isinstance(value, str):
            return value.strip() != ""

        return True

    def _is_header_candidate(self, value):
        if value is None:
            return False

        if not isinstance(value, str):
            return False

        text = value.strip()

        if text == "":
            return False

        ignored_values = {
            "-",
            "£",
            "%",
            "0",
            "n/a",
            "na",
            "none",
        }

        if text.lower() in ignored_values:
            return False

        if self.TABLE_MARKER_PATTERN.match(text):
            return False

        return True

    def _cell_reference(self, row_number, column_number):
        return f"{self._column_letter(column_number)}{row_number}"

    def _column_letter(self, column_number):
        result = ""

        while column_number > 0:
            column_number, remainder = divmod(column_number - 1, 26)
            result = chr(65 + remainder) + result

        return result