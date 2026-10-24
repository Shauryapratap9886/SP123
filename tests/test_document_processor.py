"""
Unit tests for Document and Image Processor.
"""

import io
import unittest
from PIL import Image
from pypdf import PdfWriter
from services.document_processor import extract_pdf_content, process_image, process_text_file


class TestDocumentProcessor(unittest.TestCase):
    def test_image_processing(self):
        # Generate an in-memory test image
        img = Image.new("RGB", (200, 100), color=(73, 109, 137))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        raw = img_bytes.getvalue()

        res = process_image(raw, "test_diagram.png", "image/png")
        self.assertTrue(res["success"])
        self.assertEqual(res["width"], 200)
        self.assertEqual(res["height"], 100)
        self.assertIn("base64_data", res)

    def test_text_processing(self):
        sample = b"This is a test document with key notes."
        res = process_text_file(sample, "notes.txt")
        self.assertTrue(res["success"])
        self.assertIn("key notes", res["text"])

    def test_pdf_extraction(self):
        # Create a simple PDF using PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        pdf_bytes = io.BytesIO()
        writer.write(pdf_bytes)
        raw = pdf_bytes.getvalue()

        res = extract_pdf_content(raw, "blank.pdf")
        self.assertTrue(res["success"])
        self.assertEqual(res["page_count"], 1)


if __name__ == "__main__":
    unittest.main()
