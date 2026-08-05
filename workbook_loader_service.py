# services/workbook_loader_service.py

from pathlib import Path

from parsers.workbook_parser import WorkbookParser


class WorkbookLoaderService:
    # Centralised workbook loading service.
    #
    # Responsibilities:
    # - Validate workbook file paths
    # - Validate supported Excel extensions
    # - Load files through WorkbookParser
    # - Provide a stable service for GUI and analysis layers
    #
    # This keeps workbook loading out of MainWindow and AnalysisService.

    SUPPORTED_EXTENSIONS = {
        ".xlsx",
        ".xls",
        ".xlsm",
    }

    def __init__(self, workbook_parser=None):
        if workbook_parser is None:
            workbook_parser = WorkbookParser()

        self.workbook_parser = workbook_parser

    def load_workbook(self, file_path):
        self.validate_file_path(file_path)
        return self.workbook_parser.load_workbook(file_path)

    def load_workbooks(self, file_paths):
        workbooks = []

        for file_path in file_paths:
            workbook = self.load_workbook(file_path)
            workbooks.append(workbook)

        return workbooks

    def load_named_workbooks(self, file_paths):
        named_workbooks = []

        for file_path in file_paths:
            workbook = self.load_workbook(file_path)
            supplier_name = self.get_workbook_name(file_path)
            named_workbooks.append((supplier_name, workbook))

        return named_workbooks

    def validate_file_path(self, file_path):
        if file_path is None:
            raise ValueError("No workbook file path provided.")

        path = Path(file_path)

        if str(path).strip() == "":
            raise ValueError("No workbook file path provided.")

        if not path.exists():
            raise FileNotFoundError(f"Workbook file not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Workbook path is not a file: {file_path}")

        extension = path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                "Unsupported workbook file type: "
                f"{extension}. Supported types are: "
                f"{', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
            )

    def is_supported_file(self, file_path):
        if file_path is None:
            return False

        extension = Path(file_path).suffix.lower()
        return extension in self.SUPPORTED_EXTENSIONS

    def filter_supported_files(self, file_paths):
        supported_files = []

        for file_path in file_paths:
            if self.is_supported_file(file_path):
                supported_files.append(file_path)

        return supported_files

    def get_workbook_name(self, file_path):
        return Path(file_path).stem

    def get_display_name(self, file_path):
        return Path(file_path).name