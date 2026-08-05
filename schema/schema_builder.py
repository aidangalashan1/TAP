# schema/schema_builder.py

from schema.input_area_detector import InputAreaDetector
from schema.workbook_schema import (
    DataRecord,
    WorkbookSchema,
    WorksheetSchema,
)


class SchemaBuilder:
    """
    Builds workbook schemas focused on supplier
    response areas rather than workbook structure.

    The output is used by:

        Workbook Mapper
        Analysis Engine
        Rule Engine

    Everything downstream should work from
    InputAreas rather than Regions.
    """

    def __init__(self):
        self.input_area_detector = (
            InputAreaDetector()
        )

    # ==================================================
    # MAIN ENTRY POINT
    # ==================================================

    def build_schema(
        self,
        workbook,
    ):
        """
        Build a workbook schema and detect
        supplier input areas.
        """

        workbook_schema = (
            WorkbookSchema(
                workbook_name=workbook.file_name,
                workbook_path=workbook.file_path,
            )
        )

        for worksheet_name in (
            workbook.worksheets.keys()
        ):
            worksheet_schema = (
                WorksheetSchema(
                    sheet_name=worksheet_name
                )
            )

            workbook_schema.add_worksheet(
                worksheet_schema
            )

        workbook_schema = (
            self.input_area_detector.detect_input_areas(
                workbook=workbook,
                workbook_schema=workbook_schema,
            )
        )

        return workbook_schema

    # ==================================================
    # DATA RECORD EXTRACTION
    # ==================================================

    def build_records(
        self,
        workbook,
        workbook_schema,
    ):
        """
        Build one DataRecord per row spanned by the
        analysis input areas on each worksheet, with
        one field per input area (or one field per
        column, for areas wider than a single column).
        """

        records = []

        areas_by_sheet = {}

        for input_area in self.get_analysis_areas(
            workbook_schema
        ):
            areas_by_sheet.setdefault(
                input_area.sheet_name, []
            ).append(input_area)

        for sheet_name, input_areas in areas_by_sheet.items():

            worksheet = workbook.get_worksheet(
                sheet_name
            )

            if worksheet is None:
                continue

            min_row = min(
                input_area.area_range.min_row
                for input_area in input_areas
            )

            max_row = max(
                input_area.area_range.max_row
                for input_area in input_areas
            )

            for row in range(min_row, max_row + 1):

                record = DataRecord(
                    sheet_name=sheet_name,
                    region_name=sheet_name,
                    record_reference=f"Row {row}",
                )

                has_value = False

                for input_area in input_areas:

                    area_range = input_area.area_range

                    if row < area_range.min_row or row > area_range.max_row:
                        continue

                    multi_column = (
                        area_range.max_column > area_range.min_column
                    )

                    for column in range(
                        area_range.min_column,
                        area_range.max_column + 1,
                    ):
                        column_text = area_range._number_to_column(
                            column
                        )

                        cell_reference = f"{column_text}{row}"

                        cell = worksheet.get_cell(
                            cell_reference
                        )

                        if cell is None:
                            continue

                        field_name = (
                            input_area.area_name
                            if not multi_column
                            else f"{input_area.area_name} ({column_text})"
                        )

                        record.set_value(
                            field_name,
                            cell.value,
                            cell_reference,
                        )

                        if cell.value is not None and cell.value != "":
                            has_value = True

                if has_value:
                    records.append(record)

        return records

    def build_schema_and_records(
        self,
        workbook,
    ):
        workbook_schema = self.build_schema(
            workbook
        )

        records = self.build_records(
            workbook,
            workbook_schema,
        )

        return workbook_schema, records

    # ==================================================
    # REFRESH EXISTING SCHEMA
    # ==================================================

    def refresh_input_areas(
        self,
        workbook,
        workbook_schema,
    ):
        """
        Re-run input area detection while
        preserving the workbook structure.
        """

        return (
            self.input_area_detector.detect_input_areas(
                workbook=workbook,
                workbook_schema=workbook_schema,
            )
        )

    # ==================================================
    # ANALYSIS HELPERS
    # ==================================================

    def get_analysis_areas(
        self,
        workbook_schema,
    ):
        """
        Prefer confirmed areas.

        Fall back to detected areas if
        nothing has been confirmed yet.
        """

        confirmed = (
            workbook_schema.get_confirmed_input_areas()
        )

        if confirmed:
            return confirmed

        return workbook_schema.get_input_areas()

    def get_analysis_ranges(
        self,
        workbook_schema,
    ):
        """
        Return simple range list.

        Example:

            Sheet1!H12:H95
            Sheet1!K12:K95
        """

        ranges = []

        for input_area in (
            self.get_analysis_areas(
                workbook_schema
            )
        ):
            ranges.append(
                (
                    input_area.sheet_name,
                    input_area.address,
                )
            )

        return ranges

    # ==================================================
    # SUMMARY
    # ==================================================

    def get_detection_summary(
        self,
        workbook_schema,
    ):
        summary = {
            "worksheets": 0,
            "input_areas": 0,
            "confirmed_input_areas": 0,
        }

        summary["worksheets"] = len(
            workbook_schema.worksheets
        )

        summary["input_areas"] = len(
            workbook_schema.get_input_areas()
        )

        summary["confirmed_input_areas"] = len(
            workbook_schema.get_confirmed_input_areas()
        )

        return summary