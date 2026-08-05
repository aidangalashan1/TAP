# services/mapping_profile_service.py

import json
from pathlib import Path

from schema.workbook_schema import FieldRole
from schema.workbook_schema import RangeSchema


class MappingProfileService:
    """
    Persists workbook mapping decisions so users do not need
    to repeatedly remap the same template.

    Stores:
        - field name
        - field role
        - field range
        - header range

    Example:

    {
        "Weekday Rate": {
            "role": "PRICE",
            "field_range": {
                "start_cell": "H19",
                "end_cell": "H300"
            },
            "header_range": {
                "start_cell": "H18",
                "end_cell": "H18"
            }
        }
    }
    """

    def __init__(self, profile_directory="mapping_profiles"):
        self.profile_directory = Path(profile_directory)

        self.profile_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ==================================================
    # Profile Management
    # ==================================================

    def save_profile(
        self,
        profile_name,
        workbook_schema,
    ):
        profile_path = self._get_profile_path(
            profile_name
        )

        profile_data = self._serialise_schema(
            workbook_schema
        )

        with open(
            profile_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                profile_data,
                file,
                indent=4,
            )

    def load_profile(
        self,
        profile_name,
    ):
        profile_path = self._get_profile_path(
            profile_name
        )

        if not profile_path.exists():
            return None

        with open(
            profile_path,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    def delete_profile(
        self,
        profile_name,
    ):
        profile_path = self._get_profile_path(
            profile_name
        )

        if profile_path.exists():
            profile_path.unlink()

    def list_profiles(self):
        profiles = []

        for file_path in self.profile_directory.glob(
            "*.json"
        ):
            profiles.append(
                file_path.stem
            )

        return sorted(profiles)

    # ==================================================
    # Apply Profile
    # ==================================================

    def apply_profile(
        self,
        workbook_schema,
        profile_data,
    ):
        if profile_data is None:
            return workbook_schema

        fields = profile_data.get(
            "fields",
            {},
        )

        for field_schema in workbook_schema.get_all_fields():

            field_data = fields.get(
                field_schema.field_name
            )

            if field_data is None:
                continue

            role_name = field_data.get(
                "role"
            )

            if role_name:
                try:
                    field_schema.role = FieldRole(
                        role_name
                    )
                except ValueError:
                    pass

            field_range_data = field_data.get(
                "field_range"
            )

            if field_range_data:

                field_schema.field_range = (
                    RangeSchema(
                        sheet_name=field_schema.sheet_name,
                        start_cell=field_range_data["start_cell"],
                        end_cell=field_range_data["end_cell"],
                    )
                )

            header_range_data = field_data.get(
                "header_range"
            )

            if header_range_data:

                field_schema.header_range = (
                    RangeSchema(
                        sheet_name=field_schema.sheet_name,
                        start_cell=header_range_data["start_cell"],
                        end_cell=header_range_data["end_cell"],
                    )
                )

            field_schema.user_defined = True

        return workbook_schema

    # ==================================================
    # Internal Helpers
    # ==================================================

    def _get_profile_path(
        self,
        profile_name,
    ):
        safe_name = self._safe_name(
            profile_name
        )

        return (
            self.profile_directory
            / f"{safe_name}.json"
        )

    def _safe_name(
        self,
        value,
    ):
        invalid = "\\/:*?<>|"

        result = str(value)

        for character in invalid:
            result = result.replace(
                character,
                "_"
            )

        result = result.strip()

        if not result:
            return "profile"

        return result

    def _serialise_schema(
        self,
        workbook_schema,
    ):
        data = {
            "workbook_name": workbook_schema.workbook_name,
            "fields": {},
        }

        for field_schema in workbook_schema.get_all_fields():

            data["fields"][
                field_schema.field_name
            ] = {
                "role": field_schema.role.value,
                "field_range": (
                    self._serialise_range(
                        field_schema.field_range
                    )
                ),
                "header_range": (
                    self._serialise_range(
                        field_schema.header_range
                    )
                ),
            }

        return data

    def _serialise_range(
        self,
        range_schema,
    ):
        if range_schema is None:
            return None

        return {
            "start_cell": range_schema.start_cell,
            "end_cell": range_schema.end_cell,
        }