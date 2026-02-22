import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from models.preprocessing import Preprocessor
from models.sentiment_model import SentimentModel
from models.severity_engine import SeverityEngine

class TestAIModels(unittest.TestCase):
    def setUp(self):
        self.preprocessor = Preprocessor()
        self.sentiment_model = SentimentModel()
        self.severity_engine = SeverityEngine()

    def test_preprocessing(self):
        text = "The doctor was VERY helpful!!"
        cleaned = self.preprocessor.clean_text(text)
        self.assertIn("doctor", cleaned)
        self.assertIn("helpful", cleaned)
        self.assertNotIn("!!", cleaned)

    def test_sentiment(self):
        text = "I love this hospital, everyone is so kind."
        sentiment, score = self.sentiment_model.analyze(text)
        self.assertEqual(sentiment, "Positive")
        self.assertGreater(score, 0)

        text = "I hate waiting for so long, it's terrible."
        sentiment, score = self.sentiment_model.analyze(text)
        self.assertEqual(sentiment, "Negative")
        self.assertLess(score, 0)

    def test_severity(self):
        text = "I am going to sue for malpractice."
        severity = self.severity_engine.calculate_severity(text, -0.8)
        self.assertEqual(severity, "Critical")

        text = "The food was cold."
        severity = self.severity_engine.calculate_severity(text, -0.2)
        self.assertEqual(severity, "Low")

if __name__ == "__main__":
    unittest.main()
