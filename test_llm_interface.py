import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm.interface import LLMInterface


class FakeClient:
    def __init__(self, response):
        self.response = response

    def chat(self, system_prompt, user_prompt):
        return self.response


class LLMInterfaceTests(unittest.TestCase):
    def test_bare_question_falls_back_to_answer(self):
        llm = LLMInterface()
        llm.client = FakeClient('{"type":"command","intent":"unknown","target":""}')

        result = llm.extract_intent("define mathematics")

        self.assertEqual(result["type"], "question")
        self.assertEqual(result["intent"], "answer")

    def test_question_starter_is_preserved_as_question(self):
        llm = LLMInterface()
        llm.client = FakeClient('{"type":"command","intent":"unknown","target":""}')

        result = llm.extract_intent("what is the capital of india")

        self.assertEqual(result["type"], "question")
        self.assertEqual(result["intent"], "answer")

    def test_supported_command_stays_a_command(self):
        llm = LLMInterface()
        llm.intent_classifier.client = FakeClient('{"type":"command","intent":"open_app","target":"chrome"}')

        result = llm.extract_intent("open chrome")

        self.assertEqual(result["type"], "command")
        self.assertEqual(result["intent"], "open_app")

    def test_calculation_phrase_maps_to_calculate(self):
        llm = LLMInterface()
        llm.client = FakeClient('{"type":"command","intent":"unknown","target":""}')

        result = llm.extract_intent("what is 12 plus 8")

        self.assertEqual(result["type"], "command")
        self.assertEqual(result["intent"], "calculate")
        self.assertEqual(result["target"], "12 + 8")


if __name__ == "__main__":
    unittest.main()
