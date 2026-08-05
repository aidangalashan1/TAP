# services/mapping_profile_service.py

import json
from pathlib import Path

from schema.workbook_schema import RangeSchema


class MappingProfileService:
    """
    Persists confirmed/edited input areas so users do not need
    to repeatedly remap the same template.

    Stores, per worksheet + input area name:
        - area range
        - confirmed / user-created status

    Example:

    {
        "workbook_name": "Tender Template.xlsx",
        "input_areas": {
            "Sheet1::Input Area 1": {
                "sheet_name": "Sheet1",
                "start_cell": "H19",
                "end_cell": "H300",
                "user_confirmed": true,
                "user_created": false
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

        saved_areas = profile_data.get(
            "input_areas",
            {},
        )

        for worksheet_schema in workbook_schema.worksheets.values():

            for input_area in worksheet_schema.input_areas:

                key = self._area_key(
                    worksheet_schema.sheet_name,
                    input_area.area_name,
                )

                area_data = saved_areas.get(key)

                if area_data is None:
                    continue

                input_area.area_range = RangeSchema(
                    sheet_name=input_area.sheet_name,
                    start_cell=area_data["start_cell"],
                    end_cell=area_data["end_cell"],
                )

                if area_data.get("user_confirmed"):
                    input_area.user_confirmed = True

                if area_data.get("user_created"):
                    input_area.user_created = True

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

    def _area_key(
        self,
        sheet_name,
        area_name,
    ):
        return f"{sheet_name}::{area_name}"

    def _serialise_schema(
        self,
        workbook_schema,
    ):
        data = {
            "workbook_name": workbook_schema.workbook_name,
            "input_areas": {},
        }

        for worksheet_schema in workbook_schema.worksheets.values():

            for input_area in worksheet_schema.input_areas:

                if input_area.is_deleted:
                    continue

                key = self._area_key(
                    worksheet_schema.sheet_name,
                    input_area.area_name,
                )

                data["input_areas"][key] = {
                    "sheet_name": input_area.sheet_name,
                    "start_cell": input_area.area_range.start_cell,
                    "end_cell": input_area.area_range.end_cell,
                    "user_confirmed": input_area.user_confirmed,
                    "user_created": input_area.user_created,
                }

        return data
