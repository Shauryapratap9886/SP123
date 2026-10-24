"""
Intent and Language Interpretation Service.
Parses natural language commands to extract action intent, target language(s),
spoken preferences, and ambiguity status.
"""

import re
from typing import Dict, Any, Optional

# Regex patterns for language detection in user prompt
HINDI_PATTERNS = [
    r"\b(?:in\s+)?hindi\b",
    r"\bhindi\s+me(?:in)?\b",
    r"\bहिंदी\b",
    r"\bहिंदी\s+में\b",
    r"\bshuddh\s+hindi\b"
]

HINGLISH_PATTERNS = [
    r"\b(?:in\s+)?hinglish\b",
    r"\bhinglish\s+me(?:in)?\b",
    r"\bsimple\s+hinglish\b",
    r"\bhindi\s*-\s*english\b",
    r"\broman\s+hindi\b",
    r"\bbolchaal\s+ki\s+hindi\b"
]

ENGLISH_PATTERNS = [
    r"\b(?:in\s+)?english\b",
    r"\benglish\s+me(?:in)?\b",
    r"\bangrezi\b",
    r"\bअंग्रेज़ी\b",
    r"\bअंग्रेजी\b"
]

# Dual output patterns (e.g. "spoken answer in English, but display the key points in Hindi")
DUAL_PATTERN = re.compile(
    r"(?:give\s+me\s+a\s+)?spoken\s+(?:answer|response)\s+in\s+([a-zA-Z]+)[,\s]+but\s+display\s+(?:the\s+)?(?:key\s+points|response|text)\s+in\s+([a-zA-Z]+)",
    re.IGNORECASE
)


def detect_requested_language(query: str, default_preference: str = "auto") -> Dict[str, Optional[str]]:
    """
    Detects if the user explicitly requested a specific output language in their prompt.
    Also handles dual language commands (spoken in X, display in Y).
    """
    query_lower = query.lower()

    # Check for dual language request
    dual_match = DUAL_PATTERN.search(query_lower)
    if dual_match:
        spoken_raw = dual_match.group(1).lower()
        display_raw = dual_match.group(2).lower()
        
        def map_lang(l: str) -> str:
            if "hindi" in l:
                return "hi"
            if "hinglish" in l:
                return "hinglish"
            if "english" in l or "angrezi" in l:
                return "en"
            return l

        return {
            "is_dual": True,
            "spoken_language": map_lang(spoken_raw),
            "display_language": map_lang(display_raw),
            "primary_language": map_lang(display_raw)
        }

    # Check for Hinglish first (before Hindi, since "hinglish" contains "hindi" or sounds similar)
    for p in HINGLISH_PATTERNS:
        if re.search(p, query_lower):
            return {"is_dual": False, "primary_language": "hinglish", "spoken_language": "hinglish", "display_language": "hinglish"}

    # Check for Hindi
    for p in HINDI_PATTERNS:
        if re.search(p, query_lower):
            return {"is_dual": False, "primary_language": "hi", "spoken_language": "hi", "display_language": "hi"}

    # Check for English
    for p in ENGLISH_PATTERNS:
        if re.search(p, query_lower):
            return {"is_dual": False, "primary_language": "en", "spoken_language": "en", "display_language": "en"}

    # Fallback to user selector preference
    resolved_lang = default_preference
    if resolved_lang == "auto" or not resolved_lang:
        resolved_lang = "en"  # Standard default if unspecified

    return {
        "is_dual": False,
        "primary_language": resolved_lang,
        "spoken_language": resolved_lang,
        "display_language": resolved_lang
    }


def parse_intent(query: str, has_attachment: bool = False, attachment_type: Optional[str] = None, preference_lang: str = "auto") -> Dict[str, Any]:
    """
    Analyzes user command intent, output formatting, speech requirement, and ambiguity.
    """
    clean_query = query.strip()
    query_lower = clean_query.lower()

    lang_info = detect_requested_language(clean_query, preference_lang)

    # Detect ambiguity: completely empty query when no attachment exists
    if not clean_query and not has_attachment:
        return {
            "intent": "AMBIGUOUS",
            "is_ambiguous": True,
            "clarification_question": "I didn't receive any text or document. How can I help you today? You can type a question, speak into the mic, or upload a PDF/image.",
            "language_info": lang_info,
            "should_speak": False,
            "target_format": "text"
        }

    # If attachment exists but prompt is empty or just generic "hi/hello"
    if has_attachment and not clean_query:
        if attachment_type == "pdf":
            clean_query = "Please provide an executive summary and key points of this document."
            query_lower = clean_query.lower()
        elif attachment_type == "image":
            clean_query = "Please describe and analyze this image or diagram in detail."
            query_lower = clean_query.lower()

    # Intent classification
    intent = "QUESTION_ANSWER"
    target_format = "markdown"
    should_speak = False

    # Check for explicit read aloud
    if re.search(r"\b(?:read(?:\s+this)?(?:\s+aloud|\s+out\s+loud)?|recite|bol\s+ke\s+batao|sunao|bol\s+kar\s+padho)\b", query_lower):
        intent = "READ_ALOUD"
        should_speak = True
        target_format = "spoken_reading"
    elif re.search(r"\b(?:summariz[a-z]*|summaris[a-z]*|summary|brief|overview|saransh|nichod|convert\s+this\s+paragraph\s+into\s+a\s+simple\s+text\s+summary)\b", query_lower):
        intent = "SUMMARIZE"
        target_format = "bullet_summary"
    elif re.search(r"\b(?:translat[a-z]*|anuvad|tarjuma|convert\s+(?:this\s+)?into\s+(?:hindi|english|hinglish))\b", query_lower):
        intent = "TRANSLATE"
        target_format = "translation"
    elif re.search(r"\b(?:diagram|chart|graph|flowchart|architecture|visual|schematic)\b", query_lower):
        intent = "EXPLAIN_DIAGRAM"
        target_format = "diagram_explanation"
    elif re.search(r"\b(?:formula|equation|math|mathematical|derivation|step\s+by\s+step|calculate)\b", query_lower):
        intent = "EXPLAIN_FORMULA"
        target_format = "step_by_step_math"
    elif re.search(r"\b(?:extract(?:\s+the)?\s+important\s+points|key\s+points|takeaways|bullet\s+points|mukhya\s+bindu|notes)\b", query_lower):
        intent = "EXTRACT_POINTS"
        target_format = "bullet_points"
    
    # Check if speech is requested or implied
    if "spoken" in query_lower or "speak" in query_lower or "awaz" in query_lower or "voice" in query_lower or intent == "READ_ALOUD" or lang_info.get("is_dual"):
        should_speak = True

    return {
        "intent": intent,
        "is_ambiguous": False,
        "clarification_question": None,
        "language_info": lang_info,
        "should_speak": should_speak,
        "target_format": target_format,
        "original_query": clean_query
    }
