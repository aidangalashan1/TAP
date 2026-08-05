# rules/median_outlier_rule.py

from statistics import median

from models.pricing_models import Finding
from models.pricing_models import Severity
from rules.rule_base import Rule


class MedianOutlierRule(Rule):
    """
    Identifies pricing entries that deviate significantly
    from the median price across all pricing lines.

    This is intended to identify:
    - Potential data entry errors
    - Missing decimal points
    - Pricing anomalies
    - Commercial outliers

    Example:

        Median = £50

        Value = £250

        Deviation = 400%

        -> Finding created
    """

    def __init__(self, threshold_percent=30.0):
        super().__init__(
            rule_name="Median Outlier Check",
            severity=Severity.MEDIUM
        )

        self.threshold_percent = threshold_percent

    def execute(self, pricing_lines):
        findings = []

        numeric_values = []

        for line in pricing_lines:

            if line.value is None:
                continue

            if line.value <= 0:
                continue

            numeric_values.append(
                float(line.value)
            )

        if len(numeric_values) < 2:
            return findings

        median_value = median(
            numeric_values
        )

        if median_value == 0:
            return findings

        for line in pricing_lines:

            if line.value is None:
                continue

            if line.value <= 0:
                continue

            deviation_percent = (
                abs(
                    line.value - median_value
                )
                / median_value
            ) * 100

            if deviation_percent < self.threshold_percent:
                continue

            findings.append(
                Finding(
                    supplier_name=line.supplier_name,
                    severity=self.severity,
                    worksheet_name=line.worksheet_name,
                    cell_reference=line.cell_reference,
                    item_code=line.item_code,
                    item_description=line.item_description,
                    actual_value=str(line.value),
                    comparator_value=str(
                        round(median_value, 2)
                    ),
                    deviation_percent=round(
                        deviation_percent,
                        2
                    ),
                    reason=(
                        f"Value differs from "
                        f"median by "
                        f"{deviation_percent:.2f}%"
                    ),
                    suggested_clarification=(
                        "Please confirm that the "
                        "submitted value is correct "
                        "as it differs significantly "
                        "from the median value for "
                        "the pricing dataset."
                    )
                )
            )

        return findings