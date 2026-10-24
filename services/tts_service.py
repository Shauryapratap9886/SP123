"""
Text-to-Speech (TTS) Service.
Integrates with Sarvam AI Bulbul TTS, OpenAI TTS, and guides client-side SpeechSynthesis.
"""

import base64
import logging
import requests
import config

logger = logging.getLogger(__name__)


def synthesize_speech_server(text: str, language: str = "en", preferred_provider: str = "auto") -> dict:
    """
    Synthesize audio using external cloud TTS if configured.
    Returns:
        {"success": True, "audio_base64": str, "mime_type": "audio/mp3", "provider": str}
        or {"success": False, "use_browser_speech": True, "message": str}
    """
    clean_text = text[:1500].strip()
    if not clean_text:
        return {"success": False, "error": "Empty text for speech synthesis"}

    sarvam_key = config.get_api_key("sarvam")
    openai_key = config.get_api_key("openai")

    # Priority 1: Sarvam AI for Hindi / Hinglish if key available
    if (language in ["hi", "hinglish"] or preferred_provider == "sarvam") and sarvam_key:
        try:
            target_lang_code = "hi-IN" if language == "hi" else "en-IN"
            url = "https://api.sarvam.ai/text-to-speech"
            headers = {
                "api-subscription-key": sarvam_key,
                "Content-Type": "application/json"
            }
            payload = {
                "inputs": [clean_text],
                "target_language_code": target_lang_code,
                "speaker": "meera",
                "pitch": 0,
                "pace": 1.0,
                "loudness": 1.0,
                "speech_sample_rate": 22050,
                "enable_preprocessing": True,
                "model": "bulbul:v1"
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                audios = data.get("audios", [])
                if audios:
                    return {
                        "success": True,
                        "audio_base64": audios[0],
                        "mime_type": "audio/wav",
                        "provider": "Sarvam AI Bulbul TTS"
                    }
        except Exception as e:
            logger.warning(f"Sarvam TTS failed, falling back: {e}")

    # Priority 2: OpenAI TTS if key available
    if openai_key and preferred_provider in ["auto", "openai"]:
        try:
            url = "https://api.openai.com/v1/audio/speech"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "tts-1",
                "input": clean_text,
                "voice": "alloy"
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=25)
            if resp.status_code == 200:
                audio_b64 = base64.b64encode(resp.content).decode("utf-8")
                return {
                    "success": True,
                    "audio_base64": audio_b64,
                    "mime_type": "audio/mp3",
                    "provider": "OpenAI TTS"
                }
        except Exception as e:
            logger.warning(f"OpenAI TTS failed, falling back: {e}")

    # Fallback to browser-native Web Speech Synthesis API
    return {
        "success": False,
        "use_browser_speech": True,
        "language": language,
        "message": "Use browser Web Speech API for zero-latency local speech synthesis."
    }
