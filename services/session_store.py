# services/session_store.py

import json
from pathlib import Path

import config


class SessionStore:
    """
    Persists the file paths (template, benchmark, supplier workbooks,
    output folder) the user last had loaded, so closing and reopening
    the app doesn't mean reselecting every file from scratch.

    Deliberately stores paths only, not workbook contents or the
    built schema - those are rebuilt from the files on resume, and
    mapping profiles/rules already have their own persistence.
    """

    def __init__(self, file_path=None):
        if file_path is None:
            file_path = config.SESSION_FILE_PATH

        self.file_path = Path(file_path)

    def load(self):
        if not self.file_path.exists():
            return None

        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return None

    def save(self, session_data):
        parent = self.file_path.parent

        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)

        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(session_data, file, indent=4)

    def clear(self):
        if self.file_path.exists():
            self.file_path.unlink()
