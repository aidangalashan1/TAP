# gui/workbook_mapper_dialog.py

import tkinter as tk
from tkinter import ttk
from tkinter import simpledialog

try:
    from tksheet import Sheet
except ImportError:
    Sheet = None

from schema.workbook_schema import (
    InputArea,
    RangeSchema,
)


class WorkbookMapperDialog:
    """
    Lets the user review the automatically detected input zones and
    correct them by dragging a selection over cells in the grid and
    applying a tool:

        Detected (yellow)  - a candidate zone, not yet reviewed
        Confirmed (green)  - reviewed and correct, used for analysis
        Removed (red)      - reviewed and rejected, kept for audit
        Ignored (black)    - not an input zone at all (headers, notes,
                              blank formatting, etc.)

    Every cell in the sheet is coloured by its status when "Show Input
    Areas" is on, so the whole grid - not just the detected patches -
    shows what will and won't be read during analysis.
    """

    TOOLS = {
        "Detected (Yellow)": "detected",
        "Confirmed (Green)": "confirmed",
        "Removed (Red)": "removed",
        "Ignored (Black)": "ignored",
    }

    STATUS_COLOURS = {
        "detected": "#FFF2A8",
        "confirmed": "#93C47D",
        "removed": "#E06666",
        "ignored": "#434343",
    }

    def __init__(
        self,
        parent,
        workbook,
        workbook_schema,
        benchmark_workbook=None,
    ):
        self.parent = parent
        self.workbook = workbook
        self.workbook_schema = workbook_schema
        self.benchmark_workbook = benchmark_workbook

        self.result = None

        self.current_sheet_name = None

        self.input_area_lookup = {}
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
        self.input_area_tree = None
        self.inspector = None

        self.show_input_areas_var = tk.BooleanVar(
            value=True
        )

        self.show_formatting_var = tk.BooleanVar(
            value=False
        )

        self.show_benchmark_var = tk.BooleanVar(
            value=False
        )

        self.tool_var = tk.StringVar(
            value=list(self.TOOLS.keys())[1]
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
        self._build_input_area_panel(right)
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

        ttk.Label(
            frame,
            text=(
                "Drag to select cells in the grid, choose a zone type "
                "below, then click Apply. Yellow = detected but not "
                "reviewed, green = confirmed input, red = removed, "
                "black = ignored / not an input cell. Tick 'Show "
                "Benchmark Rates' to overlay the matching benchmark "
                "value under each cell (requires a benchmark workbook "
                "loaded in Step 2)."
            ),
            wraplength=1000,
        ).pack(anchor="w", padx=5, pady=(0, 5))

        tool_row = ttk.Frame(frame)
        tool_row.pack(fill=tk.X)

        ttk.Label(
            tool_row,
            text="Zone type:",
        ).pack(side=tk.LEFT, padx=(5, 5))

        tool_combo = ttk.Combobox(
            tool_row,
            textvariable=self.tool_var,
            values=list(self.TOOLS.keys()),
            state="readonly",
            width=20,
        )

        tool_combo.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            tool_row,
            text="Apply to Selection",
            command=self._apply_tool_to_selection,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Checkbutton(
            tool_row,
            text="Show Input Areas",
            variable=self.show_input_areas_var,
            command=self._refresh_display,
        ).pack(
            side=tk.LEFT,
            padx=(20, 5),
        )

        ttk.Checkbutton(
            tool_row,
            text="Show Original Formatting",
            variable=self.show_formatting_var,
            command=self._refresh_display,
        ).pack(
            side=tk.LEFT,
            padx=5,
        )

        benchmark_checkbox = ttk.Checkbutton(
            tool_row,
            text="Show Benchmark Rates",
            variable=self.show_benchmark_var,
            command=self._refresh_display,
        )

        benchmark_checkbox.pack(
            side=tk.LEFT,
            padx=5,
        )

        if self.benchmark_workbook is None:
            benchmark_checkbox.configure(state="disabled")

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

        self.expect_discrepancies_var = tk.BooleanVar(value=False)

        ttk.Checkbutton(
            frame,
            text="Discrepancies expected on this sheet",
            variable=self.expect_discrepancies_var,
            command=self._toggle_expect_discrepancies,
        ).pack(
            anchor="w",
            pady=(5, 0),
        )

    def _toggle_expect_discrepancies(self):
        if self.current_sheet_name is None:
            return

        worksheet_schema = self.workbook_schema.get_worksheet(
            self.current_sheet_name
        )

        if worksheet_schema is None:
            return

        worksheet_schema.expect_discrepancies = (
            self.expect_discrepancies_var.get()
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

    def _build_input_area_panel(
        self,
        parent,
    ):
        frame = ttk.LabelFrame(
            parent,
            text="Input Areas",
            padding=5,
        )

        frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self.input_area_tree = ttk.Treeview(
            frame,
            columns=(
                "range",
                "status",
            ),
            show="headings",
            height=18,
        )

        self.input_area_tree.heading(
            "range",
            text="Range",
        )

        self.input_area_tree.heading(
            "status",
            text="Status",
        )

        self.input_area_tree.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self.input_area_tree.bind(
            "<<TreeviewSelect>>",
            self._input_area_selected,
        )

        ttk.Button(
            frame,
            text="Edit Range...",
            command=self._edit_input_area,
        ).pack(
            fill=tk.X,
            pady=2,
        )

        ttk.Button(
            frame,
            text="Restore to Detected",
            command=self._restore_input_area,
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
        self._load_input_areas()
        self._refresh_expect_discrepancies_checkbox()

    def _refresh_expect_discrepancies_checkbox(self):
        worksheet_schema = self.workbook_schema.get_worksheet(
            self.current_sheet_name
        )

        self.expect_discrepancies_var.set(
            bool(worksheet_schema.expect_discrepancies)
            if worksheet_schema is not None
            else False
        )

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

        overlay_benchmark = (
            self.show_benchmark_var.get()
            and self.benchmark_workbook is not None
        )

        benchmark_lookup = (
            self._build_benchmark_lookup()
            if overlay_benchmark
            else {}
        )

        for cell in worksheet.cells:

            self.cell_lookup[
                cell.cell_reference
            ] = cell

            display_value = (
                ""
                if cell.value is None
                else str(cell.value)
            )

            if overlay_benchmark:

                benchmark_value = benchmark_lookup.get(
                    cell.cell_reference
                )

                if benchmark_value is not None:
                    display_value = (
                        f"{display_value} | Bench: {benchmark_value}"
                        if display_value
                        else f"Bench: {benchmark_value}"
                    )

            data[
                cell.row_number - 1
            ][
                cell.column_number - 1
            ] = display_value

        self.sheet_control.set_sheet_data(
            data
        )

        if self.show_formatting_var.get():
            self._apply_formatting(
                worksheet
            )

        if self.show_input_areas_var.get():
            self._render_input_areas(
                worksheet
            )

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

    def _render_input_areas(self, worksheet):
        """
        Colour every used cell in the sheet by its input-area status,
        including cells that aren't part of any area at all (ignored/
        irrelevant, shown black) - not just the detected patches.
        """

        worksheet_schema = (
            self.workbook_schema.get_worksheet(
                self.current_sheet_name
            )
        )

        if worksheet_schema is None:
            return

        input_areas = worksheet_schema.get_all_input_areas()

        for cell in worksheet.cells:

            status = self._status_for_cell(
                cell.cell_reference, input_areas
            )

            colour = self.STATUS_COLOURS.get(status)

            if colour is None:
                continue

            row = cell.row_number - 1
            column = cell.column_number - 1

            try:

                self.sheet_control.highlight_cells(
                    row=row,
                    column=column,
                    bg=colour,
                )

            except Exception:
                pass

    def _status_for_cell(self, cell_reference, input_areas):
        best = None

        for input_area in input_areas:

            if not input_area.contains_cell(cell_reference):
                continue

            if input_area.is_deleted:
                return "removed"

            if input_area.is_ignored:
                best = best or "ignored"
                continue

            if (
                input_area.user_confirmed
                or input_area.user_created
            ):
                return "confirmed"

            best = best or "detected"

        return best or "ignored"

    # ==================================================
    # TOOLS (click-and-drag zone assignment)
    # ==================================================

    def _apply_tool_to_selection(self):

        if self.current_sheet_name is None:
            return

        selection_range = self._get_selection_range()

        if selection_range is None:
            return

        tool = self.TOOLS.get(self.tool_var.get())

        if tool is None:
            return

        worksheet_schema = (
            self.workbook_schema.get_worksheet(
                self.current_sheet_name
            )
        )

        if worksheet_schema is None:
            return

        overlapping = [
            input_area
            for input_area in worksheet_schema.get_all_input_areas()
            if input_area.area_range.intersects(selection_range)
        ]

        if overlapping:

            for input_area in overlapping:
                self._apply_status(input_area, tool)

        else:

            input_area = InputArea(
                area_name=(
                    f"{self.current_sheet_name}!"
                    f"{selection_range.address}"
                ),
                sheet_name=self.current_sheet_name,
                area_range=selection_range,
                detected_by_ai=False,
                confidence=1.0,
            )

            self._apply_status(input_area, tool)

            worksheet_schema.add_input_area(input_area)

        self._load_input_areas()
        self._refresh_display()

        try:
            # Clear the selection so it can't be accidentally reused
            # (e.g. accumulated with a later ctrl+drag) by the next
            # tool application.
            self.sheet_control.deselect()
        except Exception:
            pass

    def _apply_status(self, input_area, tool):
        if tool == "confirmed":
            input_area.confirm()

        elif tool == "removed":
            input_area.mark_deleted()

        elif tool == "ignored":
            input_area.mark_ignored()

        elif tool == "detected":
            input_area.restore()
            input_area.user_confirmed = False
            input_area.user_created = False

    def _get_selection_range(self):
        """
        Reads the current drag-selected cell rectangle from the grid
        and converts it to a RangeSchema. Returns None if nothing (or
        an unusable single point) is selected.
        """

        if Sheet is None or self.sheet_control is None:
            return None

        try:
            min_row, min_col, max_row, max_col = (
                self.sheet_control.get_selected_min_max()
            )
        except Exception:
            return None

        if min_row is None:
            return None

        # tksheet's max bound is exclusive.
        start_cell = self._indexes_to_cell_ref(min_row, min_col)
        end_cell = self._indexes_to_cell_ref(max_row - 1, max_col - 1)

        return RangeSchema(
            sheet_name=self.current_sheet_name,
            start_cell=start_cell,
            end_cell=end_cell,
        )

    # ==================================================
    # INPUT AREAS
    # ==================================================

    def _load_input_areas(self):

        for item in self.input_area_tree.get_children():
            self.input_area_tree.delete(item)

        self.input_area_lookup.clear()

        worksheet_schema = (
            self.workbook_schema.get_worksheet(
                self.current_sheet_name
            )
        )

        if worksheet_schema is None:
            return

        for input_area in worksheet_schema.get_all_input_areas():

            item = self.input_area_tree.insert(
                "",
                tk.END,
                values=(
                    input_area.address,
                    input_area.status,
                ),
            )

            self.input_area_lookup[
                item
            ] = input_area

    def _edit_input_area(self):

        input_area = (
            self._selected_input_area()
        )

        if input_area is None:
            return

        new_range = (
            simpledialog.askstring(
                "Edit Input Area",
                "Enter new range",
                initialvalue=input_area.address,
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

        input_area.area_range = (
            RangeSchema(
                sheet_name=input_area.sheet_name,
                start_cell=start_cell.strip(),
                end_cell=end_cell.strip(),
            )
        )

        input_area.mark_modified()

        self._load_input_areas()
        self._refresh_display()

    def _restore_input_area(self):

        input_area = (
            self._selected_input_area()
        )

        if input_area is None:
            return

        input_area.restore()
        input_area.user_confirmed = False
        input_area.user_created = False
        input_area.user_modified = False

        self._load_input_areas()
        self._refresh_display()

    def _selected_input_area(self):

        selection = (
            self.input_area_tree.selection()
        )

        if not selection:
            return None

        return self.input_area_lookup.get(
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

        if self.benchmark_workbook is not None:

            benchmark_value = self._benchmark_value_for_cell(
                cell.cell_reference
            )

            lines.append(
                "Benchmark Rate: "
                + (
                    "(no matching benchmark cell)"
                    if benchmark_value is None
                    else str(benchmark_value)
                )
            )

        self.inspector.insert(
            tk.END,
            "\n".join(lines),
        )

    def _benchmark_value_for_cell(
        self,
        cell_reference,
    ):
        """
        Looks up the value at the same sheet name / cell reference in
        the benchmark workbook, so the user can validate the rate that
        will be used for benchmark comparison against this cell.
        """
        return self._build_benchmark_lookup().get(cell_reference)

    def _build_benchmark_lookup(self):
        """
        Maps cell_reference -> value for every cell on the current
        sheet in the benchmark workbook, so the grid overlay and the
        inspector can both look up a cell's benchmark rate without
        re-scanning the benchmark worksheet per cell.
        """
        if self.benchmark_workbook is None:
            return {}

        benchmark_worksheet = (
            self.benchmark_workbook.get_worksheet(
                self.current_sheet_name
            )
        )

        if benchmark_worksheet is None:
            return {}

        return {
            benchmark_cell.cell_reference: benchmark_cell.value
            for benchmark_cell in benchmark_worksheet.cells
            if benchmark_cell.value is not None
        }

    def _input_area_selected(
        self,
        event=None,
    ):
        input_area = (
            self._selected_input_area()
        )

        if input_area is None:
            return

        self.inspector.delete(
            "1.0",
            tk.END,
        )

        self.inspector.insert(
            tk.END,
            (
                f"Input Area: {input_area.area_name}\n"
                f"Range: {input_area.address}\n"
                f"Status: {input_area.status}\n"
                f"Confidence: {input_area.confidence}\n"
                f"Detected by AI: {input_area.detected_by_ai}"
            ),
        )

    # ==================================================
    # HELPERS
    # ==================================================

    def _refresh_display(self):
        self._render_sheet()

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

    def _indexes_to_cell_ref(
        self,
        row,
        column,
    ):
        return (
            f"{self._number_to_column(column + 1)}"
            f"{row + 1}"
        )

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
