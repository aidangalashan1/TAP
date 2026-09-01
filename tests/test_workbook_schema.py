# tests/test_workbook_schema.py

from schema.workbook_schema import (
    InputArea,
    RangeOrientation,
    RangeSchema,
    WorkbookSchema,
    WorksheetSchema,
)


def test_range_schema_detects_orientation():
    assert RangeSchema("Sheet1", "B2", "B2").orientation == (
        RangeOrientation.SINGLE_CELL
    )
    assert RangeSchema("Sheet1", "B2", "B10").orientation == (
        RangeOrientation.VERTICAL
    )
    assert RangeSchema("Sheet1", "B2", "F2").orientation == (
        RangeOrientation.HORIZONTAL
    )
    assert RangeSchema("Sheet1", "B2", "F10").orientation == (
        RangeOrientation.BLOCK
    )


def test_range_schema_contains_and_intersects():
    range_a = RangeSchema("Sheet1", "B2", "D10")

    assert range_a.contains("C5")
    assert not range_a.contains("E5")

    range_b = RangeSchema("Sheet1", "D10", "F15")
    range_c = RangeSchema("Sheet1", "E20", "F25")
    range_d = RangeSchema("Sheet2", "B2", "D10")

    assert range_a.intersects(range_b)
    assert not range_a.intersects(range_c)
    # Different sheets never intersect, even with overlapping cells.
    assert not range_a.intersects(range_d)


def test_range_schema_iter_cell_references():
    range_schema = RangeSchema("Sheet1", "A1", "B2")

    assert range_schema.iter_cell_references() == [
        "A1", "B1", "A2", "B2",
    ]


def test_input_area_status_transitions():
    input_area = InputArea(
        area_name="Day Rate",
        sheet_name="Sheet1",
        area_range=RangeSchema("Sheet1", "B2", "B10"),
    )

    assert input_area.status == "DETECTED"

    input_area.confirm()
    assert input_area.status == "CONFIRMED"

    input_area.mark_ignored()
    assert input_area.status == "IGNORED"
    assert not input_area.is_deleted

    input_area.mark_deleted()
    assert input_area.status == "DELETED"
    assert not input_area.is_ignored

    input_area.restore()
    assert not input_area.is_deleted
    assert not input_area.is_ignored


def test_worksheet_schema_active_vs_all_input_areas():
    worksheet_schema = WorksheetSchema(sheet_name="Sheet1")

    confirmed = InputArea(
        area_name="Confirmed",
        sheet_name="Sheet1",
        area_range=RangeSchema("Sheet1", "B2", "B10"),
        user_confirmed=True,
    )

    removed = InputArea(
        area_name="Removed",
        sheet_name="Sheet1",
        area_range=RangeSchema("Sheet1", "C2", "C10"),
        is_deleted=True,
    )

    worksheet_schema.add_input_area(confirmed)
    worksheet_schema.add_input_area(removed)

    assert worksheet_schema.get_active_input_areas() == [confirmed]
    assert len(worksheet_schema.get_all_input_areas()) == 2

    # New field from the "discrepancies expected" toggle - defaults
    # to False so existing profiles/schemas behave as before.
    assert worksheet_schema.expect_discrepancies is False


def test_workbook_schema_get_confirmed_input_areas():
    workbook_schema = WorkbookSchema(
        workbook_name="Template.xlsx",
        workbook_path="/tmp/Template.xlsx",
    )

    worksheet_schema = WorksheetSchema(sheet_name="Sheet1")

    confirmed = InputArea(
        area_name="Confirmed",
        sheet_name="Sheet1",
        area_range=RangeSchema("Sheet1", "B2", "B10"),
        user_confirmed=True,
    )

    detected_only = InputArea(
        area_name="Detected",
        sheet_name="Sheet1",
        area_range=RangeSchema("Sheet1", "C2", "C10"),
    )

    worksheet_schema.add_input_area(confirmed)
    worksheet_schema.add_input_area(detected_only)
    workbook_schema.add_worksheet(worksheet_schema)

    assert workbook_schema.get_confirmed_input_areas() == [confirmed]
    assert len(workbook_schema.get_input_areas()) == 2
