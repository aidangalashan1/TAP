# schema/field_mapper.py

from schema.workbook_schema import (
    FieldDataType,
    FieldRole,
    FieldSchema,
    RangeSchema,
)


class FieldMapper:
    """
    Maps likely supplier input fields from detected regions.

    This does not map every populated column. It scores fields based on:
    - yellow fill
    - unlocked cells
    - absence of formula
    - numeric-like values
    - input-style headers
    - exclusion of totals, notes and estimated quantities
    """

    MINIMUM_INPUT_SCORE = 45

    def map_fields(self, workbook, workbook_schema):
        cell_lookup = self._build_cell_lookup(workbook)

        for worksheet_schema in workbook_schema.worksheets.values():
            worksheet = workbook.worksheets.get(worksheet_schema.sheet_name)

            if worksheet is None:
                continue

            for region in worksheet_schema.regions:
                self._map_region_fields(
                    worksheet=worksheet,
                    region=region,
                    cell_lookup=cell_lookup,
                )

        return workbook_schema

    def _map_region_fields(self, worksheet, region, cell_lookup):
        if region.header_range is None:
            return

        header_row = region.header_range.start_row

        header_cells = self._get_cells_in_range(
            worksheet=worksheet,
            start_row=header_row,
            end_row=header_row,
            start_col=region.header_range.start_column,
            end_col=region.header_range.end_column,
        )

        used_names = set()

        for header_cell in header_cells:
            if not self._is_valid_header(header_cell.value):
                continue

            header_text = str(header_cell.value).strip()

            if self._is_metadata_header(header_text):
                continue

            data_range = self._build_data_range(
                worksheet=worksheet,
                region=region,
                header_cell=header_cell,
            )

            cells = self._cells_for_range(
                worksheet=worksheet,
                range_schema=data_range,
            )

            input_score = self._score_input_field(
                header_text=header_text,
                cells=cells,
            )

            if input_score < self.MINIMUM_INPUT_SCORE:
                continue

            field_name = self._unique_field_name(
                base_name=header_text,
                used_names=used_names,
                cell_reference=header_cell.cell_reference,
            )

            role = self._infer_role(header_text)

            field_schema = FieldSchema(
                field_name=field_name,
                sheet_name=worksheet.worksheet_name,
                field_range=data_range,
                header_range=RangeSchema(
                    sheet_name=worksheet.worksheet_name,
                    start_cell=header_cell.cell_reference,
                    end_cell=header_cell.cell_reference,
                ),
                role=role,
                data_type=self._detect_data_type(cells),
                confidence=min(1.0, input_score / 100),
                input_confidence=min(1.0, input_score / 100),
                is_input_field=True,
                user_defined=False,
            )

            region.add_field(field_schema)

    # ==================================================
    # Input scoring
    # ==================================================

    def _score_input_field(self, header_text, cells):
        score = 0

        header_lower = header_text.lower()

        if self._header_suggests_input(header_lower):
            score += 25

        if self._header_suggests_metadata(header_lower):
            score -= 40

        if not cells:
            return score

        yellow_count = 0
        unlocked_count = 0
        formula_count = 0
        numeric_count = 0
        populated_count = 0
        merged_count = 0

        for cell in cells:
            if self._is_populated(cell.value):
                populated_count += 1

            if self._is_yellow_fill(cell.fill_colour):
                yellow_count += 1

            if not cell.is_locked:
                unlocked_count += 1

            if cell.has_formula:
                formula_count += 1

            if self._to_float_or_none(cell.value) is not None:
                numeric_count += 1

            if getattr(cell, "is_merged", False):
                merged_count += 1

        total = len(cells)

        yellow_ratio = yellow_count / total
        unlocked_ratio = unlocked_count / total
        formula_ratio = formula_count / total
        numeric_ratio = numeric_count / total
        populated_ratio = populated_count / total
        merged_ratio = merged_count / total

        score += yellow_ratio * 55
        score += unlocked_ratio * 25
        score += numeric_ratio * 15
        score += populated_ratio * 5

        score -= formula_ratio * 70
        score -= merged_ratio * 30

        return round(score, 2)

    def _header_suggests_input(self, header_lower):
        input_terms = [
            "rate",
            "price",
            "cost",
            "discount",
            "%",
            "mileage band",
            "closest depot",
            "value",
            "premium",
        ]

        for term in input_terms:
            if term in header_lower:
                return True

        return False

    def _header_suggests_metadata(self, header_lower):
        metadata_terms = [
            "estimated qty",
            "estimate qty",
            "qty",
            "quantity",
            "description",
            "example",
            "type of",
            "classified",
            "asset ref",
            "reference",
            "total",
            "subtotal",
            "sub total",
            "for evaluation",
        ]

        for term in metadata_terms:
            if term in header_lower:
                return True

        return False

    def _is_metadata_header(self, header_text):
        header_lower = header_text.lower().strip()

        blocked_exact = {
            "description",
            "inclusions",
            "instructions",
            "price notes",
            "notes",
            "total",
        }

        if header_lower in blocked_exact:
            return True

        return False

    # ==================================================
    # Range handling
    # ==================================================

    def _build_data_range(self, worksheet, region, header_cell):
        start_row = region.header_range.start_row + 1
        end_row = region.region_range.end_row

        column_letter = self._column_letter(header_cell.column_number)

        return RangeSchema(
            sheet_name=worksheet.worksheet_name,
            start_cell=f"{column_letter}{start_row}",
            end_cell=f"{column_letter}{end_row}",
        )

    def _cells_for_range(self, worksheet, range_schema):
        cells = []

        for cell in worksheet.cells:
            if range_schema.contains(cell.cell_reference):
                cells.append(cell)

        return cells

    def _get_cells_in_range(
        self,
        worksheet,
        start_row,
        end_row,
        start_col,
        end_col,
    ):
        cells = []

        for cell in worksheet.cells:
            if cell.row_number < start_row:
                continue

            if cell.row_number > end_row:
                continue

            if cell.column_number < start_col:
                continue

            if cell.column_number > end_col:
                continue

            cells.append(cell)

        return sorted(cells, key=lambda item: item.column_number)

    # ==================================================
    # Type / role helpers
    # ==================================================

    def _detect_data_type(self, cells):
        numeric_count = 0
        text_count = 0
        formula_count = 0

        for cell in cells:
            if cell.has_formula:
                formula_count += 1
                continue

            if self._to_float_or_none(cell.value) is not None:
                numeric_count += 1
                continue

            if self._is_populated(cell.value):
                text_count += 1

        if formula_count > numeric_count and formula_count > text_count:
            return FieldDataType.FORMULA

        if numeric_count >= text_count:
            return FieldDataType.NUMBER

        if text_count > 0:
            return FieldDataType.TEXT

        return FieldDataType.UNKNOWN

    def _infer_role(self, header_text):
        text = header_text.lower()

        if "discount" in text or "%" in text:
            return FieldRole.PRICE

        if "rate" in text:
            return FieldRole.PRICE

        if "price" in text or "cost" in text:
            return FieldRole.PRICE

        if "premium" in text:
            return FieldRole.PRICE

        if "mileage band" in text:
            return FieldRole.CATEGORY

        if "depot" in text:
            return FieldRole.DESCRIPTION

        return FieldRole.UNKNOWN

    # ==================================================
    # Basic helpers
    # ==================================================

    def _build_cell_lookup(self, workbook):
        lookup = {}

        for worksheet in workbook.worksheets.values():
            for cell in worksheet.cells:
                key = f"{worksheet.worksheet_name}!{cell.cell_reference}"
                lookup[key] = cell

        return lookup

    def _is_valid_header(self, value):
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

        return True

    def _is_populated(self, value):
        if value is None:
            return False

        if isinstance(value, str):
            return value.strip() != ""

        return True

    def _is_yellow_fill(self, fill_colour):
        if not fill_colour:
            return False

        colour = str(fill_colour).upper()

        yellow_codes = [
            "FFFFFF00",
            "FFFF00",
            "00FFFF00",
            "FFFFFF99",
            "FFFF99",
            "00FFFF99",
            "FFFFCC",
            "00FFFFCC",
            "FFFFFFCC",
        ]

        if colour in yellow_codes:
            return True

        if "FFFF00" in colour:
            return True

        if "FFFF99" in colour:
            return True

        if "FFFFCC" in colour:
            return True

        return False

    def _to_float_or_none(self, value):
        if value is None:
            return None

        if isinstance(value, bool):
            return None

        if isinstance(value, int) or isinstance(value, float):
            return float(value)

        text = str(value).strip()

        if text == "":
            return None

        cleaned = text.replace(",", "")
        cleaned = cleaned.replace("£", "")
        cleaned = cleaned.replace("%", "")

        try:
            return float(cleaned)
        except ValueError:
            return None

    def _unique_field_name(self, base_name, used_names, cell_reference):
        name = base_name.strip()

        if name not in used_names:
            used_names.add(name)
            return name

        candidate = f"{name} [{cell_reference}]"
        used_names.add(candidate)

        return candidate

    def _column_letter(self, column_number):
        result = ""

        while column_number > 0:
            column_number, remainder = divmod(column_number - 1, 26)
            result = chr(65 + remainder) + result

        return result