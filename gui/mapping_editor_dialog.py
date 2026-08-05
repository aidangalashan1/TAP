# gui/mapping_editor_dialog.py

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from schema.workbook_schema import (
    FieldRole,
    RangeSchema,
)


class MappingEditorDialog:

    def __init__(
        self,
        parent,
        workbook_schema,
    ):
        self.parent = parent
        self.workbook_schema = workbook_schema
        self.result = None

        self.window = tk.Toplevel(parent)
        self.window.title("Workbook Mapping Review")
        self.window.geometry("1100x700")
        self.window.transient(parent)
        self.window.grab_set()

        self.field_lookup = {}

        self._build_ui()
        self._load_fields()

    def show(self):
        self.parent.wait_window(self.window)
        return self.result

    # ==================================================
    # UI
    # ==================================================

    def _build_ui(self):

        main = ttk.Frame(
            self.window,
            padding=10,
        )

        main.pack(
            fill=tk.BOTH,
            expand=True,
        )

        ttk.Label(
            main,
            text="Workbook Mapping Review",
            font=("Segoe UI", 14, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 10),
        )

        content = ttk.Frame(main)
        content.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self._build_field_grid(content)
        self._build_editor(content)
        self._build_buttons(main)

    def _build_field_grid(self, parent):

        frame = ttk.LabelFrame(
            parent,
            text="Detected Fields",
            padding=10,
        )

        frame.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
        )

        columns = (
            "field",
            "sheet",
            "role",
            "range",
        )

        self.tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
        )

        self.tree.heading("field", text="Field")
        self.tree.heading("sheet", text="Sheet")
        self.tree.heading("role", text="Role")
        self.tree.heading("range", text="Range")

        self.tree.column("field", width=240)
        self.tree.column("sheet", width=140)
        self.tree.column("role", width=120)
        self.tree.column("range", width=180)

        self.tree.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self.tree.bind(
            "<<TreeviewSelect>>",
            self._field_selected,
        )

    def _build_editor(self, parent):

        frame = ttk.LabelFrame(
            parent,
            text="Mapping",
            padding=10,
        )

        frame.pack(
            side=tk.LEFT,
            fill=tk.Y,
            padx=(10, 0),
        )

        self.field_name_var = tk.StringVar()
        self.role_var = tk.StringVar()
        self.start_cell_var = tk.StringVar()
        self.end_cell_var = tk.StringVar()

        ttk.Label(
            frame,
            text="Field Name",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=5,
        )

        ttk.Entry(
            frame,
            textvariable=self.field_name_var,
            width=30,
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )

        ttk.Label(
            frame,
            text="Role",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=5,
        )

        ttk.Combobox(
            frame,
            textvariable=self.role_var,
            values=[r.value for r in FieldRole],
            state="readonly",
            width=27,
        ).grid(
            row=1,
            column=1,
            sticky="w",
        )

        ttk.Label(
            frame,
            text="Start Cell",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            pady=5,
        )

        ttk.Entry(
            frame,
            textvariable=self.start_cell_var,
            width=30,
        ).grid(
            row=2,
            column=1,
            sticky="w",
        )

        ttk.Label(
            frame,
            text="End Cell",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            pady=5,
        )

        ttk.Entry(
            frame,
            textvariable=self.end_cell_var,
            width=30,
        ).grid(
            row=3,
            column=1,
            sticky="w",
        )

        ttk.Button(
            frame,
            text="Apply Changes",
            command=self._apply_changes,
        ).grid(
            row=4,
            column=1,
            sticky="e",
            pady=10,
        )

    def _build_buttons(self, parent):

        frame = ttk.Frame(parent)

        frame.pack(
            fill=tk.X,
            pady=(10, 0),
        )

        ttk.Button(
            frame,
            text="Save",
            command=self._save,
        ).pack(
            side=tk.RIGHT,
            padx=5,
        )

        ttk.Button(
            frame,
            text="Cancel",
            command=self._cancel,
        ).pack(
            side=tk.RIGHT,
        )

    # ==================================================
    # Data Loading
    # ==================================================

    def _load_fields(self):

        for field_schema in self.workbook_schema.get_all_fields():

            if field_schema.field_range:
                range_text = (
                    field_schema.field_range.address
                )
            else:
                range_text = ""

            item_id = self.tree.insert(
                "",
                "end",
                values=(
                    field_schema.field_name,
                    field_schema.sheet_name,
                    field_schema.role.value,
                    range_text,
                ),
            )

            self.field_lookup[item_id] = field_schema

    # ==================================================
    # Selection
    # ==================================================

    def _field_selected(self, event=None):

        selection = self.tree.selection()

        if not selection:
            return

        field_schema = self.field_lookup[
            selection[0]
        ]

        self.field_name_var.set(
            field_schema.field_name
        )

        self.role_var.set(
            field_schema.role.value
        )

        if field_schema.field_range:

            self.start_cell_var.set(
                field_schema.field_range.start_cell
            )

            self.end_cell_var.set(
                field_schema.field_range.end_cell
            )

    # ==================================================
    # Editing
    # ==================================================

    def _apply_changes(self):

        selection = self.tree.selection()

        if not selection:
            return

        field_schema = self.field_lookup[
            selection[0]
        ]

        field_schema.field_name = (
            self.field_name_var.get().strip()
        )

        field_schema.role = FieldRole(
            self.role_var.get()
        )

        start_cell = (
            self.start_cell_var.get().strip()
        )

        end_cell = (
            self.end_cell_var.get().strip()
        )

        if start_cell and end_cell:

            field_schema.field_range = (
                RangeSchema(
                    sheet_name=field_schema.sheet_name,
                    start_cell=start_cell,
                    end_cell=end_cell,
                )
            )

        field_schema.user_defined = True

        self._refresh_grid()

    def _refresh_grid(self):

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.field_lookup.clear()

        self._load_fields()

    # ==================================================
    # Save / Cancel
    # ==================================================

    def _save(self):

        self.result = self.workbook_schema
        self.window.destroy()

    def _cancel(self):

        self.result = None
        self.window.destroy()