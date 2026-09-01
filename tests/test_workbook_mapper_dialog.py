# tests/test_workbook_mapper_dialog.py
#
# Exercises WorkbookMapperDialog's cell-highlighting logic without
# opening a real window - a bare instance built via __new__, with a
# fake sheet_control that just records highlight_cells() calls
# instead of driving a real tksheet widget. This is the code path
# that was rewritten from one highlight_cells() call per cell to
# batched calls grouped by colour/status, for performance on large
# sheets - these tests lock in that the batching produces the same
# end result as the old per-cell version would have.

from dataclasses import dataclass, field

from gui.workbook_mapper_dialog import WorkbookMapperDialog
from schema.workbook_schema import InputArea, RangeSchema, WorkbookSchema, WorksheetSchema


class _FakeSheetControl:
    def __init__(self):
        self.highlight_calls = []

    def highlight_cells(self, **kwargs):
        self.highlight_calls.append(kwargs)

    def redraw(self):
        pass


@dataclass
class _FakeCell:
    row_number: int
    column_number: int
    fill_colour: str = ""


@dataclass
class _FakeWorksheet:
    cells: list = field(default_factory=list)


def _bare_dialog():
    dialog = object.__new__(WorkbookMapperDialog)
    dialog.sheet_control = _FakeSheetControl()
    dialog.current_sheet_name = "Labour"
    return dialog


def test_apply_formatting_batches_cells_by_colour():
    dialog = _bare_dialog()

    worksheet = _FakeWorksheet(
        cells=[
            _FakeCell(1, 1, fill_colour="FFFF0000"),
            _FakeCell(1, 2, fill_colour="FFFF0000"),
            _FakeCell(2, 1, fill_colour="FF00FF00"),
        ]
    )

    dialog._apply_formatting(worksheet)

    calls = dialog.sheet_control.highlight_calls
    assert len(calls) == 2

    red_call = next(c for c in calls if c["bg"] == "#FF0000")
    green_call = next(c for c in calls if c["bg"] == "#00FF00")

    assert sorted(red_call["cells"]) == [(0, 0), (0, 1)]
    assert green_call["cells"] == [(1, 0)]
    assert red_call["redraw"] is False


def test_apply_formatting_skips_cells_with_no_fill():
    dialog = _bare_dialog()
    worksheet = _FakeWorksheet(cells=[_FakeCell(1, 1, fill_colour="")])

    dialog._apply_formatting(worksheet)

    assert dialog.sheet_control.highlight_calls == []


def test_input_area_status_priority():
    dialog = _bare_dialog()

    detected = InputArea(
        area_name="A", sheet_name="Labour",
        area_range=RangeSchema("Labour", "B2", "B2"),
    )
    confirmed = InputArea(
        area_name="B", sheet_name="Labour",
        area_range=RangeSchema("Labour", "B3", "B3"),
        user_confirmed=True,
    )
    ignored = InputArea(
        area_name="C", sheet_name="Labour",
        area_range=RangeSchema("Labour", "B4", "B4"),
        is_ignored=True,
    )
    removed = InputArea(
        area_name="D", sheet_name="Labour",
        area_range=RangeSchema("Labour", "B5", "B5"),
        is_deleted=True,
    )

    assert dialog._input_area_status(detected) == "detected"
    assert dialog._input_area_status(confirmed) == "confirmed"
    assert dialog._input_area_status(ignored) == "ignored"
    assert dialog._input_area_status(removed) == "removed"


def test_input_area_cell_indexes_are_zero_based():
    dialog = _bare_dialog()

    input_area = InputArea(
        area_name="A", sheet_name="Labour",
        area_range=RangeSchema("Labour", "B2", "C3"),
    )

    indexes = dialog._input_area_cell_indexes(input_area)

    # B2:C3 is rows 2-3, columns B(2)-C(3) - zero-based that's
    # rows 1-2, columns 1-2.
    assert sorted(indexes) == [(1, 1), (1, 2), (2, 1), (2, 2)]


def test_render_input_areas_defaults_whole_sheet_to_ignored_then_layers_status():
    dialog = _bare_dialog()

    workbook_schema = WorkbookSchema(
        workbook_name="Template.xlsx", workbook_path="/tmp/Template.xlsx"
    )
    worksheet_schema = WorksheetSchema(sheet_name="Labour")

    detected = InputArea(
        area_name="Detected Area", sheet_name="Labour",
        area_range=RangeSchema("Labour", "B2", "B2"),
    )
    confirmed = InputArea(
        area_name="Confirmed Area", sheet_name="Labour",
        area_range=RangeSchema("Labour", "C2", "C2"),
        user_confirmed=True,
    )

    worksheet_schema.add_input_area(detected)
    worksheet_schema.add_input_area(confirmed)
    workbook_schema.add_worksheet(worksheet_schema)

    dialog.workbook_schema = workbook_schema

    worksheet = _FakeWorksheet(cells=[])
    dialog._render_input_areas(worksheet)

    calls = dialog.sheet_control.highlight_calls

    default_call = calls[0]
    assert default_call["row"] == "all"
    assert default_call["column"] == "all"
    assert default_call["bg"] == WorkbookMapperDialog.STATUS_COLOURS["ignored"]

    detected_call = next(
        c for c in calls if c.get("bg") == WorkbookMapperDialog.STATUS_COLOURS["detected"]
    )
    confirmed_call = next(
        c for c in calls if c.get("bg") == WorkbookMapperDialog.STATUS_COLOURS["confirmed"]
    )

    assert detected_call["cells"] == [(1, 1)]
    assert confirmed_call["cells"] == [(1, 2)]

    # confirmed must be applied after detected so it isn't clobbered -
    # matches removed > confirmed > detected > default priority.
    assert calls.index(confirmed_call) > calls.index(detected_call)


def test_render_input_areas_overlapping_removed_beats_confirmed():
    """
    Two areas over the same cell: one confirmed, one removed. The old
    per-cell logic returned "removed" the instant it saw a deleted
    area, regardless of encounter order - the batched version must
    still resolve the overlap the same way, by applying removed last.
    """

    dialog = _bare_dialog()

    workbook_schema = WorkbookSchema(
        workbook_name="Template.xlsx", workbook_path="/tmp/Template.xlsx"
    )
    worksheet_schema = WorksheetSchema(sheet_name="Labour")

    confirmed = InputArea(
        area_name="Confirmed Area", sheet_name="Labour",
        area_range=RangeSchema("Labour", "B2", "B2"),
        user_confirmed=True,
    )
    removed = InputArea(
        area_name="Removed Area", sheet_name="Labour",
        area_range=RangeSchema("Labour", "B2", "B2"),
        is_deleted=True,
    )

    worksheet_schema.add_input_area(confirmed)
    worksheet_schema.add_input_area(removed)
    workbook_schema.add_worksheet(worksheet_schema)

    dialog.workbook_schema = workbook_schema

    dialog._render_input_areas(_FakeWorksheet(cells=[]))

    calls = dialog.sheet_control.highlight_calls
    removed_call = next(
        c for c in calls if c.get("bg") == WorkbookMapperDialog.STATUS_COLOURS["removed"]
    )
    confirmed_call = next(
        c for c in calls if c.get("bg") == WorkbookMapperDialog.STATUS_COLOURS["confirmed"]
    )

    assert calls.index(removed_call) > calls.index(confirmed_call)
