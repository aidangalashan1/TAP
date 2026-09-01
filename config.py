# config.py

# Application-level configuration for the Tender Clarification Analyser.
#
# Keep default values here rather than hardcoding them across
# parser, rules, GUI, and reporting modules.


from dataclasses import dataclass
from pathlib import Path


# --------------------------------------------------
# Application Directory
# --------------------------------------------------

# Anchor persisted app data (custom rules, mapping profiles, reports)
# to the application's own directory rather than the process's current
# working directory, which changes depending on how the app is launched.

BASE_DIR = Path(__file__).resolve().parent


# --------------------------------------------------
# Application Defaults
# --------------------------------------------------

APP_NAME = "Tender Clarification Analyser"

DEFAULT_OUTPUT_FOLDER = str(BASE_DIR / "reports")

DEFAULT_REPORT_FILE_NAME = "tender_clarification_report.xlsx"

CUSTOM_RULES_FILE_PATH = str(BASE_DIR / "custom_rules.json")

THRESHOLD_SETTINGS_FILE_PATH = str(BASE_DIR / "threshold_settings.json")

SESSION_FILE_PATH = str(BASE_DIR / "session.json")

MAPPING_PROFILES_DIRECTORY = str(BASE_DIR / "mapping_profiles")


# --------------------------------------------------
# Excel File Support
# --------------------------------------------------

SUPPORTED_EXCEL_EXTENSIONS = {
    ".xlsx",
    ".xlsm",
    ".xls",
}


# --------------------------------------------------
# Mandatory Cell Detection
# --------------------------------------------------

# Common yellow fill colours used in Excel templates to indicate
# supplier input cells - matched as a substring of a cell's fill
# colour by InputAreaDetector, since Excel fill colours often carry
# an alpha-channel prefix (e.g. "FFFFFF00").

YELLOW_FILL_CODES = {
    "FFFF00",
    "FFFF99",
    "FFFFCC",
    "FFF2CC",
    "FFEB9C",
}


# --------------------------------------------------
# Optional Sections
# --------------------------------------------------

# These phrases identify sections that should normally
# be ignored because they are optional supplier catalogue
# areas rather than mandatory evaluated tender items.

OPTIONAL_SECTION_KEYWORDS = [
    "Other/Non Standard/Specialist Attachments",
    "Other / Non Standard / Specialist Attachments",
    "Other attachments not covered above",
    "Other (Please insert title)",
]


# --------------------------------------------------
# Default Analysis Thresholds
# --------------------------------------------------

DEFAULT_OUTLIER_THRESHOLD_PERCENT = 30.0

DEFAULT_BENCHMARK_THRESHOLD_PERCENT = 30.0

DEFAULT_STANDARD_DEVIATION_THRESHOLD = 3.0

DEFAULT_WEEKEND_PREMIUM_THRESHOLD_PERCENT = 100.0


# --------------------------------------------------
# Severity Thresholds
# --------------------------------------------------

HIGH_SEVERITY_DEVIATION_PERCENT = 100.0

MEDIUM_SEVERITY_DEVIATION_PERCENT = 50.0

LOW_SEVERITY_DEVIATION_PERCENT = 25.0


# --------------------------------------------------
# Report Sheet Names
# --------------------------------------------------

SUMMARY_SHEET_NAME = "Executive Summary"

DETAILED_FINDINGS_SHEET_NAME = "Detailed Findings"

CLARIFICATIONS_SHEET_NAME = "Clarifications"


# --------------------------------------------------
# Dataclass Settings Object
# --------------------------------------------------

@dataclass
class AppConfig:
    app_name: str = APP_NAME

    output_folder: str = DEFAULT_OUTPUT_FOLDER

    default_report_file_name: str = DEFAULT_REPORT_FILE_NAME

    default_outlier_threshold_percent: float = (
        DEFAULT_OUTLIER_THRESHOLD_PERCENT
    )

    default_benchmark_threshold_percent: float = (
        DEFAULT_BENCHMARK_THRESHOLD_PERCENT
    )

    default_standard_deviation_threshold: float = (
        DEFAULT_STANDARD_DEVIATION_THRESHOLD
    )

    default_weekend_premium_threshold_percent: float = (
        DEFAULT_WEEKEND_PREMIUM_THRESHOLD_PERCENT
    )

    check_blank_cells: bool = True

    check_zero_values: bool = True

    check_negative_values: bool = True

    check_statistical_outliers: bool = True

    check_benchmark_variance: bool = True

    check_weekend_weekday_logic: bool = True

    check_formula_overwrites: bool = True

    check_summary_reconciliation: bool = True

    ignore_optional_sections: bool = True

    def get_output_folder_path(self):
        return Path(self.output_folder)

    def get_default_report_path(self):
        return (
            self.get_output_folder_path()
            / self.default_report_file_name
        )


# --------------------------------------------------
# Helper Functions
# --------------------------------------------------

def is_supported_excel_file(file_path):
    suffix = Path(file_path).suffix.lower()

    return suffix in SUPPORTED_EXCEL_EXTENSIONS


def get_default_config():
    return AppConfig()