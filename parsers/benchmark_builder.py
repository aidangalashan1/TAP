# parsers/benchmark_builder.py

from models.workbook_models import WorkbookInfo


class BenchmarkBuilder:

    def validate_template_match(self, template_workbook, benchmark_workbook):
        template_sheet_names = set(template_workbook.worksheets.keys())
        benchmark_sheet_names = set(benchmark_workbook.worksheets.keys())

        if template_sheet_names != benchmark_sheet_names:
            missing_from_benchmark = template_sheet_names - benchmark_sheet_names
            extra_in_benchmark = benchmark_sheet_names - template_sheet_names

            message_parts = []

            if missing_from_benchmark:
                message_parts.append(
                    "Missing sheets in benchmark: "
                    + ", ".join(sorted(missing_from_benchmark))
                )

            if extra_in_benchmark:
                message_parts.append(
                    "Extra sheets in benchmark: "
                    + ", ".join(sorted(extra_in_benchmark))
                )

            return False, " ".join(message_parts)

        for sheet_name in template_sheet_names:
            template_sheet = template_workbook.worksheets[sheet_name]
            benchmark_sheet = benchmark_workbook.worksheets[sheet_name]

            template_mandatory_cells = self._get_mandatory_cell_references(
                template_sheet
            )

            benchmark_mandatory_cells = self._get_mandatory_cell_references(
                benchmark_sheet
            )

            if template_mandatory_cells != benchmark_mandatory_cells:
                return (
                    False,
                    f"Mandatory input cell structure differs on sheet '{sheet_name}'."
                )

        return True, "Benchmark structure matches template."

    def build_lookup(self, benchmark_workbook):
        benchmark_lookup = {}

        for worksheet in benchmark_workbook.worksheets.values():
            for cell in worksheet.cells:
                numeric_value = self._to_float_or_none(cell.value)

                if numeric_value is None:
                    continue

                lookup_key = self._make_lookup_key(
                    worksheet.worksheet_name,
                    cell.cell_reference
                )

                benchmark_lookup[lookup_key] = numeric_value

        return benchmark_lookup

    def _get_mandatory_cell_references(self, worksheet):
        mandatory_cells = set()

        for cell in worksheet.cells:
            if cell.is_mandatory:
                mandatory_cells.add(cell.cell_reference)

        return mandatory_cells

    def _make_lookup_key(self, worksheet_name, cell_reference):
        return f"{worksheet_name}!{cell_reference}"

    def _to_float_or_none(self, value):
        if value is None:
            return None

        if isinstance(value, bool):
            return None

        if isinstance(value, int):
            return float(value)

        if isinstance(value, float):
            return float(value)

        if isinstance(value, str):
            cleaned_value = value.strip()

            if cleaned_value == "":
                return None

            try:
                return float(cleaned_value.replace(",", ""))
            except ValueError:
                return None

        return None