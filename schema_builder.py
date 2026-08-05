# services/schema_builder.py

from schema.input_area_detector import InputAreaDetector
from schema.workbook_schema import (
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