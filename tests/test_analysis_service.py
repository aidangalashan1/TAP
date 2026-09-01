# tests/test_analysis_service.py
#
# Integration-style tests that exercise AnalysisService end-to-end
# (missing-sheet detection, quick/advanced rules, benchmark and
# between-response comparison, expected-discrepancy flagging, and
# benchmark coverage) without touching real Excel files - a fake
# schema service stands in for SchemaBuilder/openpyxl so these run
# fast and deterministically.

from models.pricing_models import FindingCategory
from rules.cross_supplier_comparator import CrossSupplierComparator
from rules.custom_rule_models import (
    CustomRule,
    CustomRuleSeverity,
    CustomRuleType,
)
from schema.workbook_schema import (
    DataRecord,
    InputArea,
    RangeSchema,
    WorkbookSchema,
    WorksheetSchema,
)
from services.analysis_service import AnalysisService


def _record(sheet, ref, values):
    record = DataRecord(sheet_name=sheet, region_name=sheet, record_reference=ref)

    for field_name, value in values.items():
        record.set_value(field_name, value, f"{field_name}!{ref}")

    return record


class FakeSchemaService:
    """
    Stands in for SchemaService: each "workbook" passed to
    analyse_suppliers is just a dict {"records": [...], "missing_sheets": [...]}.
    """

    def get_missing_sheets(self, workbook, workbook_schema):
        return workbook.get("missing_sheets", [])

    def build_records(self, workbook, workbook_schema):
        return workbook["records"]


def _make_schema_with_sheets(sheet_names, expect_discrepancies_on=()):
    workbook_schema = WorkbookSchema(
        workbook_name="Template.xlsx", workbook_path="/tmp/Template.xlsx"
    )

    for sheet_name in sheet_names:
        worksheet_schema = WorksheetSchema(sheet_name=sheet_name)
        worksheet_schema.expect_discrepancies = (
            sheet_name in expect_discrepancies_on
        )

        worksheet_schema.add_input_area(
            InputArea(
                area_name="Value",
                sheet_name=sheet_name,
                area_range=RangeSchema(sheet_name, "B2", "B10"),
                user_confirmed=True,
            )
        )

        workbook_schema.add_worksheet(worksheet_schema)

    return workbook_schema


def test_benchmark_comparison_end_to_end_with_coverage_and_findings():
    service = AnalysisService(schema_service=FakeSchemaService())
    workbook_schema = _make_schema_with_sheets(["Sheet1"])

    supplier_a = {
        "records": [
            _record("Sheet1", "Row 2", {"FieldA": 110, "FieldB": 50})
        ],
    }
    supplier_b = {
        "records": [
            _record("Sheet1", "Row 2", {"FieldA": 90, "FieldB": 999})
        ],
    }
    # FieldB has no benchmark match at all.
    benchmark = {"records": [_record("Sheet1", "Row 2", {"FieldA": 100})]}

    results = service.analyse_suppliers(
        workbook_schema=workbook_schema,
        supplier_workbooks=[("SupplierA", supplier_a), ("SupplierB", supplier_b)],
        benchmark_workbook=benchmark,
        custom_rules=[],
        output_folder=None,
    )

    assert len(results) == 2

    result_a = next(r for r in results if r.supplier_name == "SupplierA")
    # FieldA: 110 vs 100 = 10% deviation, below the 30% default -
    # no finding. FieldB has no benchmark match, so it's also not a
    # finding, but it does count against coverage.
    assert result_a.findings == []
    assert result_a.benchmark_coverage.total_fields == 2
    assert result_a.benchmark_coverage.matched_fields == 1
    assert result_a.benchmark_coverage.unmatched_by_field == {"FieldB": 1}

    result_b = next(r for r in results if r.supplier_name == "SupplierB")
    assert result_b.findings == []


def test_missing_sheet_produces_a_high_severity_finding():
    service = AnalysisService(schema_service=FakeSchemaService())
    workbook_schema = _make_schema_with_sheets(["Sheet1", "Sheet2"])

    supplier = {
        "records": [],
        "missing_sheets": ["Sheet2"],
    }

    results = service.analyse_suppliers(
        workbook_schema=workbook_schema,
        supplier_workbooks=[("SupplierA", supplier)],
        output_folder=None,
    )

    findings = results[0].findings
    assert len(findings) == 1
    assert findings[0].category == FindingCategory.MISSING_WORKSHEET.value
    assert "Sheet2" in findings[0].worksheet_name


