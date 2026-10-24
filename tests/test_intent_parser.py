"""
Unit tests for Intent & Language Parser.
"""

import unittest
from services.intent_parser import parse_intent, detect_requested_language


class TestIntentParser(unittest.TestCase):
    def test_hindi_intent_detection(self):
        query = "Summarize this PDF in Hindi."
        res = parse_intent(query, has_attachment=True, attachment_type="pdf")
        self.assertEqual(res["intent"], "SUMMARIZE")
        self.assertEqual(res["language_info"]["primary_language"], "hi")

    def test_hinglish_intent_detection(self):
        query = "Explain this diagram in simple Hinglish."
        res = parse_intent(query, has_attachment=True, attachment_type="image")
        self.assertEqual(res["intent"], "EXPLAIN_DIAGRAM")
        self.assertEqual(res["language_info"]["primary_language"], "hinglish")

    def test_dual_language_detection(self):
        query = "Give me a spoken answer in English, but display the key points in Hindi."
        res = parse_intent(query)
        lang = res["language_info"]
        self.assertTrue(lang["is_dual"])
        self.assertEqual(lang["spoken_language"], "en")
        self.assertEqual(lang["display_language"], "hi")
        self.assertTrue(res["should_speak"])

    def test_read_aloud_intent(self):
        query = "Read this document aloud."
        res = parse_intent(query, has_attachment=True)
        self.assertEqual(res["intent"], "READ_ALOUD")
        self.assertTrue(res["should_speak"])

    def test_math_formula_intent(self):
        query = "Explain this mathematical formula step by step: E = mc^2"
        res = parse_intent(query)
        self.assertEqual(res["intent"], "EXPLAIN_FORMULA")

    def test_ambiguous_empty_query(self):
        res = parse_intent("", has_attachment=False)
        self.assertEqual(res["intent"], "AMBIGUOUS")
        self.assertTrue(res["is_ambiguous"])
        self.assertIsNotNone(res["clarification_question"])


if __name__ == "__main__":
    unittest.main()
