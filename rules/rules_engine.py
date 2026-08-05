# rules/rules_engine.py

from rules.schema_rule_engine import (
    SchemaRuleEngine,
)


class RulesEngine:

    def __init__(self):
        self.schema_rule_engine = (
            SchemaRuleEngine()
        )

    def execute(
        self,
        records,
        custom_rules,
    ):
        findings = []

        findings.extend(
            self.schema_rule_engine.execute(
                records,
                custom_rules,
            )
        )

        return findings