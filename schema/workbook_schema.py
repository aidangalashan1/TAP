# schema/workbook_schema.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FieldDataType(str, Enum):
    UNKNOWN = "UNKNOWN"
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    DATE = "DATE"
    BOOLEAN = "BOOLEAN"
    FORMULA = "FORMULA"


class FieldRole(str, Enum):
    UNKNOWN = "UNKNOWN"
    IDENTIFIER = "IDENTIFIER"
    DESCRIPTION = "DESCRIPTION"
    PRICE = "PRICE"
    QUANTITY = "QUANTITY"
    BENCHMARK = "BENCHMARK"
    DATE = "DATE"
    CATEGORY = "CATEGORY"
    NOTE = "NOTE"
    TOTAL = "TOTAL"
    INPUT = "INPUT"


class RangeOrientation(str, Enum):
    UNKNOWN = "UNKNOWN"
    SINGLE_CELL = "SINGLE_CELL"
    VERTICAL = "VERTICAL"
    HORIZONTAL = "HORIZONTAL"
    BLOCK = "BLOCK"


class RegionOrientation(str, Enum):
    UNKNOWN = "UNKNOWN"
    TABLE = "TABLE"
    VERTICAL_RANGE = "VERTICAL_RANGE"
    HORIZONTAL_RANGE = "HORIZONTAL_RANGE"
    CELL_BLOCK = "CELL_BLOCK"
    SINGLE_CELL = "SINGLE_CELL"


class InputAreaStatus(str, Enum):
    DETECTED = "DETECTED"
    CONFIRMED = "CONFIRMED"
    USER_CREATED = "USER_CREATED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"


@dataclass
class RangeSchema:
    sheet_name: str
    start_cell: str
    end_cell: str
    orientation: RangeOrientation = RangeOrientation.UNKNOWN
    user_defined: bool = False

    def __post_init__(self) -> None:
        self.start_cell = str(self.start_cell).strip().upper()
        self.end_cell = str(self.end_cell).strip().upper()

        if self.orientation == RangeOrientation.UNKNOWN:
            self.orientation = self.detect_orientation()

    @property
    def address(self) -> str:
        return f"{self.start_cell}:{self.end_cell}"

    @property
    def start_row(self) -> int:
        return self._row(self.start_cell)

    @property
    def end_row(self) -> int:
        return self._row(self.end_cell)

    @property
    def start_column(self) -> int:
        return self._column_number(self._column_text(self.start_cell))

    @property
    def end_column(self) -> int:
        return self._column_number(self._column_text(self.end_cell))

    @property
    def min_row(self) -> int:
        return min(self.start_row, self.end_row)

    @property
    def max_row(self) -> int:
        return max(self.start_row, self.end_row)

    @property
    def min_column(self) -> int:
        return min(self.start_column, self.end_column)

    @property
    def max_column(self) -> int:
        return max(self.start_column, self.end_column)

    @property
    def width(self) -> int:
        return self.max_column - self.min_column + 1

    @property
    def height(self) -> int:
        return self.max_row - self.min_row + 1

    def detect_orientation(self) -> RangeOrientation:
        if self.start_row == self.end_row and self.start_column == self.end_column:
            return RangeOrientation.SINGLE_CELL

        if self.start_row == self.end_row:
            return RangeOrientation.HORIZONTAL

        if self.start_column == self.end_column:
            return RangeOrientation.VERTICAL

        return RangeOrientation.BLOCK

    def contains(self, cell_reference: str) -> bool:
        row = self._row(cell_reference)
        column = self._column_number(self._column_text(cell_reference))

        return (
            self.min_row <= row <= self.max_row
            and self.min_column <= column <= self.max_column
        )

    def iter_cell_references(self) -> list:
        references = []

        for row in range(self.min_row, self.max_row + 1):
            for column in range(self.min_column, self.max_column + 1):
                references.append(f"{self._number_to_column(column)}{row}")

        return references

    @staticmethod
    def _row(cell_reference: str) -> int:
        digits = "".join(
            character
            for character in str(cell_reference)
            if character.isdigit()
        )

        return int(digits) if digits else 0

    @staticmethod
    def _column_text(cell_reference: str) -> str:
        return "".join(
            character
            for character in str(cell_reference)
            if character.isalpha()
        ).upper()

    @staticmethod
    def _column_number(column_text: str) -> int:
        result = 0

        for character in str(column_text).upper():
            result = result * 26 + ord(character) - ord("A") + 1

        return result

    @staticmethod
    def _number_to_column(number: int) -> str:
        result = ""

        while number > 0:
            number, remainder = divmod(number - 1, 26)
            result = chr(65 + remainder) + result

        return result


@dataclass
class FieldSchema:
    field_name: str
    sheet_name: str
    field_range: RangeSchema | None = None
    header_range: RangeSchema | None = None
    role: FieldRole = FieldRole.UNKNOWN
    data_type: FieldDataType = FieldDataType.UNKNOWN
    confidence: float = 0.0
    input_confidence: float = 0.0
    is_input_field: bool = False
    user_defined: bool = False

    @property
    def data_range(self) -> str | None:
        if self.field_range is None:
            return None

        return self.field_range.address

    @property
    def header_cell(self) -> str | None:
        if self.header_range is None:
            return None

        return self.header_range.start_cell


