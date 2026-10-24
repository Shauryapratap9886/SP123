"""
Unit tests for AI Service Layer and Multilingual Response Generation.
"""

import unittest
from services.intent_parser import parse_intent
from services.ai_service import generate_multilingual_response


class TestAIService(unittest.TestCase):
    def test_builtin_summarize_hinglish(self):
        query = "Explain this in simple Hinglish."
        intent_data = parse_intent(query, has_attachment=True)
        doc_data = {
            "type": "pdf",
            "filename": "class_notes.pdf",
            "extracted_text": (
                "Supervised learning trains models on labeled data pairs.\n\n"
                "Unsupervised learning discovers clusters and hidden patterns.\n\n"
                "Reinforcement learning optimizes rewards via environment feedback."
            )
        }
        res = generate_multilingual_response(query, intent_data, doc_data, history=[], preferred_provider="builtin")
        self.assertTrue(res["success"])
        self.assertIn("Hinglish", res["display_text"])
        self.assertIsNotNone(res["spoken_text"])

    def test_builtin_dual_language(self):
        query = "Give me a spoken answer in English, but display the key points in Hindi."
        intent_data = parse_intent(query)
        res = generate_multilingual_response(query, intent_data, doc_data=None, history=[], preferred_provider="builtin")
        self.assertTrue(res["success"])
        self.assertEqual(res["spoken_language"], "en")
        self.assertIn("हिंदी", res["display_text"] + res.get("display_language", ""))


if __name__ == "__main__":
    unittest.main()
