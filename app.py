"""
Multilingual AI Voice Assistant - Backend Server
Provides REST API endpoints and static web application serving.
"""

import os
import json
import base64
import logging
from urllib.parse import urlparse, parse_qs
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import config
from services.document_processor import (
    extract_pdf_content,
    process_image,
    process_text_file,
    MAX_FILE_SIZE
)
from services.intent_parser import parse_intent
from services.session_manager import session_manager
from services.ai_service import generate_multilingual_response
from services.tts_service import synthesize_speech_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("App")


class AppRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(config.STATIC_DIR), **kwargs)

    def end_headers(self):
        # Enable CORS and caching headers for local testing
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, data: dict, status_code: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Malformed JSON request: {e}")
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/config":
            self.handle_get_config()
            return
        elif path == "/api/sample":
            self.handle_get_sample(parsed)
            return

        # Fallback to serving static frontend files
        if path == "/" or path == "":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/upload":
            self.handle_upload()
        elif path == "/api/chat":
            self.handle_chat()
        elif path == "/api/tts":
            self.handle_tts()
        elif path == "/api/config":
            self.handle_update_config()
        elif path == "/api/session/clear":
            self.handle_clear_session()
        else:
            self.send_json({"error": "Endpoint not found"}, 404)

    # =========================================================================
    # API Handlers
    # =========================================================================
    def handle_get_config(self):
        active_provider = config.get_active_provider()
        resp = {
            "active_provider": active_provider,
            "has_gemini": bool(config.get_api_key("gemini")),
            "has_openai": bool(config.get_api_key("openai")),
            "has_sarvam": bool(config.get_api_key("sarvam")),
            "preferred_provider": config.RUNTIME_CONFIG.get("preferred_provider", "auto"),
            "supported_languages": config.SUPPORTED_LANGUAGES,
            "providers_list": [
                {"id": "auto", "name": f"Auto Best Match ({active_provider.title()})"},
                {"id": "gemini", "name": "Google Gemini 2.5 Flash", "has_key": bool(config.get_api_key("gemini"))},
                {"id": "openai", "name": "OpenAI GPT-4o-mini", "has_key": bool(config.get_api_key("openai"))},
                {"id": "sarvam", "name": "Sarvam AI (Indic Focus)", "has_key": bool(config.get_api_key("sarvam"))},
                {"id": "builtin", "name": "Built-in Intelligent Engine (Local)", "has_key": True}
            ]
        }
        self.send_json(resp)

    def handle_update_config(self):
        data = self.read_json_body()
        gemini_k = data.get("gemini_api_key")
        openai_k = data.get("openai_api_key")
        sarvam_k = data.get("sarvam_api_key")
        provider = data.get("preferred_provider")

        config.update_runtime_config(
            gemini_key=gemini_k,
            openai_key=openai_k,
            sarvam_key=sarvam_k,
            provider=provider
        )

        logger.info(f"Updated configuration. Preferred provider: {provider}")
        self.send_json({"success": True, "active_provider": config.get_active_provider()})

    def handle_upload(self):
        """
        Processes file upload passed via JSON base64 payload.
        Expected JSON:
        {
            "session_id": "...",
            "filename": "...",
            "mime_type": "...",
            "base64_data": "..."
        }
        """
        data = self.read_json_body()
        session_id = data.get("session_id", "default")
        filename = data.get("filename", "uploaded_file")
        mime_type = data.get("mime_type", "application/pdf")
        b64_content = data.get("base64_data", "")

        if not b64_content:
            self.send_json({"success": False, "error": "No file content received"}, 400)
            return

        try:
            # Handle potential data URI prefix
            if "," in b64_content:
                b64_content = b64_content.split(",", 1)[1]
            file_bytes = base64.b64decode(b64_content)
        except Exception as e:
            self.send_json({"success": False, "error": f"Invalid base64 payload: {str(e)}"}, 400)
            return

        if len(file_bytes) > MAX_FILE_SIZE:
            self.send_json({"success": False, "error": "File exceeds 25MB limit"}, 400)
            return

        session = session_manager.get_or_create(session_id)
        result = {}

        # Determine file type
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".pdf" or mime_type == "application/pdf":
            extracted = extract_pdf_content(file_bytes, filename)
            if not extracted.get("success"):
                self.send_json(extracted, 400)
                return
            
            doc_record = {
                "type": "pdf",
                "filename": filename,
                "mime_type": "application/pdf",
                "extracted_text": extracted.get("text", ""),
                "page_count": extracted.get("page_count", 1),
                "is_scanned_or_empty": extracted.get("is_scanned_or_empty", False),
                "metadata": extracted.get("metadata", {}),
                "summary": f"PDF Document: {filename} ({extracted.get('page_count')} pages)"
            }
            session.set_document(doc_record)
            result = {
                "success": True,
                "document": doc_record,
                "extracted_text_preview": (extracted.get("text") or "")[:500],
                "full_extracted_text": extracted.get("text", "")
            }

        elif ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"] or mime_type.startswith("image/"):
            img_result = process_image(file_bytes, filename, mime_type)
            if not img_result.get("success"):
                self.send_json(img_result, 400)
                return

            doc_record = {
                "type": "image",
                "filename": filename,
                "mime_type": mime_type,
                "base64_data": img_result["base64_data"],
                "data_uri": img_result["data_uri"],
                "width": img_result["width"],
                "height": img_result["height"],
                "summary": img_result["summary"]
            }
            session.set_document(doc_record)
            result = {
                "success": True,
                "document": doc_record,
                "thumbnail_uri": img_result["data_uri"]
            }

        elif ext in [".txt", ".md"] or mime_type.startswith("text/"):
            txt_result = process_text_file(file_bytes, filename)
            doc_record = {
                "type": "text",
                "filename": filename,
                "extracted_text": txt_result.get("text", ""),
                "summary": f"Text File: {filename}"
            }
            session.set_document(doc_record)
            result = {
                "success": True,
                "document": doc_record,
                "extracted_text_preview": (txt_result.get("text") or "")[:500]
            }
        else:
            self.send_json({"success": False, "error": f"Unsupported file type '{ext}'"}, 400)
            return

        self.send_json(result)

    def handle_chat(self):
        """
        Handles multimodal conversation turn.
        Expected JSON:
        {
            "session_id": "...",
            "message": "...",
            "language_preference": "auto" | "en" | "hi" | "hinglish",
            "provider": "auto" | "gemini" | "openai" | "sarvam" | "builtin"
        }
        """
        data = self.read_json_body()
        session_id = data.get("session_id", "default")
        message = data.get("message", "").strip()
        pref_lang = data.get("language_preference", "auto")
        pref_provider = data.get("provider", "auto")

        session = session_manager.get_or_create(session_id)
        active_doc = session.active_document

        # Parse user intent and requested languages
        has_doc = active_doc is not None
        doc_type = active_doc.get("type") if has_doc else None
        intent_data = parse_intent(
            query=message,
            has_attachment=has_doc,
            attachment_type=doc_type,
            preference_lang=pref_lang
        )

        # Ambiguous check: If empty input and no active attachment
        if intent_data.get("is_ambiguous"):
            clarify = intent_data.get("clarification_question")
            self.send_json({
                "success": True,
                "intent": "AMBIGUOUS",
                "display_text": clarify,
                "spoken_text": clarify,
                "spoken_language": "en",
                "should_speak": False,
                "has_extracted_content": False
            })
            return

        # Fetch multi-turn conversation context
        history = session.get_conversation_history(max_turns=6)

        # Generate response using AI Service layer
        ai_resp = generate_multilingual_response(
            query=message,
            intent_data=intent_data,
            doc_data=active_doc,
            history=history,
            preferred_provider=pref_provider
        )

        display_text = ai_resp.get("display_text", "")
        spoken_text = ai_resp.get("spoken_text", "")
        spoken_lang = ai_resp.get("spoken_language", "en")
        display_lang = ai_resp.get("display_language", "en")
        should_speak = intent_data.get("should_speak", False)

        # Save turn to session memory
        session.add_message("user", message, {"intent": intent_data.get("intent")})
        session.add_message("assistant", display_text, {
            "spoken_text": spoken_text,
            "provider": ai_resp.get("provider")
        })

        # Check for extracted document content to clearly distinguish it in the UI
        extracted_preview = None
        if active_doc and active_doc.get("extracted_text"):
            extracted_preview = active_doc["extracted_text"][:2000]

        # Optional Server-side TTS synthesis if configured
        tts_audio = None
        if should_speak:
            server_tts = synthesize_speech_server(spoken_text, spoken_lang, pref_provider)
            if server_tts.get("success"):
                tts_audio = {
                    "audio_base64": server_tts.get("audio_base64"),
                    "mime_type": server_tts.get("mime_type"),
                    "provider": server_tts.get("provider")
                }

        self.send_json({
            "success": True,
            "session_id": session_id,
            "intent": intent_data.get("intent"),
            "display_text": display_text,
            "spoken_text": spoken_text,
            "spoken_language": spoken_lang,
            "display_language": display_lang,
            "should_speak": should_speak,
            "provider": ai_resp.get("provider"),
            "has_extracted_content": bool(extracted_preview),
            "extracted_content_preview": extracted_preview,
            "active_document": {
                "filename": active_doc.get("filename"),
                "type": active_doc.get("type"),
                "summary": active_doc.get("summary")
            } if active_doc else None,
            "tts_audio": tts_audio
        })

    def handle_tts(self):
        """Dedicated endpoint to convert any text to speech on demand."""
        data = self.read_json_body()
        text = data.get("text", "")
        lang = data.get("language", "en")
        provider = data.get("provider", "auto")

        result = synthesize_speech_server(text, lang, provider)
        self.send_json(result)

    def handle_clear_session(self):
        data = self.read_json_body()
        session_id = data.get("session_id", "default")
        session = session_manager.get_or_create(session_id)
        session.clear()
        self.send_json({"success": True, "message": "Session context and attachments reset."})

    def handle_get_sample(self, parsed):
        """Returns built-in sample document text for zero-effort instant testing."""
        sample_type = parse_qs(parsed.query).get("type", ["notes"])[0]
        if sample_type == "math":
            self.send_json({
                "filename": "quantum_physics_formula.txt",
                "text": "Energy-Frequency Relation:\nE = h * nu\nWhere:\nE = Energy of photon\nh = Planck's constant (6.626e-34 J s)\nnu = Frequency of electromagnetic wave.\n\nEinstein's Mass-Energy Equivalence:\nE = m * c^2\nWhere m is relativistic mass and c is the speed of light."
            })
        else:
            self.send_json({
                "filename": "ai_course_notes.txt",
                "text": "Class Notes: Introduction to Machine Learning and Neural Networks\n\nConcept 1: Supervised Learning\nIn supervised learning, models learn from labeled input-output training pairs. Common algorithms include Linear Regression, Support Vector Machines, and Decision Trees.\n\nConcept 2: Unsupervised Learning & Clustering\nUnsupervised learning discovers hidden patterns in unlabeled data. K-Means clustering and Principal Component Analysis (PCA) are widely applied in market segmentation and dimensionality reduction.\n\nConcept 3: Reinforcement Learning\nAgents optimize cumulative rewards by interacting with dynamic environments via trial, error, and feedback loops.\n\nKey Takeaways:\n1. Data quality is more decisive than raw algorithmic complexity.\n2. Overfitting occurs when models memorize noise rather than generalizable signals."
            })


def run_server():
    server_address = (config.HOST, config.PORT)
    httpd = ThreadingHTTPServer(server_address, AppRequestHandler)
    print(f"================================================================")
    print(f" Multilingual AI Voice Assistant Server running at:")
    print(f" http://{config.HOST}:{config.PORT}")
    print(f" Active Provider: {config.get_active_provider()}")
    print(f" Static Web UI Directory: {config.STATIC_DIR}")
    print(f"================================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server gracefully...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
