# services/schema_service.py

from schema.schema_builder import SchemaBuilder


class SchemaService:
    """
    Central schema orchestration service.

    Responsibilities:
        - Build workbook schemas
        - Build DataRecord collections
        - Retrieve input areas and sheets
        - Provide schema summaries for UI/reporting

    GUI code and analysis code should interact with
    this service rather than calling SchemaBuilder directly.
    """

    def __init__(self):
        self.schema_builder = SchemaBuilder()

    # --------------------------------------------------
    # Build Operations
    # --------------------------------------------------

    def build_schema(self, workbook):
        return self.schema_builder.build_schema(
            workbook
        )

    def build_records(
        self,
        workbook,
        workbook_schema,
    ):
        return self.schema_builder.build_records(
            workbook,
            workbook_schema,
        )

    def build_schema_and_records(
        self,
        workbook,
    ):
        return (
            self.schema_builder.build_schema_and_records(
                workbook
            )
        )

    def get_missing_sheets(
        self,
        workbook,
        workbook_schema,
    ):
        return self.schema_builder.get_missing_sheets(
            workbook,
            workbook_schema,
        )

    # --------------------------------------------------
    # Input Area Operations
    # --------------------------------------------------

    def get_input_areas(
        self,
        workbook_schema,
    ):
        return workbook_schema.get_input_areas()

    def get_field_names(
        self,
        workbook_schema,
    ):
        names = set()

        for input_area in workbook_schema.get_input_areas():
            names.add(input_area.area_name)

        return sorted(names)

    def find_input_area(
        self,
        workbook_schema,
        area_name,
    ):
        target = area_name.strip().lower()

        for input_area in workbook_schema.get_input_areas():

            if input_area.area_name.strip().lower() == target:
                return input_area

        return None

    # --------------------------------------------------
    # Worksheet Operations
    # --------------------------------------------------

    def get_sheet_names(
        self,
        workbook_schema,
    ):
        return sorted(
            workbook_schema.worksheets.keys()
        )

    # --------------------------------------------------
    # Summary Operations
    # --------------------------------------------------

    def get_schema_summary(
        self,
        workbook_schema,
    ):
        summary = []

        for worksheet in workbook_schema.worksheets.values():

            for input_area in worksheet.get_active_input_areas():

                summary.append(
                    {
                        "sheet_name": input_area.sheet_name,
                        "area_name": input_area.area_name,
                        "range": input_area.address,
                        "status": input_area.status,
                        "confidence": round(
                            float(input_area.confidence),
                            2,
                        ),
                    }
                )

        return summary