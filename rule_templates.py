# gui/mapping_editor_dialog.py

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk


class MappingEditorDialog:
    # Allows users to review and correct automatically detected workbook mappings.
    #
    # The dialog works with WorkbookSchema objects created by SchemaBuilder.
    # Users can update:
    # - field name
    # - data range
    # - confidence/user-defined flag
    #
    # The dialog edits the supplied schema object in memory and returns it when saved.

    def __init__(self, parent, workbook_schema):
        self.parent = parent
        self.workbook_schema = workbook_schema
        self.result = None

        self.region_lookup = []
        self.field_lookup = []

        self.window = tk.Toplevel(parent)
        self.window.title("Review Workbook Mappings")
        self.window.geometry("1000x650")
        self.window.transient(parent)
        self.window.grab_set()

        self.field_name_var = tk.StringVar()
        self.header_cell_var = tk.StringVar()
        self.data_range_var = tk.StringVar()
        self.detected_type_var = tk.StringVar()
        self.confidence_var = tk.StringVar()
        self.user_defined_var = tk.BooleanVar(value=False)

        self._build_ui()
        self._load_regions()

    def show(self):
        self.parent.wait_window(self.window)
        return self.result

    def _build_ui(self):
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(
            main_frame,
            text="Workbook Mapping Review",
            font=("Segoe UI", 14, "bold"),
        )
        title_label.pack(anchor="w", pady=(0, 10))

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        self._build_region_panel(content_frame)
        self._build_field_panel(content_frame)
        self._build_edit_panel(content_frame)
        self._build_button_panel(main_frame)

    def _build_region_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Detected Regions", padding=10)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.region_listbox = tk.Listbox(frame, height=20, exportselection=False)
        self.region_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(
            frame,
            orient=tk.VERTICAL,
            command=self.region_listbox.yview,
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.region_listbox.configure(yscrollcommand=scrollbar.set)
        self.region_listbox.bind("<<ListboxSelect>>", self._on_region_selected)

    def _build_field_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Mapped Fields", padding=10)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        self.field_listbox = tk.Listbox(frame, height=20, exportselection=False)
        self.field_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(
            frame,
            orient=tk.VERTICAL,
            command=self.field_listbox.yview,
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.field_listbox.configure(yscrollcommand=scrollbar.set)
        self.field_listbox.bind("<<ListboxSelect>>", self._on_field_selected)

    def _build_edit_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Edit Selected Field", padding=10)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        ttk.Label(frame, text="Field Name").grid(
            row=0,
            column=0,
            sticky="w",
            padx=5,
            pady=4,
        )
        ttk.Entry(frame, textvariable=self.field_name_var, width=35).grid(
            row=0,
            column=1,
            sticky="w",
            padx=5,
            pady=4,
        )

        ttk.Label(frame, text="Header Cell").grid(
            row=1,
            column=0,
            sticky="w",
            padx=5,
            pady=4,
        )
        ttk.Entry(frame, textvariable=self.header_cell_var, width=35).grid(
            row=1,
            column=1,
            sticky="w",
            padx=5,
            pady=4,
        )

        ttk.Label(frame, text="Data Range").grid(
            row=2,
            column=0,
            sticky="w",
            padx=5,
            pady=4,
        )
        ttk.Entry(frame, textvariable=self.data_range_var, width=35).grid(
            row=2,
            column=1,
            sticky="w",
            padx=5,
            pady=4,
        )

        ttk.Label(frame, text="Detected Type").grid(
            row=3,
            column=0,
            sticky="w",
            padx=5,
            pady=4,
        )
        ttk.Entry(frame, textvariable=self.detected_type_var, width=35).grid(
            row=3,
            column=1,
            sticky="w",
            padx=5,
            pady=4,
        )

        ttk.Label(frame, text="Confidence").grid(
            row=4,
            column=0,
            sticky="w",
        )