# gui/workbook_mapper_dialog.py

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog

try:
    from tksheet import Sheet
except ImportError:
    Sheet = None

from schema.workbook_schema import (
    RangeSchema,
    RegionSchema,
)


class WorkbookMapperDialog:

    def __init__(
        self,
        parent,
        workbook,
        workbook_schema,
    ):
        self.parent = parent
        self.workbook = workbook
        self.workbook_schema = workbook_schema

        self.result = None

        self.current_sheet_name = None

        self.region_lookup = {}
        self.cell_lookup = {}

        self.window = tk.Toplevel(parent)

        self.window.title(
            "Workbook Mapper"
        )

        self.window.geometry(
            "1800x1000"
        )

        self.window.transient(parent)
        self.window.grab_set()

        self.sheet_control = None
        self.sheet_list = None
        self.region_tree = None
        self.inspector = None

        self.show_regions_var = tk.BooleanVar(
            value=True
        )

        self.show_formatting_var = tk.BooleanVar(
            value=True
        )

        self._build_ui()
        self._load_sheets()

    def show(self):

        self.parent.wait_window(
            self.window
        )

        return self.result

    # ==================================================
    # UI
    # ==================================================

    def _build_ui(self):

        main = ttk.Frame(
            self.window,
            padding=5,
        )

        main.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self._build_toolbar(main)

        body = ttk.Frame(main)

        body.pack(
            fill=tk.BOTH,
            expand=True,
        )

        left = ttk.Frame(body)
        left.pack(
            side=tk.LEFT,
            fill=tk.Y,
        )

        centre = ttk.Frame(body)

        centre.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
            padx=5,
        )

        right = ttk.Frame(body)

        right.pack(
            side=tk.LEFT,
            fill=tk.Y,
        )

        self._build_sheet_panel(left)
        self._build_grid_panel(centre)
        self._build_region_panel(right)
        self._build_inspector(right)

        self._build_footer(main)

    def _build_toolbar(
        self,
        parent,
    ):
        frame = ttk.Frame(parent)

        frame.pack(
            fill=tk.X,
            pady=(0, 5),
        )

        ttk.Checkbutton(
            frame,
            text="Show Regions",
            variable=self.show_regions_var,
            command=self._refresh_display,
        ).pack(
            side=tk.LEFT,
            padx=5,
        )

        ttk.Checkbutton(
            frame,
            text="Show Formatting",
            variable=self.show_formatting_var,
            command=self._refresh_display,
        ).pack(
            side=tk.LEFT,
            padx=5,
        )

    def _build_sheet_panel(
        self,
        parent,
    ):
        frame = ttk.LabelFrame(
            parent,
            text="Sheets",
            padding=5,
        )

        frame.pack(
            fill=tk.Y,
            expand=True,
        )

        self.sheet_list = tk.Listbox(
            frame,
            width=35,
            exportselection=False,
        )

        self.sheet_list.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self.sheet_list.bind(
            "<<ListboxSelect>>",
            self._sheet_selected,
        )

    def _build_grid_panel(
        self,
        parent,
    ):
        frame = ttk.LabelFrame(
            parent,
            text="Workbook View",
            padding=5,
        )

        frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        if Sheet is None:

            self.sheet_control = tk.Text(
                frame
            )

            self.sheet_control.insert(
                tk.END,
                (
                    "Install tksheet:\n\n"
                    "pip install tksheet"
                ),
            )

            self.sheet_control.pack(
                fill=tk.BOTH,
                expand=True,
            )

            return

        self.sheet_control = Sheet(
            frame,
            data=[[]],
        )

        self.sheet_control.enable_bindings()

        self.sheet_control.pack(
            fill=tk.BOTH,
            expand=True,
        )

        try:
            self.sheet_control.extra_bindings(
                [
                    (
                        "cell_select",
                        self._cell_selected,
                    ),
                ]
            )
        except Exception:
            pass

    def _build_region_panel(
        self,
        parent,
    ):
        frame = ttk.LabelFrame(
            parent,
            text="Regions",
            padding=5,
        )

        frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self.region_tree = ttk.Treeview(
            frame,
            columns=(
                "range",
                "status",
            ),
            show="headings",
            height=18,
        )

        self.region_tree.heading(
            "range",
            text="Range",
        )

        self.region_tree.heading(
            "status",
            text="Status",
        )

        self.region_tree.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self.region_tree.bind(
            "<<TreeviewSelect>>",
            self._region_selected,
        )

        ttk.Button(
            frame,
            text="Create Region",
            command=self._create_region,
        ).pack(
            fill=tk.X,
            pady=2,
        )

        ttk.Button(
            frame,
            text="Edit Region",
            command=self._edit_region,
        ).pack(
            fill=tk.X,
            pady=2,
        )

        ttk.Button(
            frame,
            text="Delete Region",
            command=self._delete_region,
        ).pack(
            fill=tk.X,
            pady=2,
        )

        ttk.Button(
            frame,
            text="Confirm Region",
            command=self._confirm_region,
        ).pack(
            fill=tk.X,
            pady=2,
        )

    def _build_inspector(
        self,
        parent,
    ):
        frame = ttk.LabelFrame(
            parent,
            text="Inspector",
            padding=5,
        )

        frame.pack(
            fill=tk.BOTH,
            expand=True,
            pady=(5, 0),
        )

        self.inspector = tk.Text(
            frame,
            width=40,
            height=20,
        )

        self.inspector.pack(
            fill=tk.BOTH,
            expand=True,
        )

    def _build_footer(
        self,
        parent,
    ):
        frame = ttk.Frame(parent)

        frame.pack(
            fill=tk.X,
            pady=(5, 0),
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
    # SHEETS
    # ==================================================

    def _load_sheets(self):

        self.sheet_list.delete(
            0,
            tk.END,
        )

        sheet_names = sorted(
            self.workbook.worksheets.keys()
        )

        for sheet_name in sheet_names:

            self.sheet_list.insert(
                tk.END,
                sheet_name,
            )

        if sheet_names:

            self.sheet_list.selection_set(0)

            self._sheet_selected()

    def _sheet_selected(
        self,
        event=None,
    ):
        selection = (
            self.sheet_list.curselection()
        )

        if not selection:
            return

        self.current_sheet_name = (
            self.sheet_list.get(
                selection[0]
            )
        )

        self._render_sheet()
        self._load_regions()

    # ==================================================
    # RENDERING
    # ==================================================

    def _render_sheet(self):

        if Sheet is None:
            return

        worksheet = (
            self.workbook.get_worksheet(
                self.current_sheet_name
            )
        )

        if worksheet is None:
            return

        self.cell_lookup.clear()

        max_row = max(
            (
                cell.row_number
                for cell in worksheet.cells
            ),
            default=1,
        )

        max_column = max(
            (
                cell.column_number
                for cell in worksheet.cells
            ),
            default=1,
        )

        data = [
            ["" for _ in range(max_column)]
            for _ in range(max_row)
        ]

        for cell in worksheet.cells:

            self.cell_lookup[
                cell.cell_reference
            ] = cell

            data[
                cell.row_number - 1
            ][
                cell.column_number - 1
            ] = (
                ""
                if cell.value is None
                else str(cell.value)
            )

        self.sheet_control.set_sheet_data(
            data
        )

        if self.show_formatting_var.get():
            self._apply_formatting(
                worksheet
            )

        if self.show_regions_var.get():
            self._render_regions()

    def _apply_formatting(
        self,
        worksheet,
    ):
        for cell in worksheet.cells:

            row = cell.row_number - 1
            column = (
                cell.column_number - 1
            )

            colour = (
                self._normalise_colour(
                    getattr(
                        cell,
                        "fill_colour",
                        "",
                    )
                )
            )

            if colour:

                try:

                    self.sheet_control.highlight_cells(
                        row=row,
                        column=column,
                        bg=colour,
                    )

                except Exception:
                    pass

    def _render_regions(self):

        worksheet_schema = (
            self.workbook_schema.get_worksheet(
                self.current_sheet_name
            )
        )

        if worksheet_schema is None:
            return

        for region in worksheet_schema.regions:

            if region.is_deleted:
                continue

            colour = (
                self._region_colour(
                    region
                )
            )

            for cell_reference in (
                region.region_range.iter_cell_references()
            ):

                row, column = (
                    self._cell_ref_to_indexes(
                        cell_reference
                    )
                )

                try:

                    self.sheet_control.highlight_cells(
                        row=row,
                        column=column,
                        bg=colour,
                    )

                except Exception:
                    pass

    # ==================================================
    # REGIONS
    # ==================================================

    def _load_regions(self):

        for item in self.region_tree.get_children():
            self.region_tree.delete(item)

        self.region_lookup.clear()

        worksheet_schema = (
            self.workbook_schema.get_worksheet(
                self.current_sheet_name
            )
        )

        if worksheet_schema is None:
            return

        for region in worksheet_schema.regions:

            if region.is_deleted:
                continue

            item = self.region_tree.insert(
                "",
                tk.END,
                values=(
                    region.address,
                    region.status,
                ),
            )

            self.region_lookup[
                item
            ] = region

    def _create_region(self):

        range_text = (
            simpledialog.askstring(
                "Create Region",
                (
                    "Enter range\n\n"
                    "Example:\n"
                    "A10:H55"
                ),
                parent=self.window,
            )
        )

        if not range_text:
            return

        if ":" not in range_text:

            messagebox.showerror(
                "Invalid Range",
                "Use A1:H50 format.",
            )

            return

        start_cell, end_cell = (
            range_text.split(":")
        )

        worksheet_schema = (
            self.workbook_schema.get_worksheet(
                self.current_sheet_name
            )
        )

        region = RegionSchema(
            region_name=(
                f"Region "
                f"{len(worksheet_schema.regions) + 1}"
            ),
            sheet_name=self.current_sheet_name,
            region_range=RangeSchema(
                sheet_name=self.current_sheet_name,
                start_cell=start_cell.strip(),
                end_cell=end_cell.strip(),
            ),
            detected_by_ai=False,
            user_created=True,
            user_confirmed=True,
            confidence=1.0,
        )

        worksheet_schema.add_region(
            region
        )

        self._load_regions()
        self._refresh_display()

    def _edit_region(self):

        region = (
            self._selected_region()
        )

        if region is None:
            return

        new_range = (
            simpledialog.askstring(
                "Edit Region",
                "Enter new range",
                initialvalue=region.address,
                parent=self.window,
            )
        )

        if not new_range:
            return

        if ":" not in new_range:
            return

        start_cell, end_cell = (
            new_range.split(":")
        )

        region.region_range = (
            RangeSchema(
                sheet_name=region.sheet_name,
                start_cell=start_cell.strip(),
                end_cell=end_cell.strip(),
            )
        )

        region.mark_modified()

        self._load_regions()
        self._refresh_display()

    def _delete_region(self):

        region = (
            self._selected_region()
        )

        if region is None:
            return

        region.mark_deleted()

        self._load_regions()
        self._refresh_display()

    def _confirm_region(self):

        region = (
            self._selected_region()
        )

        if region is None:
            return

        region.confirm()

        self._load_regions()

    def _selected_region(self):

        selection = (
            self.region_tree.selection()
        )

        if not selection:
            return None

        return self.region_lookup.get(
            selection[0]
        )

    # ==================================================
    # INSPECTOR
    # ==================================================

    def _cell_selected(
        self,
        event=None,
    ):
        try:

            selection = (
                self.sheet_control.get_currently_selected()
            )

            if not selection:
                return

            row = int(selection[0])
            column = int(selection[1])

            cell_ref = (
                self._indexes_to_cell_ref(
                    row,
                    column,
                )
            )

            cell = self.cell_lookup.get(
                cell_ref
            )

            if cell is None:
                return

            self._show_cell(
                cell
            )

        except Exception:
            pass

    def _show_cell(
        self,
        cell,
    ):
        self.inspector.delete(
            "1.0",
            tk.END,
        )

        lines = [
            f"Cell: {cell.cell_reference}",
            f"Value: {cell.value}",
            f"Fill: {getattr(cell, 'fill_colour', '')}",
            f"Font: {getattr(cell, 'font_name', '')}",
            f"Bold: {getattr(cell, 'bold', False)}",
            f"Italic: {getattr(cell, 'italic', False)}",
            f"Locked: {getattr(cell, 'is_locked', False)}",
            f"Merged: {getattr(cell, 'is_merged', False)}",
            f"Formula: {getattr(cell, 'has_formula', False)}",
            f"Format: {getattr(cell, 'number_format', '')}",
        ]

        self.inspector.insert(
            tk.END,
            "\n".join(lines),
        )

    def _region_selected(
        self,
        event=None,
    ):
        region = (
            self._selected_region()
        )

        if region is None:
            return

        self.inspector.delete(
            "1.0",
            tk.END,
        )

        self.inspector.insert(
            tk.END,
            (
                f"Region: {region.region_name}\n"
                f"Range: {region.address}\n"
                f"Status: {region.status}\n"
                f"Type: {region.region_type}\n"
                f"Fields: {region.field_count}\n"
                f"Confidence: {region.confidence}"
            ),
        )

    # ==================================================
    # HELPERS
    # ==================================================

    def _refresh_display(self):
        self._render_sheet()

    def _region_colour(
        self,
        region,
    ):
        if region.user_created:
            return "#D9EAD3"

        if region.user_modified:
            return "#FCE5CD"

        if region.user_confirmed:
            return "#D9EAD3"

        return "#CFE2F3"

    def _normalise_colour(
        self,
        colour,
    ):
        if not colour:
            return ""

        colour = str(colour).upper()

        if (
            len(colour) == 8
            and colour.startswith("FF")
        ):
            return "#" + colour[-6:]

        if len(colour) == 6:
            return "#" + colour

        return ""

    def _cell_ref_to_indexes(
        self,
        cell_reference,
    ):
        col_text = "".join(
            c
            for c in cell_reference
            if c.isalpha()
        )

        row_text = "".join(
            c
            for c in cell_reference
            if c.isdigit()
        )

        column = (
            self._column_to_number(
                col_text
            )
            - 1
        )

        row = int(row_text) - 1

        return row, column

    def _indexes_to_cell_ref(
        self,
        row,
        column,
    ):
        return (
            f"{self._number_to_column(column + 1)}"
            f"{row + 1}"
        )

    def _column_to_number(
        self,
        column_text,
    ):
        result = 0

        for character in column_text.upper():
            result = (
                result * 26
                + ord(character)
                - ord("A")
                + 1
            )

        return result

    def _number_to_column(
        self,
        number,
    ):
        result = ""

        while number > 0:

            number, remainder = divmod(
                number - 1,
                26,
            )

            result = (
                chr(65 + remainder)
                + result
            )

        return result

    # ==================================================
    # SAVE / CANCEL
    # ==================================================

    def _save(self):

        self.result = (
            self.workbook_schema
        )

        self.window.destroy()

    def _cancel(self):

        self.result = None

        self.window.destroy()