"""
Document processing service for PDFs and Images.
Extracts text, metadata, and prepares multimodal payloads.
"""

import io
import base64
import logging
from typing import Dict, Any, Optional
from pypdf import PdfReader
from PIL import Image

logger = logging.getLogger(__name__)

# Maximum file size allowed (25 MB)
MAX_FILE_SIZE = 25 * 1024 * 1024
SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}
SUPPORTED_DOC_TYPES = {"application/pdf", "text/plain", "text/markdown"}


def extract_pdf_content(file_bytes: bytes, filename: str = "document.pdf") -> Dict[str, Any]:
    """
    Extracts text and metadata from a PDF file using pypdf.
    Returns:
        {
            "success": True,
            "filename": filename,
            "page_count": int,
            "text": str,
            "pages": [{"page_number": int, "text": str}],
            "is_scanned_or_empty": bool,
            "metadata": dict
        }
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        page_count = len(reader.pages)
        pages_content = []
        full_text_parts = []

        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            page_text = page_text.strip()
            pages_content.append({
                "page_number": idx + 1,
                "text": page_text
            })
            if page_text:
                full_text_parts.append(f"--- Page {idx + 1} ---\n{page_text}")

        extracted_text = "\n\n".join(full_text_parts).strip()
        is_scanned_or_empty = len(extracted_text) < 20

        raw_meta = reader.metadata or {}
        clean_meta = {}
        for k, v in raw_meta.items():
            if isinstance(k, str) and isinstance(v, (str, int, float)):
                clean_meta[k.replace("/", "")] = v

        return {
            "success": True,
            "filename": filename,
            "page_count": page_count,
            "text": extracted_text,
            "pages": pages_content,
            "is_scanned_or_empty": is_scanned_or_empty,
            "metadata": clean_meta,
            "file_size": len(file_bytes),
            "note": "Document text extracted successfully." if not is_scanned_or_empty else "The PDF contains minimal or no extractable text. It may be scanned or contain diagram/image pages."
        }
    except Exception as e:
        logger.error(f"Error reading PDF {filename}: {e}", exc_info=True)
        return {
            "success": False,
            "filename": filename,
            "error": f"Failed to extract text from PDF: {str(e)}",
            "page_count": 0,
            "text": ""
        }


def process_image(file_bytes: bytes, filename: str = "image.png", mime_type: str = "image/png") -> Dict[str, Any]:
    """
    Processes an image, validates format and dimensions, and produces base64 payload.
    """
    try:
        image = Image.open(io.BytesIO(file_bytes))
        width, height = image.size
        img_format = image.format or "PNG"
        mode = image.mode

        b64_data = base64.b64encode(file_bytes).decode("utf-8")
        data_uri = f"data:{mime_type};base64,{b64_data}"

        return {
            "success": True,
            "filename": filename,
            "mime_type": mime_type,
            "width": width,
            "height": height,
            "format": img_format,
            "mode": mode,
            "file_size": len(file_bytes),
            "base64_data": b64_data,
            "data_uri": data_uri,
            "summary": f"Image '{filename}' ({width}x{height}, {img_format}, {len(file_bytes)/1024:.1f} KB)"
        }
    except Exception as e:
        logger.error(f"Error processing image {filename}: {e}", exc_info=True)
        return {
            "success": False,
            "filename": filename,
            "error": f"Invalid or corrupt image format: {str(e)}"
        }


def process_text_file(file_bytes: bytes, filename: str = "document.txt") -> Dict[str, Any]:
    """Processes plain text or markdown files."""
    try:
        text = file_bytes.decode("utf-8", errors="replace").strip()
        return {
            "success": True,
            "filename": filename,
            "text": text,
            "page_count": 1,
            "file_size": len(file_bytes)
        }
    except Exception as e:
        return {
            "success": False,
            "filename": filename,
            "error": f"Could not read text file: {str(e)}"
        }
