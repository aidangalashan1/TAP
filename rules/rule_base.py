# rules/rule_base.py

from abc import ABC
from abc import abstractmethod


class Rule(ABC):

    def __init__(self, rule_name, severity):
        self.rule_name = rule_name
        self.severity = severity

    @abstractmethod
    def execute(self, *args, **kwargs):
        raise NotImplementedError
