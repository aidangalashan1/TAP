# models/workbook_models.py

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CellInfo:
    """
    Normalised representation of a worksheet cell.
    """

    sheet_name: str
    cell_reference: str

    row_number: int
    column_number: int

    value: Any = None

    formula: str | None = None

    fill_colour: str | None = None

    is_mandatory: bool = False
    is_protected: bool = False

    is_hidden_row: bool = False
    is_hidden_column: bool = False

    comment_text: str | None = None

    data_type: str | None = None


@dataclass
class WorksheetInfo:
    """
    Represents a single worksheet and all cells within it.
    """

    worksheet_name: str

    is_hidden: bool = False

    cells: list[CellInfo] = field(default_factory=list)

    def add_cell(
        self,
        cell: CellInfo
    ) -> None:
        """
        Add a cell to the worksheet.
        """

        self.cells.append(cell)

    def get_cell(
        self,
        cell_reference: str
    ) -> CellInfo | None:
        """
        Retrieve a cell by reference.
        Example:
            A1
            H127
        """

        for cell in self.cells:

            if cell.cell_reference == cell_reference:
                return cell

        return None

    def get_mandatory_cells(self) -> list:
        """
        Return all mandatory cells.
        """

        return [
            cell
            for cell in self.cells
            if cell.is_mandatory
        ]

    def get_formula_cells(self) -> list:
        """
        Return all cells containing formulas.
        """

        return [
            cell
            for cell in self.cells
            if cell.formula is not None
        ]

    def get_used_cells(self) -> list:
        """
        Return all populated cells.
        """

        return [
            cell
            for cell in self.cells
            if cell.value is not None
        ]


@dataclass
class WorkbookInfo:
    """
    Represents an entire workbook.
    """

    file_name: str
    file_path: str

    worksheets: dict[str, WorksheetInfo] = field(
        default_factory=dict
    )

    def add_worksheet(
        self,
        worksheet: WorksheetInfo
    ) -> None:
        """
        Add worksheet to workbook.
        """

        self.worksheets[
            worksheet.worksheet_name
        ] = worksheet

    def get_worksheet(
        self,
        worksheet_name: str
    ) -> WorksheetInfo | None:
        """
        Retrieve worksheet by name.
        """

        return self.worksheets.get(
            worksheet_name
        )

    def get_all_cells(self) -> list:
        """
        Return all cells across all worksheets.
        """

        all_cells: list[CellInfo] = []

        for worksheet in self.worksheets.values():
            all_cells.extend(
                worksheet.cells
            )

        return all_cells

    def get_mandatory_cells(self) -> list:
        """
        Return all mandatory cells across workbook.
        """

        return [
            cell
            for cell in self.get_all_cells()
            if cell.is_mandatory
        ]

    def get_formula_cells(self) -> list:
        """
        Return all formula cells across workbook.
        """

        return [
            cell
            for cell in self.get_all_cells()
            if cell.formula is not None
        ]

    @property
    def worksheet_count(self) -> int:
        """
        Number of worksheets.
        """

        return len(self.worksheets)

    @property
    def total_cell_count(self) -> int:
        """
        Total number of cells.
        """

        return sum(
            len(worksheet.cells)
            for worksheet in self.worksheets.values()
        )