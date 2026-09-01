# gui/mapping_profile_dialog.py

import tkinter as tk
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import ttk

from services.mapping_profile_service import (
    MappingProfileService,
)


class MappingProfileDialog:
    """
    Save, load and delete mapping profiles.

    Intended workflow:

        Review Mapping
                ↓
        Save Profile
                ↓
        Reuse Next Tender

    Returns:

        {
            "action": "load",
            "profile_name": "...",
            "profile_data": {...}
        }

    or

        {
            "action": "save",
            "profile_name": "..."
        }

    or

        None
    """

    def __init__(
        self,
        parent,
        workbook_schema=None,
        mapping_profile_service=None,
    ):
        self.parent = parent
        self.workbook_schema = workbook_schema

        self.mapping_profile_service = (
            mapping_profile_service
            or MappingProfileService()
        )

        self.result = None

        self.window = tk.Toplevel(parent)
        self.window.title("Mapping Profiles")
        self.window.geometry("700x500")

        self.window.transient(parent)
        self.window.grab_set()

        self.profile_lookup = []

        self._build_ui()
        self._load_profiles()

    # ==================================================
    # Public
    # ==================================================

    def show(self):
        self.parent.wait_window(
            self.window
        )

        return self.result

    # ==================================================
    # UI
    # ==================================================

    def _build_ui(self):
        main_frame = ttk.Frame(
            self.window,
            padding=10,
        )

        main_frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        title = ttk.Label(
            main_frame,
            text="Mapping Profiles",
            font=("Segoe UI", 14, "bold"),
        )

        title.pack(
            anchor="w",
            pady=(0, 10),
        )

        content_frame = ttk.Frame(
            main_frame
        )

        content_frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self._build_profile_list(
            content_frame
        )

        self._build_profile_preview(
            content_frame
        )

        self._build_buttons(
            main_frame
        )

    def _build_profile_list(
        self,
        parent,
    ):
        frame = ttk.LabelFrame(
            parent,
            text="Profiles",
            padding=10,
        )

        frame.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=False,
        )

        self.profile_listbox = tk.Listbox(
            frame,
            width=35,
            exportselection=False,
        )

        self.profile_listbox.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
        )

        self.profile_listbox.bind(
            "<<ListboxSelect>>",
            self._profile_selected,
        )

        scrollbar = ttk.Scrollbar(
            frame,
            orient=tk.VERTICAL,
            command=self.profile_listbox.yview,
        )

        scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y,
        )

        self.profile_listbox.config(
            yscrollcommand=scrollbar.set
        )

    def _build_profile_preview(
        self,
        parent,
    ):
        frame = ttk.LabelFrame(
            parent,
            text="Profile Details",
            padding=10,
        )

        frame.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
            padx=(10, 0),
        )

        self.preview_text = tk.Text(
            frame,
            wrap="word",
        )

        self.preview_text.pack(
            fill=tk.BOTH,
            expand=True,
        )

    def _build_buttons(
        self,
        parent,
    ):
        frame = ttk.Frame(parent)

        frame.pack(
            fill=tk.X,
            pady=(10, 0),
        )

        ttk.Button(
            frame,
            text="Save Current Mapping",
            command=self._save_profile,
        ).pack(
            side=tk.LEFT,
            padx=5,
        )

        ttk.Button(
            frame,
            text="Load Profile",
            command=self._load_selected_profile,
        ).pack(
            side=tk.LEFT,
            padx=5,
        )

        ttk.Button(
            frame,
            text="Delete Profile",
            command=self._delete_profile,
        ).pack(
            side=tk.LEFT,
            padx=5,
        )

        ttk.Button(
            frame,
            text="Close",
            command=self._close,
        ).pack(
            side=tk.RIGHT,
            padx=5,
        )

    # ==================================================
    # Profile Loading
    # ==================================================

    def _load_profiles(self):
        self.profile_lookup.clear()

        self.profile_listbox.delete(
            0,
            tk.END,
        )

        profiles = (
            self.mapping_profile_service.list_profiles()
        )

        for profile in profiles:
            self.profile_lookup.append(
                profile
            )

            self.profile_listbox.insert(
                tk.END,
                profile,
            )

    def _profile_selected(
        self,
        event=None,
    ):
        profile_name = (
            self._selected_profile()
        )

        if profile_name is None:
            return

        profile_data = (
            self.mapping_profile_service.load_profile(
                profile_name
            )
        )

        self._show_preview(
            profile_data
        )

    # ==================================================
    # Save
    # ==================================================

    def _save_profile(self):
        if self.workbook_schema is None:

            messagebox.showwarning(
                "No Mapping",
                (
                    "Review a workbook mapping "
                    "before saving a profile."
                ),
            )

            return

        profile_name = (
            simpledialog.askstring(
                "Profile Name",
                "Enter profile name:",
                parent=self.window,
            )
        )

        if not profile_name:
            return

        if profile_name in self.mapping_profile_service.list_profiles():

            overwrite = messagebox.askyesno(
                "Profile Already Exists",
                (
                    f"A profile named '{profile_name}' already "
                    "exists. Overwrite it?"
                ),
            )

            if not overwrite:
                return

        self.mapping_profile_service.save_profile(
            profile_name,
            self.workbook_schema,
        )

        self._load_profiles()

        messagebox.showinfo(
            "Saved",
            (
                f"Profile '{profile_name}' "
                "saved successfully."
            ),
        )

    # ==================================================
    # Load
    # ==================================================

    def _load_selected_profile(self):
        profile_name = (
            self._selected_profile()
        )

        if profile_name is None:
            return

        profile_data = (
            self.mapping_profile_service.load_profile(
                profile_name
            )
        )

        self.result = {
            "action": "load",
            "profile_name": profile_name,
            "profile_data": profile_data,
        }

        self.window.destroy()

    # ==================================================
    # Delete
    # ==================================================

    def _delete_profile(self):
        profile_name = (
            self._selected_profile()
        )

        if profile_name is None:
            return

        confirmed = messagebox.askyesno(
            "Delete Profile",
            (
                f"Delete profile "
                f"'{profile_name}'?"
            ),
        )

        if not confirmed:
            return

        self.mapping_profile_service.delete_profile(
            profile_name
        )

        self._load_profiles()

        self.preview_text.delete(
            "1.0",
            tk.END,
        )

    # ==================================================
    # Helpers
    # ==================================================

    def _selected_profile(self):
        selection = (
            self.profile_listbox.curselection()
        )

        if not selection:
            return None

        return self.profile_lookup[
            selection[0]
        ]

    def _show_preview(
        self,
        profile_data,
    ):
        self.preview_text.delete(
            "1.0",
            tk.END,
        )

        if profile_data is None:
            return

        workbook_name = profile_data.get(
            "workbook_name",
            "",
        )

        self.preview_text.insert(
            tk.END,
            f"Workbook: {workbook_name}\n\n",
        )

        input_areas = profile_data.get(
            "input_areas",
            {},
        )

        for area_key, area_data in input_areas.items():

            sheet_name = area_data.get(
                "sheet_name",
                "",
            )

            start_cell = area_data.get(
                "start_cell",
                "",
            )

            end_cell = area_data.get(
                "end_cell",
                "",
            )

            confirmed = area_data.get(
                "user_confirmed",
                False,
            )

            self.preview_text.insert(
                tk.END,
                (
                    f"{area_key}\n"
                    f"  Sheet: {sheet_name}\n"
                    f"  Range: {start_cell}:{end_cell}\n"
                    f"  Confirmed: {confirmed}\n\n"
                ),
            )

    def _close(self):
        self.window.destroy()