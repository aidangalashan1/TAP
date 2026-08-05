# services/custom_rules_service.py

from pathlib import Path

import config
from rules.custom_rule_store import CustomRuleStore
from rules.schema_rule_engine import SchemaRuleEngine
from schema.schema_builder import SchemaBuilder


class CustomRulesService:
    # Coordinates user-defined rule storage and execution.
    #
    # This version is schema-driven and no longer uses:
    # - HeaderDetector
    # - RowBuilder
    # - WorkbookRow
    # - CustomRuleEngine
    #
    # Instead it uses:
    # - SchemaBuilder
    # - WorkbookSchema
    # - DataRecord
    # - SchemaRuleEngine

    def __init__(self, rules_file_path=None):
        if rules_file_path is None:
            rules_file_path = config.CUSTOM_RULES_FILE_PATH

        self.rules_file_path = Path(rules_file_path)
        self.rule_store = CustomRuleStore(str(self.rules_file_path))
        self.schema_builder = SchemaBuilder()
        self.rule_engine = SchemaRuleEngine()

    def load_rules(self):
        return self.rule_store.load_rules()

    def save_rules(self, rules):
        self.rule_store.save_rules(rules)

    def get_rule_count(self):
        return len(self.load_rules())

    def build_schema(self, workbook):
        return self.schema_builder.build_schema(workbook)

    def build_records(self, workbook, workbook_schema):
        return self.schema_builder.build_records(
            workbook,
            workbook_schema,
        )

    def build_schema_and_records(self, workbook):
        return self.schema_builder.build_schema_and_records(workbook)

    def get_available_sheets(self, workbook):
        workbook_schema = self.build_schema(workbook)
        return sorted(workbook_schema.worksheets.keys())

    def execute_rules(self, workbook, rules=None, workbook_schema=None):
        if rules is None:
            rules = self.load_rules()

        if not rules:
            return []

        if workbook_schema is None:
            workbook_schema, records = self.build_schema_and_records(workbook)
        else:
            records = self.build_records(
                workbook,
                workbook_schema,
            )

        return self.rule_engine.execute(
            records,
            rules,
        )

    def execute_rules_against_records(self, records, rules=None):
        if rules is None:
            rules = self.load_rules()

        if not rules:
            return []

        return self.rule_engine.execute(
            records,
            rules,
        )

    def get_schema_summary(self, workbook):
        workbook_schema = self.build_schema(workbook)
        summary = []

        for worksheet in workbook_schema.worksheets.values():
            for input_area in worksheet.get_active_input_areas():
                summary.append(
                    {
                        "sheet_name": input_area.sheet_name,
                        "area_name": input_area.area_name,
                        "range": input_area.address,
                        "confidence": input_area.confidence,
                    }
                )

        return summary