@dataclass
class InputArea:
    area_name: str
    sheet_name: str
    area_range: RangeSchema
    confidence: float = 0.0
    detected_by_ai: bool = True
    user_confirmed: bool = False
    user_created: bool = False
    user_modified: bool = False
    is_deleted: bool = False
    visible: bool = True
    colour: str = "#D9EAD3"
    notes: str = ""

    @property
    def address(self) -> str:
        return self.area_range.address

    @property
    def status(self) -> str:
        if self.is_deleted:
            return InputAreaStatus.DELETED.value

        if self.user_created:
            return InputAreaStatus.USER_CREATED.value

        if self.user_modified:
            return InputAreaStatus.MODIFIED.value

        if self.user_confirmed:
            return InputAreaStatus.CONFIRMED.value

        return InputAreaStatus.DETECTED.value

    def contains_cell(self, cell_reference: str) -> bool:
        return self.area_range.contains(cell_reference)

    def confirm(self) -> None:
        self.user_confirmed = True

    def mark_modified(self) -> None:
        self.user_modified = True

    def mark_deleted(self) -> None:
        self.is_deleted = True

    def restore(self) -> None:
        self.is_deleted = False


@dataclass
class RegionSchema:
    region_name: str
    sheet_name: str
    region_range: RangeSchema
    header_range: RangeSchema | None = None
    orientation: RegionOrientation = RegionOrientation.UNKNOWN
    confidence: float = 0.0
    detected_by_ai: bool = True
    user_confirmed: bool = False
    user_created: bool = False
    user_modified: bool = False
    is_deleted: bool = False
    colour: str = "#4F81BD"
    visible: bool = True
    region_type: str = "TABLE"
    fields: list[FieldSchema] = field(default_factory=list)
    notes: str = ""

    @property
    def address(self) -> str:
        return self.region_range.address

    @property
    def field_count(self) -> int:
        return len(self.fields)

    @property
    def status(self) -> str:
        if self.is_deleted:
            return "DELETED"

        if self.user_created:
            return "USER_CREATED"

        if self.user_modified:
            return "MODIFIED"

        if self.user_confirmed:
            return "CONFIRMED"

        return "DETECTED"

    def add_field(self, field_schema: FieldSchema) -> None:
        self.fields.append(field_schema)

    def remove_field(self, field_name: str) -> None:
        self.fields = [
            field
            for field in self.fields
            if field.field_name != field_name
        ]

    def contains_cell(self, cell_reference: str) -> bool:
        return self.region_range.contains(cell_reference)

    def confirm(self) -> None:
        self.user_confirmed = True

    def mark_modified(self) -> None:
        self.user_modified = True

    def mark_deleted(self) -> None:
        self.is_deleted = True

    def restore(self) -> None:
        self.is_deleted = False


@dataclass
class WorksheetSchema:
    sheet_name: str
    regions: list[RegionSchema] = field(default_factory=list)
    input_areas: list[InputArea] = field(default_factory=list)

    def add_region(self, region_schema: RegionSchema) -> None:
        self.regions.append(region_schema)

    def add_input_area(self, input_area: InputArea) -> None:
        self.input_areas.append(input_area)

    def get_all_fields(self) -> list:
        fields = []

        for region in self.regions:
            fields.extend(region.fields)

        return fields

    def get_active_input_areas(self) -> list:
        return [
            input_area
            for input_area in self.input_areas
            if not input_area.is_deleted
        ]


@dataclass
class WorkbookSchema:
    workbook_name: str
    workbook_path: str
    worksheets: dict[str, WorksheetSchema] = field(default_factory=dict)

    def add_worksheet(self, worksheet_schema: WorksheetSchema) -> None:
        self.worksheets[worksheet_schema.sheet_name] = worksheet_schema

    def get_worksheet(self, sheet_name: str) -> WorksheetSchema | None:
        return self.worksheets.get(sheet_name)

    def get_all_regions(self) -> list:
        regions = []

        for worksheet in self.worksheets.values():
            regions.extend(worksheet.regions)

        return regions

    def get_all_fields(self) -> list:
        fields = []

        for worksheet in self.worksheets.values():
            fields.extend(worksheet.get_all_fields())

        return fields

    def get_input_areas(self) -> list:
        input_areas = []

        for worksheet in self.worksheets.values():
            input_areas.extend(worksheet.get_active_input_areas())

        return input_areas

    def get_confirmed_input_areas(self) -> list:
        return [
            input_area
            for input_area in self.get_input_areas()
            if input_area.user_confirmed or input_area.user_created
        ]

    def get_unique_field_names(self) -> list:
        names = set()

        for field_schema in self.get_all_fields():
            if field_schema.field_name:
                names.add(field_schema.field_name)

        return sorted(names)


@dataclass
class DataRecord:
    sheet_name: str
    region_name: str
    record_reference: str = ""
    values: dict[str, Any] = field(default_factory=dict)
    cell_references: dict[str, str] = field(default_factory=dict)

    def set_value(self, field_name: str, value: Any, cell_reference: str) -> None:
        self.values[field_name] = value
        self.cell_references[field_name] = cell_reference

    def get_value(self, field_name: str) -> Any:
        return self.values.get(field_name)

    def get_cell_reference(self, field_name: str) -> str:
        return self.cell_references.get(field_name, "")


RegionRecord = DataRecord