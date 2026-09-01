# tests/test_mapping_profile_service.py

from schema.workbook_schema import InputArea, RangeSchema, WorkbookSchema, WorksheetSchema
from services.mapping_profile_service import MappingProfileService


def _make_schema():
    workbook_schema = WorkbookSchema(
        workbook_name="Template.xlsx",
        workbook_path="/tmp/Template.xlsx",
    )

    worksheet_schema = WorksheetSchema(sheet_name="Labour")

    worksheet_schema.add_input_area(
        InputArea(
            area_name="Day Rate",
            sheet_name="Labour",
            area_range=RangeSchema("Labour", "B2", "B10"),
            user_confirmed=True,
        )
    )

    workbook_schema.add_worksheet(worksheet_schema)
    return workbook_schema


def test_save_and_load_profile_round_trip(tmp_path):
    service = MappingProfileService(profile_directory=str(tmp_path))

    workbook_schema = _make_schema()
    workbook_schema.worksheets["Labour"].expect_discrepancies = True

    service.save_profile("my-template", workbook_schema)

    assert "my-template" in service.list_profiles()

    profile_data = service.load_profile("my-template")
    assert profile_data is not None
    assert profile_data["workbook_name"] == "Template.xlsx"
    assert profile_data["sheet_settings"]["Labour"]["expect_discrepancies"]


def test_apply_profile_restores_confirmed_status_and_range_edits(tmp_path):
    service = MappingProfileService(profile_directory=str(tmp_path))

    original_schema = _make_schema()
    profile_data = service._serialise_schema(original_schema)

    # Simulate the user editing the range and confirming it, then
    # re-detecting from scratch (a fresh, unconfirmed schema) and
    # applying the saved profile on top.
    profile_data["input_areas"]["Labour::Day Rate"]["start_cell"] = "B3"
    profile_data["input_areas"]["Labour::Day Rate"]["end_cell"] = "B20"

    fresh_schema = _make_schema()
    for worksheet_schema in fresh_schema.worksheets.values():
        for input_area in worksheet_schema.input_areas:
            input_area.user_confirmed = False

    result_schema = service.apply_profile(fresh_schema, profile_data)

    input_area = result_schema.worksheets["Labour"].input_areas[0]
    assert input_area.user_confirmed is True
    assert input_area.area_range.start_cell == "B3"
    assert input_area.area_range.end_cell == "B20"


def test_apply_profile_restores_expect_discrepancies_flag(tmp_path):
    service = MappingProfileService(profile_directory=str(tmp_path))

    original_schema = _make_schema()
    original_schema.worksheets["Labour"].expect_discrepancies = True
    profile_data = service._serialise_schema(original_schema)

    fresh_schema = _make_schema()
    assert fresh_schema.worksheets["Labour"].expect_discrepancies is False

    result_schema = service.apply_profile(fresh_schema, profile_data)
    assert result_schema.worksheets["Labour"].expect_discrepancies is True


def test_apply_profile_recreates_user_drawn_areas_not_on_fresh_schema(tmp_path):
    service = MappingProfileService(profile_directory=str(tmp_path))

    original_schema = _make_schema()
    worksheet_schema = original_schema.worksheets["Labour"]

    worksheet_schema.add_input_area(
        InputArea(
            area_name="Hand-Drawn Area",
            sheet_name="Labour",
            area_range=RangeSchema("Labour", "D2", "D10"),
            user_created=True,
            user_confirmed=True,
            detected_by_ai=False,
        )
    )

    profile_data = service._serialise_schema(original_schema)

    # A freshly re-detected schema that never had the hand-drawn area.
    fresh_schema = _make_schema()

    result_schema = service.apply_profile(fresh_schema, profile_data)

    area_names = {
        input_area.area_name
        for input_area in result_schema.worksheets["Labour"].input_areas
    }
    assert "Hand-Drawn Area" in area_names


def test_apply_profile_with_none_data_returns_schema_unchanged(tmp_path):
    service = MappingProfileService(profile_directory=str(tmp_path))
    schema = _make_schema()

    result = service.apply_profile(schema, None)
    assert result is schema


def test_delete_and_list_profiles(tmp_path):
    service = MappingProfileService(profile_directory=str(tmp_path))
    service.save_profile("profile-one", _make_schema())
    service.save_profile("profile-two", _make_schema())

    assert service.list_profiles() == ["profile-one", "profile-two"]

    service.delete_profile("profile-one")
    assert service.list_profiles() == ["profile-two"]
