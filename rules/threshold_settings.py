# rules/threshold_settings.py

import json
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path

import config


@dataclass
class ThresholdSettings:
    """
    Global default thresholds used when comparing values, unless a
    rule overrides them with its own settings.

    - benchmark_threshold_percent: raw % difference from the benchmark
      rate at which a supplier value is flagged. Benchmark comparison
      is always against a single known reference value per field, so
      raw % diff is the only basis that applies to it.

    - default_outlier_tolerance_percent: raw % difference from the
      group average at which one supplier's value is flagged as an
      outlier relative to the other suppliers' responses to the same
      field (no benchmark involved) - the same basis as the benchmark
      threshold above, just against a computed average instead of an
      external reference value.
    """

    benchmark_threshold_percent: float = (
        config.DEFAULT_BENCHMARK_THRESHOLD_PERCENT
    )

    default_outlier_tolerance_percent: float = (
        config.DEFAULT_OUTLIER_THRESHOLD_PERCENT
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
                default_outlier_tolerance_percent=float(
                    data.get(
                        "default_outlier_tolerance_percent",
                        config.DEFAULT_OUTLIER_THRESHOLD_PERCENT,
                    )
                ),
            )
        except Exception:
            return ThresholdSettings()

    def save(self, settings):
        data = asdict(settings)

        parent = self.file_path.parent

        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)

        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