def test_quick_rule_findings_are_attributed_to_the_right_supplier():
    service = AnalysisService(schema_service=FakeSchemaService())
    workbook_schema = _make_schema_with_sheets(["Sheet1"])

    supplier_a = {"records": [_record("Sheet1", "Row 2", {"FieldA": None})]}
    supplier_b = {"records": [_record("Sheet1", "Row 2", {"FieldA": 100})]}

    rule = CustomRule(
        name="Quick Rules",
        severity=CustomRuleSeverity.MEDIUM,
        rule_type=CustomRuleType.QUICK_RULES,
        check_blanks=True,
    )

    results = service.analyse_suppliers(
        workbook_schema=workbook_schema,
        supplier_workbooks=[("SupplierA", supplier_a), ("SupplierB", supplier_b)],
        custom_rules=[rule],
        output_folder=None,
    )

    result_a = next(r for r in results if r.supplier_name == "SupplierA")
    result_b = next(r for r in results if r.supplier_name == "SupplierB")

    assert len(result_a.findings) == 1
    assert result_a.findings[0].supplier_name == "SupplierA"
    assert result_b.findings == []


def test_between_response_comparison_used_when_no_benchmark():
    service = AnalysisService(
        schema_service=FakeSchemaService(),
        # Default tolerance (3.0 standard deviations) is deliberately
        # loose; use a tighter one so a clear outlier among only 3
        # suppliers actually crosses it.
        cross_supplier_comparator=CrossSupplierComparator(
            outlier_tolerance=1.0
        ),
    )
    workbook_schema = _make_schema_with_sheets(["Sheet1"])

    suppliers = [
        ("SupplierA", {"records": [_record("Sheet1", "Row 2", {"FieldA": 100})]}),
        ("SupplierB", {"records": [_record("Sheet1", "Row 2", {"FieldA": 102})]}),
        ("SupplierC", {"records": [_record("Sheet1", "Row 2", {"FieldA": 500})]}),
    ]

    results = service.analyse_suppliers(
        workbook_schema=workbook_schema,
        supplier_workbooks=suppliers,
        benchmark_workbook=None,
        output_folder=None,
    )

    outlier_result = next(r for r in results if r.supplier_name == "SupplierC")
    assert len(outlier_result.findings) == 1
    assert outlier_result.findings[0].category == (
        FindingCategory.BETWEEN_RESPONSE_COMPARISON.value
    )
    # No benchmark workbook was passed, so coverage isn't computed.
    assert outlier_result.benchmark_coverage is None


def test_expect_discrepancies_flag_marks_findings_without_removing_them():
    service = AnalysisService(schema_service=FakeSchemaService())
    workbook_schema = _make_schema_with_sheets(
        ["Sheet1"], expect_discrepancies_on=["Sheet1"]
    )

    supplier = {"records": [_record("Sheet1", "Row 2", {"FieldA": None})]}

    rule = CustomRule(
        name="Quick Rules",
        severity=CustomRuleSeverity.MEDIUM,
        rule_type=CustomRuleType.QUICK_RULES,
        check_blanks=True,
    )

    results = service.analyse_suppliers(
        workbook_schema=workbook_schema,
        supplier_workbooks=[("SupplierA", supplier)],
        custom_rules=[rule],
        output_folder=None,
    )

    findings = results[0].findings
    assert len(findings) == 1
    assert findings[0].expected_discrepancy is True


def test_writes_a_report_file_when_output_folder_given(tmp_path):
    service = AnalysisService(schema_service=FakeSchemaService())
    workbook_schema = _make_schema_with_sheets(["Sheet1"])

    supplier = {"records": [_record("Sheet1", "Row 2", {"FieldA": 100})]}

    results = service.analyse_suppliers(
        workbook_schema=workbook_schema,
        supplier_workbooks=[("SupplierA", supplier)],
        output_folder=str(tmp_path),
    )

    report_path = results[0].report_path
    assert report_path != ""
    assert (tmp_path / "SupplierA_analysis.xlsx").exists()
