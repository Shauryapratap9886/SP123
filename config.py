"""
Configuration module for Multilingual AI Voice Assistant.
Handles environment variables, provider settings, and runtime overrides.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
ENV_FILE = BASE_DIR / ".env"

# Load .env if present
load_dotenv(dotenv_path=ENV_FILE)

# Server Configuration (0.0.0.0 enables access from localhost as well as cloud deployment platforms)
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Provider API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")).strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()

# Runtime configuration store (allows UI settings modal to test or set keys dynamically)
RUNTIME_CONFIG = {
    "gemini_api_key": GEMINI_API_KEY,
    "openai_api_key": OPENAI_API_KEY,
    "sarvam_api_key": SARVAM_API_KEY,
    "preferred_provider": os.getenv("PREFERRED_PROVIDER", "auto").strip().lower()
}

def get_api_key(provider: str) -> str:
    """Retrieve the API key for a specified provider."""
    provider = provider.lower()
    if provider == "gemini":
        return RUNTIME_CONFIG["gemini_api_key"] or os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")).strip()
    elif provider == "openai":
        return RUNTIME_CONFIG["openai_api_key"] or os.getenv("OPENAI_API_KEY", "").strip()
    elif provider == "sarvam":
        return RUNTIME_CONFIG["sarvam_api_key"] or os.getenv("SARVAM_API_KEY", "").strip()
    return ""

def update_runtime_config(gemini_key: str = None, openai_key: str = None, sarvam_key: str = None, provider: str = None):
    """Update runtime configuration dynamically from frontend."""
    if gemini_key is not None:
        RUNTIME_CONFIG["gemini_api_key"] = gemini_key.strip()
    if openai_key is not None:
        RUNTIME_CONFIG["openai_api_key"] = openai_key.strip()
    if sarvam_key is not None:
        RUNTIME_CONFIG["sarvam_api_key"] = sarvam_key.strip()
    if provider is not None:
        RUNTIME_CONFIG["preferred_provider"] = provider.strip().lower()

def get_active_provider() -> str:
    """
    Determine the active AI provider based on preference and available keys:
    Returns 'gemini', 'openai', 'sarvam', or 'builtin'.
    """
    pref = RUNTIME_CONFIG.get("preferred_provider", "auto")
    if pref != "auto":
        key = get_api_key(pref)
        if key or pref == "builtin":
            return pref

    # Auto fallback priority
    if get_api_key("gemini"):
        return "gemini"
    if get_api_key("openai"):
        return "openai"
    if get_api_key("sarvam"):
        return "sarvam"
    return "builtin"

# Supported response languages
SUPPORTED_LANGUAGES = {
    "auto": "Auto Detect",
    "en": "English",
    "hi": "Hindi (हिंदी)",
    "hinglish": "Hinglish (Hindi-English mix)"
}
