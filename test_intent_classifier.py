import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm.intent_classifier import IntentClassifier


class FakeClient:
    def __init__(self, response):
        self.response = response

    def chat(self, system_prompt, user_prompt):
        return self.response


class IntentClassifierTests(unittest.TestCase):
    def test_calculation_phrase_is_classified_locally(self):
        classifier = IntentClassifier()

        result = classifier.classify("what is 12 plus 8")

        self.assertEqual(result["type"], "command")
        self.assertEqual(result["intent"], "calculate")
        self.assertEqual(result["target"], "12 + 8")

    def test_open_command_is_classified_locally(self):
        classifier = IntentClassifier()
        classifier.client = FakeClient('{"type":"command","intent":"open_app","target":"chrome"}')

        result = classifier.classify("open chrome")

        self.assertEqual(result["type"], "command")
        self.assertEqual(result["intent"], "open_app")
        self.assertEqual(result["target"], "chrome")

    def test_partial_command_json_is_recovered_from_text(self):
        classifier = IntentClassifier()
        classifier.client = FakeClient('{"type":"command"}')

        result = classifier.classify("open calculator")

        self.assertEqual(result["type"], "command")
        self.assertEqual(result["intent"], "open_app")
        self.assertEqual(result["target"], "calculator")


if __name__ == "__main__":
    unittest.main()
