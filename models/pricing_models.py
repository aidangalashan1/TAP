from dataclasses import dataclass
from dataclasses import field
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
class BenchmarkCoverage:
    """
    How completely a supplier's submitted fields could actually be
    checked against the benchmark workbook - independent of whether
    any deviation was large enough to be flagged as a finding.

    A field counts as "matched" when the benchmark workbook has a
    numeric value at the same (sheet, row, field) identity as the
    supplier's submitted value. Anything else - no benchmark cell at
    that identity, a blank benchmark cell, non-numeric text - counts
    as unmatched, since no comparison could actually be made.
    """

    total_fields: int = 0
    matched_fields: int = 0

    # sheet_name -> count of unmatched fields on that sheet, so a
    # systematic mismatch (wrong sheet name, shifted rows) is easy
    # to spot rather than buried in a flat number.
    unmatched_by_sheet: dict[str, int] = field(default_factory=dict)

    # field_name -> count of unmatched instances, capped by the
    # caller to the worst offenders - helps spot a single field
    # that's consistently missing a benchmark match.
    unmatched_by_field: dict[str, int] = field(default_factory=dict)

    @property
    def unmatched_fields(self) -> int:
        return self.total_fields - self.matched_fields

    @property
    def match_rate_percent(self) -> float:
        if self.total_fields == 0:
            return 0.0

        return round(
            (self.matched_fields / self.total_fields) * 100,
            1,
        )


@dataclass
class SupplierAnalysisResult:
    supplier_name: str

    findings: list[Finding]

    benchmark_coverage: BenchmarkCoverage | None = None


@dataclass
class AnalysisSummary:
    suppliers_analysed: int

    total_findings: int

    high_findings: int

    medium_findings: int

    low_findings: int

    info_findings: int