import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from services.rule_engine import RuleEngine

class TestServices(unittest.TestCase):
    def setUp(self):
        self.rule_engine = RuleEngine()

    def test_rule_engine(self):
        dept, sla = self.rule_engine.determine_sla_and_dept("Billing", "High")
        self.assertEqual(dept, "Finance")
        self.assertEqual(sla, 24)

        dept, sla = self.rule_engine.determine_sla_and_dept("Waiting Time", "Critical")
        self.assertEqual(dept, "Front Desk")
        self.assertEqual(sla, 4)

if __name__ == "__main__":
    unittest.main()
