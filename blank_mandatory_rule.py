# rules/blank_mandatory_rule.py

from models.pricing_models import Finding
from models.pricing_models import Severity
from rules.rule_base import Rule


class BlankMandatoryRule(Rule):
    """
    Identifies mandatory workbook cells that have not been completed.
    This rule operates on a WorkbookInfo object rather than PricingLine
    objects because blank mandatory cells are lost during pricing extraction.
    """

    def __init__(self):
        super().__init__(
            rule_name="Blank Mandatory Cell Check",
            severity=Severity.HIGH
        )

    def execute(self, workbook):
        findings = []

        for worksheet in workbook.worksheets.values():

            for cell in worksheet.cells:

                if not cell.is_mandatory:
                    continue

                if self._has_value(cell.value):
                    continue

                findings.append(
                    Finding(
                        supplier_name=workbook.file_name,
                        severity=self.severity,
                        worksheet_name=worksheet.worksheet_name,
                        cell_reference=cell.cell_reference,
                        item_code="",
                        item_description="Mandatory input cell",
                        actual_value="",
                        reason="Mandatory cell is blank",
                        comparator_value=None,
                        deviation_percent=None,
                        suggested_clarification=(
                            f"Please complete mandatory cell "
                            f"{cell.cell_reference} in worksheet "
                            f"'{worksheet.worksheet_name}'."
                        )
                    )
                )

        return findings

    def _has_value(self, value):
        if value is None:
            return False

        if isinstance(value, str):
            return value.strip() != ""

        return True