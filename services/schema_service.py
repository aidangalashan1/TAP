# services/schema_service.py

from schema.schema_builder import SchemaBuilder
from schema.workbook_schema import FieldRole


class SchemaService:
    """
    Central schema orchestration service.

    Responsibilities:
        - Build workbook schemas
        - Build DataRecord collections
        - Retrieve fields, regions and sheets
        - Update user mappings
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

    # --------------------------------------------------
    # Region Operations
    # --------------------------------------------------

    def get_regions(
        self,
        workbook_schema,
    ):
        return workbook_schema.get_all_regions()

    def get_region_names(
        self,
        workbook_schema,
    ):
        return [
            region.region_name
            for region in workbook_schema.get_all_regions()
        ]

    def find_region(
        self,
        workbook_schema,
        region_name,
    ):
        target = region_name.strip().lower()

        for region in workbook_schema.get_all_regions():

            if (
                region.region_name.strip().lower()
                == target
            ):
                return region

        return None

    # --------------------------------------------------
    # Field Operations
    # --------------------------------------------------

    def get_fields(
        self,
        workbook_schema,
    ):
        return workbook_schema.get_all_fields()

    def get_field_names(
        self,
        workbook_schema,
    ):
        return workbook_schema.get_unique_field_names()

    def find_field(
        self,
        workbook_schema,
        field_name,
    ):
        target = field_name.strip().lower()

        for field_schema in workbook_schema.get_all_fields():

            if (
                field_schema.field_name.strip().lower()
                == target
            ):
                return field_schema

        return None

    def get_fields_by_role(
        self,
        workbook_schema,
        role,
    ):
        if isinstance(role, str):
            role = FieldRole(role)

        results = []

        for field_schema in workbook_schema.get_all_fields():

            if field_schema.role == role:
                results.append(field_schema)

        return results

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
    # Mapping Operations
    # --------------------------------------------------

    def update_field_mapping(
        self,
        workbook_schema,
        field_name,
        *,
        new_name=None,
        new_role=None,
        new_field_range=None,
        new_header_range=None,
    ):
        field_schema = self.find_field(
            workbook_schema,
            field_name,
        )

        if field_schema is None:
            return False

        if new_name is not None:
            field_schema.field_name = new_name

        if new_role is not None:
            field_schema.role = new_role

        if new_field_range is not None:
            field_schema.field_range = new_field_range

        if new_header_range is not None:
            field_schema.header_range = new_header_range

        field_schema.user_defined = True

        return True

    # --------------------------------------------------
    # Summary Operations
    # --------------------------------------------------

    def get_schema_summary(
        self,
        workbook_schema,
    ):
        summary = []

        for worksheet in workbook_schema.worksheets.values():

            for region in worksheet.regions:

                summary.append(
                    {
                        "sheet_name": region.sheet_name,
                        "region_name": region.region_name,
                        "range": region.region_range.address,
                        "field_count": len(
                            region.fields
                        ),
                        "confidence": round(
                            float(region.confidence),
                            2,
                        ),
                    }
                )

        return summary

    def get_field_summary(
        self,
        workbook_schema,
    ):
        summary = []

        for field_schema in workbook_schema.get_all_fields():

            summary.append(
                {
                    "field_name": field_schema.field_name,
                    "sheet_name": field_schema.sheet_name,
                    "role": field_schema.role.value,
                    "data_type": field_schema.data_type.value,
                    "range": (
                        field_schema.data_range
                        if field_schema.data_range
                        else ""
                    ),
                    "confidence": round(
                        float(field_schema.confidence),
                        2,
                    ),
                }
            )

        return summary