from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class Finding:
    severity: Severity

    worksheet_name: str

    cell_reference: str

    actual_value: str

    reason: str

    supplier_name: str = ""

    item_code: str = ""
    item_description: str = ""

    comparator_value: str | None = None

    deviation_percent: float | None = None

    suggested_clarification: str = ""


@dataclass
class SupplierAnalysisResult:
    supplier_name: str

    findings: list[Finding]


@dataclass
class AnalysisSummary:
    suppliers_analysed: int

    total_findings: int

    high_findings: int

    medium_findings: int

    low_findings: int

    info_findings: int