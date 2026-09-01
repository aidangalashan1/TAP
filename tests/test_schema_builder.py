# tests/test_schema_builder.py

from parsers.workbook_parser import CellInfo, WorkbookInfo, WorksheetInfo
from schema.schema_builder import SchemaBuilder
from schema.workbook_schema import InputArea, RangeSchema, WorkbookSchema, WorksheetSchema


def _cell(sheet_name, cell_reference, row, column, value):
    return CellInfo(
        sheet_name=sheet_name,
        cell_reference=cell_reference,
        row_number=row,
        column_number=column,
        value=value,
    )


def _make_workbook(rows):
    """rows: list of (row_number, day_rate_value, call_out_value)."""

    worksheet = WorksheetInfo(worksheet_name="Labour")

    for row_number, day_rate, call_out in rows:
        worksheet.add_cell(_cell("Labour", f"B{row_number}", row_number, 2, day_rate))
        worksheet.add_cell(_cell("Labour", f"C{row_number}", row_number, 3, call_out))

    workbook = WorkbookInfo(file_name="Supplier.xlsx", file_path="/tmp/Supplier.xlsx")
    workbook.add_worksheet(worksheet)
    return workbook


def _make_confirmed_schema():
    workbook_schema = WorkbookSchema(
        workbook_name="Template.xlsx",
        workbook_path="/tmp/Template.xlsx",
    )

    worksheet_schema = WorksheetSchema(sheet_name="Labour")

    day_rate_area = InputArea(
        area_name="Day Rate",
        sheet_name="Labour",
        area_range=RangeSchema("Labour", "B2", "B10"),
        user_confirmed=True,
    )

    call_out_area = InputArea(
        area_name="Call-Out Fee",
        sheet_name="Labour",
        area_range=RangeSchema("Labour", "C2", "C10"),
        user_confirmed=True,
    )

    worksheet_schema.add_input_area(day_rate_area)
    worksheet_schema.add_input_area(call_out_area)
    workbook_schema.add_worksheet(worksheet_schema)

    return workbook_schema


def test_build_records_reads_confirmed_input_areas():
    workbook = _make_workbook([(2, 120, 50), (3, 90, None)])
    workbook_schema = _make_confirmed_schema()

    records = SchemaBuilder().build_records(workbook, workbook_schema)

    assert len(records) == 2

    row_2 = next(r for r in records if r.record_reference == "Row 2")
    assert row_2.sheet_name == "Labour"
    assert row_2.get_value("Day Rate") == 120
    assert row_2.get_value("Call-Out Fee") == 50
    assert row_2.get_cell_reference("Day Rate") == "B2"

    row_3 = next(r for r in records if r.record_reference == "Row 3")
    assert row_3.get_value("Day Rate") == 90
    # Blank cell is still recorded (as None), just doesn't gate the
    # row's inclusion on its own - the row is kept because Day Rate
    # has a value.
    assert row_3.has_field("Call-Out Fee")
    assert row_3.get_value("Call-Out Fee") is None


def test_build_records_skips_fully_blank_rows():
    workbook = _make_workbook([(2, 120, 50), (4, None, None)])
    workbook_schema = _make_confirmed_schema()

    records = SchemaBuilder().build_records(workbook, workbook_schema)

    # Row 4 has no value in either input area, so no record at all -
    # nothing to compare or flag there.
    assert [r.record_reference for r in records] == ["Row 2"]


def test_build_records_falls_back_to_detected_when_nothing_confirmed():
    workbook = _make_workbook([(2, 120, 50)])
    workbook_schema = _make_confirmed_schema()

    for worksheet_schema in workbook_schema.worksheets.values():
        for input_area in worksheet_schema.input_areas:
            input_area.user_confirmed = False

    records = SchemaBuilder().build_records(workbook, workbook_schema)

    # get_analysis_areas() falls back to all detected areas when none
    # are confirmed, so the row is still read rather than silently
    # producing nothing.
    assert len(records) == 1


def test_get_missing_sheets():
    workbook = _make_workbook([(2, 120, 50)])
    workbook_schema = _make_confirmed_schema()

    other_sheet = WorksheetSchema(sheet_name="Extras")
    other_sheet.add_input_area(
        InputArea(
            area_name="Extra Fee",
            sheet_name="Extras",
            area_range=RangeSchema("Extras", "B2", "B10"),
            user_confirmed=True,
        )
    )
    workbook_schema.add_worksheet(other_sheet)

    missing = SchemaBuilder().get_missing_sheets(workbook, workbook_schema)

    assert missing == ["Extras"]
