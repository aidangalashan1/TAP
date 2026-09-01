# tests/test_mapping_profile_dialog.py
#
# Exercises MappingProfileDialog's save logic without opening a real
# window: a bare instance is built via __new__, and tkinter's
# simpledialog/messagebox prompts are monkeypatched so the test
# controls what the "user" enters/clicks rather than depending on
# whether a real display is available.

import tkinter.messagebox as messagebox
import tkinter.simpledialog as simpledialog

from gui.mapping_profile_dialog import MappingProfileDialog
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


def _bare_dialog(tmp_path, workbook_schema=None):
    dialog = object.__new__(MappingProfileDialog)
    dialog.workbook_schema = workbook_schema or _make_schema()
    dialog.window = None
    dialog.mapping_profile_service = MappingProfileService(
        profile_directory=str(tmp_path)
    )

    def _load_profiles():
        pass

    dialog._load_profiles = _load_profiles
    return dialog


def test_save_profile_with_new_name_does_not_prompt_to_overwrite(
    tmp_path, monkeypatch
):
    dialog = _bare_dialog(tmp_path)

    monkeypatch.setattr(
        simpledialog, "askstring", lambda *a, **k: "my-template"
    )

    askyesno_calls = []
    monkeypatch.setattr(
        messagebox,
        "askyesno",
        lambda *a, **k: askyesno_calls.append(a) or True,
    )
    monkeypatch.setattr(messagebox, "showinfo", lambda *a, **k: None)

    dialog._save_profile()

    assert askyesno_calls == []
    assert "my-template" in dialog.mapping_profile_service.list_profiles()


def test_save_profile_over_existing_name_prompts_and_overwrites_on_yes(
    tmp_path, monkeypatch
):
    dialog = _bare_dialog(tmp_path)
    dialog.mapping_profile_service.save_profile(
        "my-template", _make_schema()
    )

    monkeypatch.setattr(
        simpledialog, "askstring", lambda *a, **k: "my-template"
    )
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    monkeypatch.setattr(messagebox, "showinfo", lambda *a, **k: None)

    # A different schema than what's already saved under this name -
    # if the overwrite goes through, the saved profile should reflect
    # this new schema rather than the original.
    new_schema = _make_schema()
    new_schema.worksheets["Labour"].expect_discrepancies = True
    dialog.workbook_schema = new_schema

    dialog._save_profile()

    profile_data = dialog.mapping_profile_service.load_profile(
        "my-template"
    )
    assert profile_data["sheet_settings"]["Labour"]["expect_discrepancies"]


def test_save_profile_over_existing_name_does_not_overwrite_on_no(
    tmp_path, monkeypatch
):
    dialog = _bare_dialog(tmp_path)
    dialog.mapping_profile_service.save_profile(
        "my-template", _make_schema()
    )

    monkeypatch.setattr(
        simpledialog, "askstring", lambda *a, **k: "my-template"
    )
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: False)
    monkeypatch.setattr(messagebox, "showinfo", lambda *a, **k: None)

    new_schema = _make_schema()
    new_schema.worksheets["Labour"].expect_discrepancies = True
    dialog.workbook_schema = new_schema

    dialog._save_profile()

    # Declining the overwrite must leave the originally saved profile
    # untouched.
    profile_data = dialog.mapping_profile_service.load_profile(
        "my-template"
    )
    assert not profile_data["sheet_settings"]["Labour"]["expect_discrepancies"]
