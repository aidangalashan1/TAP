# schema/input_area_detector.py

from collections import deque

from schema.workbook_schema import (
    InputArea,
    RangeSchema,
)


class InputAreaDetector:
    """
    Detects likely supplier input cells and groups them into
    contiguous InputAreas.

    The detector is intentionally biased toward finding
    supplier-completed cells rather than understanding
    workbook structure.
    """

    MINIMUM_INPUT_SCORE = 50

    MAX_ROW_GAP = 1
    MAX_COLUMN_GAP = 1

    def detect_input_areas(
        self,
        workbook,
        workbook_schema,
    ):
        """
        Populate workbook_schema worksheets with InputAreas.
        """

        for (
            worksheet_name,
            worksheet,
        ) in workbook.worksheets.items():

            worksheet_schema = (
                workbook_schema.get_worksheet(
                    worksheet_name
                )
            )

            if worksheet_schema is None:
                continue

            worksheet_schema.input_areas.clear()

            scored_cells = (
                self._score_cells(
                    worksheet
                )
            )

            candidate_cells = {
                cell.cell_reference: cell
                for cell, score in scored_cells
                if score >= self.MINIMUM_INPUT_SCORE
            }

            groups = self._group_cells(
                candidate_cells
            )

            score_lookup = {
                cell.cell_reference: score
                for cell, score in scored_cells
            }

            for (
                index,
                group,
            ) in enumerate(groups, start=1):

                if not group:
                    continue

                confidence = (
                    self._average_score(
                        group,
                        score_lookup,
                    )
                )

                area_range = self._build_range(
                    worksheet_name,
                    group,
                )

                input_area = InputArea(
                    area_name=(
                        f"{worksheet_name}!{area_range.address}"
                    ),
                    sheet_name=worksheet_name,
                    area_range=area_range,
                    confidence=round(
                        confidence / 100,
                        2,
                    ),
                    detected_by_ai=True,
                )

                worksheet_schema.add_input_area(
                    input_area
                )

        return workbook_schema

    # ==================================================
    # CELL SCORING
    # ==================================================

    def _score_cells(
        self,
        worksheet,
    ):
        results = []

        for cell in worksheet.cells:

            score = self._score_cell(
                cell
            )

            results.append(
                (
                    cell,
                    score,
                )
            )

        return results

    def _score_cell(
        self,
        cell,
    ):
        score = 0

        # ------------------------------------------------
        # Yellow cells
        # ------------------------------------------------

        if self._is_yellow(
            getattr(
                cell,
                "fill_colour",
                "",
            )
        ):
            score += 50

        # ------------------------------------------------
        # Editable cells
        # ------------------------------------------------

        if not getattr(
            cell,
            "is_locked",
            True,
        ):
            score += 25

        # ------------------------------------------------
        # Formula cells aren't supplier input
        # ------------------------------------------------

        if getattr(
            cell,
            "has_formula",
            False,
        ):
            score -= 100
        else:
            score += 10

        # ------------------------------------------------
        # Merged cells are usually titles
        # ------------------------------------------------

        if getattr(
            cell,
            "is_merged",
            False,
        ):
            score -= 40

        # ------------------------------------------------
        # Numeric values are often supplier inputs
        # ------------------------------------------------

        if self._looks_numeric(
            cell.value
        ):
            score += 10

        # ------------------------------------------------
        # Text inputs can still be valid
        # ------------------------------------------------

        elif self._is_populated(
            cell.value
        ):
            score += 5

        # ------------------------------------------------
        # Detect obvious template content
        # ------------------------------------------------

        if self._looks_like_template_text(
            cell.value
        ):
            score -= 50

        return max(0, score)

    # ==================================================
    # GROUPING
    # ==================================================

    def _group_cells(
        self,
        candidate_cells,
    ):
        remaining = set(
            candidate_cells.keys()
        )

        groups = []

        while remaining:

            start_reference = (
                remaining.pop()
            )

            start_cell = (
                candidate_cells[
                    start_reference
                ]
            )

            queue = deque(
                [start_cell]
            )

            group = [start_cell]

            while queue:

                current = queue.popleft()

                neighbours = (
                    self._find_neighbours(
                        current,
                        remaining,
                        candidate_cells,
                    )
                )

                for neighbour in neighbours:

                    remaining.remove(
                        neighbour.cell_reference
                    )

                    queue.append(
                        neighbour
                    )

                    group.append(
                        neighbour
                    )

            groups.append(group)

        return groups

    def _find_neighbours(
        self,
        current_cell,
        remaining,
        candidate_cells,
    ):
        neighbours = []

        for reference in list(remaining):

            candidate = (
                candidate_cells[
                    reference
                ]
            )

            row_gap = abs(
                current_cell.row_number
                - candidate.row_number
            )

            col_gap = abs(
                current_cell.column_number
                - candidate.column_number
            )

            if (
                row_gap <= self.MAX_ROW_GAP
                and col_gap <= self.MAX_COLUMN_GAP
            ):
                neighbours.append(
                    candidate
                )

        return neighbours

    # ==================================================
    # RANGE CREATION
    # ==================================================

    def _build_range(
        self,
        worksheet_name,
        cells,
    ):
        min_row = min(
            cell.row_number
            for cell in cells
        )

        max_row = max(
            cell.row_number
            for cell in cells
        )

        min_column = min(
            cell.column_number
            for cell in cells
        )

        max_column = max(
            cell.column_number
            for cell in cells
        )

        return RangeSchema(
            sheet_name=worksheet_name,
            start_cell=(
                f"{self._column_letter(min_column)}"
                f"{min_row}"
            ),
            end_cell=(
                f"{self._column_letter(max_column)}"
                f"{max_row}"
            ),
        )

    # ==================================================
    # SCORING HELPERS
    # ==================================================

    def _average_score(
        self,
        cells,
        score_lookup,
    ):
        scores = [
            score_lookup.get(
                cell.cell_reference,
                0,
            )
            for cell in cells
        ]

        if not scores:
            return 0

        return (
            sum(scores)
            / len(scores)
        )

    def _is_yellow(
        self,
        fill_colour,
    ):
        if not fill_colour:
            return False

        colour = str(
            fill_colour
        ).upper()

        yellow_markers = [
            "FFFF00",
            "FFFF99",
            "FFFFCC",
            "FFF2CC",
            "FFEB9C",
        ]

        return any(
            marker in colour
            for marker in yellow_markers
        )

    def _is_populated(
        self,
        value,
    ):
        if value is None:
            return False

        if isinstance(
            value,
            str,
        ):
            return (
                value.strip()
                != ""
            )

        return True

    def _looks_numeric(
        self,
        value,
    ):
        if value is None:
            return False

        if isinstance(
            value,
            (int, float),
        ):
            return True

        try:

            text = (
                str(value)
                .replace(",", "")
                .replace("£", "")
                .replace("%", "")
                .strip()
            )

            float(text)

            return True

        except Exception:
            return False

    def _looks_like_template_text(
        self,
        value,
    ):
        if value is None:
            return False

        if not isinstance(
            value,
            str,
        ):
            return False

        text = value.lower()

        blocked_terms = [
            "instruction",
            "instructions",
            "note",
            "notes",
            "guidance",
            "example",
            "description",
            "asset ref",
            "estimated qty",
            "quantity",
            "for evaluation",
            "subtotal",
            "sub total",
            "total",
            "template",
        ]

        return any(
            term in text
            for term in blocked_terms
        )

    # ==================================================
    # COLUMN HELPERS
    # ==================================================

    def _column_letter(
        self,
        column_number,
    ):
        result = ""

        while column_number > 0:

            (
                column_number,
                remainder,
            ) = divmod(
                column_number - 1,
                26,
            )

            result = (
                chr(65 + remainder)
                + result
            )

        return result
