# rules/benchmark_outlier_rule.py

from models.pricing_models import Finding
from models.pricing_models import Severity
from rules.rule_base import Rule


class BenchmarkOutlierRule(Rule):

    def __init__(self, threshold_percent=30.0):
        super().__init__(
            rule_name="Benchmark Outlier Check",
            severity=Severity.MEDIUM
        )

        self.threshold_percent = threshold_percent

    def execute(self, pricing_lines):
        findings = []

        for line in pricing_lines:
            if line.benchmark_value is None:
                continue

            if line.value is None:
                continue

            actual_value = float(line.value)
            benchmark_value = float(line.benchmark_value)

            if benchmark_value <= 0:
                continue

            deviation_percent = (
                abs(actual_value - benchmark_value)
                / benchmark_value
            ) * 100

            if deviation_percent < self.threshold_percent:
                continue

            finding = Finding(
                supplier_name=line.supplier_name,
                severity=self.severity,
                worksheet_name=line.worksheet_name,
                cell_reference=line.cell_reference,
                item_code=line.item_code,
                item_description=line.item_description,
                actual_value=str(round(actual_value, 2)),
                comparator_value=str(round(benchmark_value, 2)),
                deviation_percent=round(deviation_percent, 2),
                reason=(
                    f"Value differs from benchmark by "
                    f"{deviation_percent:.2f}%"
                ),
                suggested_clarification=(
                    "Please confirm the submitted rate for "
                    f"{line.item_description}. The submitted value "
                    f"of {actual_value:.2f} differs from the benchmark "
                    f"value of {benchmark_value:.2f} by "
                    f"{deviation_percent:.2f}%."
                )
            )

            findings.append(finding)

        return findings