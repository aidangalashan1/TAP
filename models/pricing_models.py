from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class FindingCategory(str, Enum):
    # A worksheet the template expects is missing from the workbook.
    MISSING_WORKSHEET = "Missing Worksheet"

    # A check within a single supplier's own response (blanks,
    # zeroes, negatives, duplicates, an outlier within that one
    # workbook, or a bespoke advanced-rule condition) - no comparison
    # against a benchmark or other suppliers is involved.
    TENDER_RESPONSE_CHECK = "Tender Response Check"

    # This supplier's value compared against a known benchmark rate.
    BENCHMARK_COMPARISON = "Benchmark Comparison"

    # This supplier's value compared statistically against the other
    # suppliers' responses to the same field - no benchmark involved.
    BETWEEN_RESPONSE_COMPARISON = "Between-Response Comparison"


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

    category: str = FindingCategory.TENDER_RESPONSE_CHECK.value

    comparator_value: str | None = None

    comparator_label: str = "Comparator Value"

    deviation_percent: float | None = None

    suggested_clarification: str = ""

    # True when this finding is on a worksheet the user has flagged
    # (via "discrepancies expected" on that sheet in the mapping
    # review) as one where differences from the benchmark/other
    # suppliers are normal and not worth chasing as a clarification.
    expected_discrepancy: bool = False


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