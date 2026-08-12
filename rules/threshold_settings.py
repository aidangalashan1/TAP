# rules/threshold_settings.py

import json
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path

import config
from rules.custom_rule_models import OutlierMethod


@dataclass
class ThresholdSettings:
    """
    Global default thresholds used when comparing values, unless a
    rule overrides them with its own settings.

    - benchmark_threshold_percent: raw % difference from the benchmark
      rate at which a supplier value is flagged. Benchmark comparison
      is always against a single known reference value per field, so
      raw % diff is the only basis that applies to it.

    - default_outlier_method / default_outlier_tolerance: the basis
      used to flag one supplier's value as an outlier relative to the
      other suppliers' responses to the same field (no benchmark
      involved) - Z_SCORE compares against the group mean/standard
      deviation, IQR compares against the group median/quartile range.
    """

    benchmark_threshold_percent: float = (
        config.DEFAULT_BENCHMARK_THRESHOLD_PERCENT
    )

    default_outlier_method: OutlierMethod = OutlierMethod.Z_SCORE

    default_outlier_tolerance: float = (
        config.DEFAULT_STANDARD_DEVIATION_THRESHOLD
    )


class ThresholdSettingsStore:
    def __init__(self, file_path=None):
        if file_path is None:
            file_path = config.THRESHOLD_SETTINGS_FILE_PATH

        self.file_path = Path(file_path)

    def load(self):
        if not self.file_path.exists():
            return ThresholdSettings()

        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            return ThresholdSettings()

        try:
            return ThresholdSettings(
                benchmark_threshold_percent=float(
                    data.get(
                        "benchmark_threshold_percent",
                        config.DEFAULT_BENCHMARK_THRESHOLD_PERCENT,
                    )
                ),
                default_outlier_method=self._parse_outlier_method(
                    data.get("default_outlier_method", "Z_SCORE")
                ),
                default_outlier_tolerance=float(
                    data.get(
                        "default_outlier_tolerance",
                        config.DEFAULT_STANDARD_DEVIATION_THRESHOLD,
                    )
                ),
            )
        except Exception:
            return ThresholdSettings()

    def save(self, settings):
        data = asdict(settings)
        data["default_outlier_method"] = settings.default_outlier_method.value

        parent = self.file_path.parent

        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)

        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    def _parse_outlier_method(self, value):
        try:
            return OutlierMethod(str(value))
        except ValueError:
            return OutlierMethod.Z_SCORE
