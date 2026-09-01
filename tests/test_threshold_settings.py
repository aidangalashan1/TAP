# tests/test_threshold_settings.py

from rules.threshold_settings import ThresholdSettings, ThresholdSettingsStore


def test_load_returns_defaults_when_file_missing(tmp_path):
    store = ThresholdSettingsStore(file_path=str(tmp_path / "missing.json"))
    settings = store.load()

    assert isinstance(settings, ThresholdSettings)
    assert settings.default_outlier_tolerance_percent == 30.0


def test_round_trips_custom_settings(tmp_path):
    store = ThresholdSettingsStore(file_path=str(tmp_path / "settings.json"))

    settings = ThresholdSettings(
        benchmark_threshold_percent=12.5,
        default_outlier_tolerance_percent=20.0,
    )

    store.save(settings)
    loaded = store.load()

    assert loaded.benchmark_threshold_percent == 12.5
    assert loaded.default_outlier_tolerance_percent == 20.0


def test_load_falls_back_to_defaults_on_corrupt_file(tmp_path):
    file_path = tmp_path / "settings.json"
    file_path.write_text("{not valid json")

    store = ThresholdSettingsStore(file_path=str(file_path))
    settings = store.load()

    assert settings == ThresholdSettings()
