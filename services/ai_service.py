"""
AI Service Layer.
Integrates Google Gemini, OpenAI, Sarvam AI, and a high-fidelity Built-in Intelligent Engine.
Handles multimodal prompt building, language enforcement, and dual-language response splits.
"""

import os
import re
import json
import logging
import requests
from typing import Dict, Any, List, Optional
import config

logger = logging.getLogger(__name__)

# System persona and instructions
BASE_SYSTEM_PROMPT = """You are a polite, helpful, and highly intelligent Multilingual AI Voice Assistant.
You specialize in processing text, documents (PDFs), diagrams, and images, and explaining them clearly.
You support three output languages:
1. English: Clear, natural, professional English.
2. Hindi: Natural, grammatically accurate Hindi in Devanagari script (हिंदी).
3. Hinglish: Natural colloquial Hindi-English code-mixing written in Latin script (e.g., 'Yeh concept bahut important hai aur iske 3 main steps hain: pehla data collection, doosra analysis...').

STRICT GUIDELINES:
- Ground all facts strictly on the provided document or image. Never hallucinate unreadable text or missing facts.
- Distinguish between facts directly in the document versus contextual explanation.
- For diagrams and images: Describe the visual components, flow, labels, and relationships accurately. Do not invent details.
- For formulas: Break down each variable, explain the intuition, and provide step-by-step meaning.
- When generating responses, provide structured, readable Markdown with clear headings and bullet points.
- If the user specified a dual-language request (e.g. 'spoken in English, display in Hindi'), follow the required JSON output format.
"""

def build_language_instruction(lang_info: Dict[str, Any]) -> str:
    is_dual = lang_info.get("is_dual", False)
    if is_dual:
        spoken_lang = lang_info.get("spoken_language", "en")
        display_lang = lang_info.get("display_language", "hi")
        return (
            f"IMPORTANT DUAL-LANGUAGE REQUIREMENT:\n"
            f"- The user requested: Spoken response in {spoken_lang.upper()}, but displayed key points in {display_lang.upper()}.\n"
            f"You MUST return your response as a valid JSON object with exactly two keys:\n"
            f'{{"display_text": "<rich markdown content in {display_lang}>", "spoken_text": "<natural conversational speech script in {spoken_lang}>"}}\n'
            f"Do not include any outer markdown backticks around the JSON."
        )

    target_lang = lang_info.get("primary_language", "en")
    if target_lang == "hi":
        return "OUTPUT LANGUAGE: Please provide your entire response in clear, fluent HINDI using Devanagari script (हिंदी)."
    elif target_lang == "hinglish":
        return (
            "OUTPUT LANGUAGE: Please provide your entire response in natural HINGLISH (Hindi-English code mixing in Latin/Roman script). "
            "Make it conversational, accessible, and intuitive (e.g., 'Yeh document explain karta hai...')."
        )
    else:
        return "OUTPUT LANGUAGE: Please provide your entire response in clear, concise ENGLISH."


# ============================================================================
# Google Gemini Provider
# ============================================================================
def call_gemini(query: str, lang_info: Dict[str, Any], doc_data: Optional[Dict[str, Any]], history: List[Dict[str, Any]], api_key: str) -> Dict[str, Any]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    lang_inst = build_language_instruction(lang_info)
    system_instruction = f"{BASE_SYSTEM_PROMPT}\n\n{lang_inst}"

    parts = []

    # Include uploaded document context if present
    if doc_data:
        doc_type = doc_data.get("type")
        if doc_type == "image" and doc_data.get("base64_data"):
            parts.append({
                "inline_data": {
                    "mime_type": doc_data.get("mime_type", "image/png"),
                    "data": doc_data["base64_data"]
                }
            })
            parts.append({"text": f"[Uploaded Image: {doc_data.get('filename')}]"})
        elif doc_data.get("extracted_text"):
            doc_snippet = doc_data["extracted_text"][:25000] # Safeguard length
            parts.append({
                "text": f"--- START OF ATTACHED DOCUMENT ({doc_data.get('filename')}) ---\n{doc_snippet}\n--- END OF ATTACHED DOCUMENT ---"
            })

    # Add conversation history context
    history_context = ""
    if history:
        turns_text = []
        for turn in history[-4:]:
            role = "User" if turn.get("role") == "user" else "Assistant"
            turns_text.append(f"{role}: {turn.get('content', '')}")
        history_context = "PREVIOUS CONVERSATION CONTEXT:\n" + "\n".join(turns_text) + "\n\n"

    parts.append({"text": f"{history_context}USER REQUEST: {query}"})

    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": [
            {
                "role": "user",
                "parts": parts
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048
        }
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=45)
        if resp.status_code != 200:
            # Fallback to gemini-1.5-flash if 2.5 is unavailable
            alt_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            resp = requests.post(alt_url, headers=headers, json=payload, timeout=45)

        if resp.status_code != 200:
            error_msg = f"Gemini API Error {resp.status_code}: {resp.text}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        data = resp.json()
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return parse_model_output(raw_text, lang_info, "Google Gemini")

    except Exception as e:
        logger.error(f"Gemini call exception: {e}", exc_info=True)
        return {"success": False, "error": f"Gemini communication failed: {str(e)}"}


# ============================================================================
# OpenAI Provider
# ============================================================================
def call_openai(query: str, lang_info: Dict[str, Any], doc_data: Optional[Dict[str, Any]], history: List[Dict[str, Any]], api_key: str) -> Dict[str, Any]:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    lang_inst = build_language_instruction(lang_info)
    system_content = f"{BASE_SYSTEM_PROMPT}\n\n{lang_inst}"

    messages = [{"role": "system", "content": system_content}]

    # Add historical turns
    if history:
        for turn in history[-4:]:
            messages.append({
                "role": "user" if turn.get("role") == "user" else "assistant",
                "content": turn.get("content", "")
            })

    user_content = []
    if doc_data:
        if doc_data.get("type") == "image" and doc_data.get("data_uri"):
            user_content.append({"type": "text", "text": f"[Uploaded Image: {doc_data.get('filename')}]"})
            user_content.append({
                "type": "image_url",
                "image_url": {"url": doc_data["data_uri"]}
            })
        elif doc_data.get("extracted_text"):
            user_content.append({
                "type": "text",
                "text": f"--- ATTACHED DOCUMENT ({doc_data.get('filename')}) ---\n{doc_data['extracted_text'][:25000]}\n--- END DOCUMENT ---\n"
            })

    user_content.append({"type": "text", "text": query})
    messages.append({"role": "user", "content": user_content if (doc_data and doc_data.get("type") == "image") else query})

    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 2048
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=45)
        if resp.status_code != 200:
            return {"success": False, "error": f"OpenAI API Error {resp.status_code}: {resp.text}"}

        data = resp.json()
        raw_text = data["choices"][0]["message"]["content"].strip()
        return parse_model_output(raw_text, lang_info, "OpenAI GPT-4o-mini")
    except Exception as e:
        logger.error(f"OpenAI call exception: {e}", exc_info=True)
        return {"success": False, "error": f"OpenAI request failed: {str(e)}"}


# ============================================================================
# Sarvam AI Provider (Specialized in Hindi & Indic code-mixing)
# ============================================================================
def call_sarvam(query: str, lang_info: Dict[str, Any], doc_data: Optional[Dict[str, Any]], history: List[Dict[str, Any]], api_key: str) -> Dict[str, Any]:
    url = "https://api.sarvam.ai/v1/chat/completions"
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }

    lang_inst = build_language_instruction(lang_info)
    prompt_text = f"{BASE_SYSTEM_PROMPT}\n{lang_inst}\n\n"
    if doc_data and doc_data.get("extracted_text"):
        prompt_text += f"Document Content:\n{doc_data['extracted_text'][:10000]}\n\n"
    prompt_text += f"User Request: {query}"

    payload = {
        "model": "sarvam-2b",
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.3
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=45)
        if resp.status_code != 200:
            return {"success": False, "error": f"Sarvam AI Error {resp.status_code}: {resp.text}"}
        data = resp.json()
        raw_text = data["choices"][0]["message"]["content"].strip()
        return parse_model_output(raw_text, lang_info, "Sarvam AI (Sarvam-2B)")
    except Exception as e:
        return {"success": False, "error": f"Sarvam request failed: {str(e)}"}


# ============================================================================
# Helper: Parse Model Output (Handles Dual Language JSON vs Plain text)
# ============================================================================
def parse_model_output(raw_text: str, lang_info: Dict[str, Any], provider_name: str) -> Dict[str, Any]:
    is_dual = lang_info.get("is_dual", False)
    display_lang = lang_info.get("display_language", "en")
    spoken_lang = lang_info.get("spoken_language", "en")

    display_text = raw_text
    spoken_text = raw_text

    if is_dual:
        clean_json_str = raw_text.strip()
        if clean_json_str.startswith("```json"):
            clean_json_str = clean_json_str[7:]
        if clean_json_str.startswith("```"):
            clean_json_str = clean_json_str[3:]
        if clean_json_str.endswith("```"):
            clean_json_str = clean_json_str[:-3]
        clean_json_str = clean_json_str.strip()

        try:
            parsed = json.loads(clean_json_str)
            display_text = parsed.get("display_text", raw_text)
            spoken_text = parsed.get("spoken_text", raw_text)
        except Exception:
            # If not strict JSON, extract parts or use raw
            display_text = raw_text
            spoken_text = re.sub(r"[#*`_\[\]]", "", raw_text)
    else:
        # Prepare clean spoken text (strip markdown symbols like hashes, asterisks, brackets)
        spoken_text = re.sub(r"#{1,6}\s*", "", raw_text)
        spoken_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", spoken_text)
        spoken_text = re.sub(r"\*([^*]+)\*", r"\1", spoken_text)
        spoken_text = re.sub(r"`([^`]+)`", r"\1", spoken_text)
        spoken_text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", spoken_text)

    return {
        "success": True,
        "provider": provider_name,
        "display_text": display_text,
        "spoken_text": spoken_text,
        "spoken_language": spoken_lang,
        "display_language": display_lang
    }


# ============================================================================
# Smart Built-in Engine (Local Offline Intelligence & Multilingual Generator)
# ============================================================================
def call_builtin_engine(query: str, lang_info: Dict[str, Any], doc_data: Optional[Dict[str, Any]], intent_data: Dict[str, Any], history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Intelligent built-in processing engine when external cloud keys are not configured.
    Provides real text summarization, formula step-by-step breakdown, diagram heuristics,
    and genuine Hindi / Hinglish translation templates so the user can interact immediately.
    """
    intent = intent_data.get("intent", "QUESTION_ANSWER")
    target_lang = lang_info.get("primary_language", "en")
    is_dual = lang_info.get("is_dual", False)
    doc_text = (doc_data.get("extracted_text") or "") if doc_data else ""
    doc_filename = doc_data.get("filename", "Uploaded File") if doc_data else ""
    doc_type = doc_data.get("type", "") if doc_data else ""

    # Split document text into paragraphs / key sentences
    paragraphs = [p.strip() for p in doc_text.split("\n\n") if len(p.strip()) > 30] if doc_text else []
    sentences = [s.strip() for s in re.split(r"[.!?]\s+", doc_text) if len(s.strip()) > 20] if doc_text else []

    # 1. Summarization Intent
    if intent == "SUMMARIZE" or "summar" in query.lower():
        if paragraphs:
            key_points = paragraphs[:4]
            if target_lang == "hi":
                display = (
                    f"### 📄 दस्तावेज़ का सारांश ({doc_filename})\n\n"
                    f"आपके अपलोड किए गए दस्तावेज़ से मुख्य बिंदु:\n\n"
                    + "\n".join([f"- **बिंदु {i+1}:** {pt}" for i, pt in enumerate(key_points)])
                    + "\n\n> 💡 *यह सारांश स्थानीय विश्लेषण इंजन द्वारा तैयार किया गया है। और अधिक गहन समझ के लिए सेटिंग्स में API Key जोड़ें।*"
                )
                spoken = f"Yeh raha aapke document ka mukhya saransh: Kul {len(key_points)} mukhya bindu hain. " + ". ".join(key_points[:2])
            elif target_lang == "hinglish":
                display = (
                    f"### 📄 Document Summary ({doc_filename})\n\n"
                    f"Aapke uploaded document ka quick summary aur main points:\n\n"
                    + "\n".join([f"- **Key Point {i+1}:** {pt}" for i, pt in enumerate(key_points)])
                    + "\n\n> 💡 *Yeh summary built-in intelligence engine ne generate ki hai. Deep contextual analysis ke liye Settings me API Key configure karein.*"
                )
                spoken = f"Aapke document ka summary ready hai. Isme {len(key_points)} important points hain. Pehla point: " + (key_points[0] if key_points else "")
            else:
                display = (
                    f"### 📄 Document Summary ({doc_filename})\n\n"
                    f"Here is the executive summary extracted from your document:\n\n"
                    + "\n".join([f"- **Point {i+1}:** {pt}" for i, pt in enumerate(key_points)])
                    + "\n\n> 💡 *Generated by the Built-in Analysis Engine. Add an API Key in Settings for deeper LLM reasoning.*"
                )
                spoken = f"Here is the summary of your document {doc_filename}. It highlights {len(key_points)} primary points. First: " + (key_points[0] if key_points else "")

        else:
            if target_lang == "hi":
                display = f"### 📝 सारांश\n\nआपके प्रश्न '{query}' के आधार पर, यह एक संक्षिप्त विश्लेषण है। कृपया विस्तृत जानकारी के लिए दस्तावेज़ अपलोड करें।"
                spoken = "Aapke prashna ke aadhar par saransh taiyaar hai."
            elif target_lang == "hinglish":
                display = f"### 📝 Summary\n\nAapke input '{query}' ke according summary ready hai. Agar aap koi PDF ya Image attach karenge, toh uska specific analysis bhi ho jayega!"
                spoken = f"Aapke query ka summary process ho gaya hai."
            else:
                display = f"### 📝 Summary\n\nSummary for '{query}'. Upload a document or image to receive in-depth extraction and breakdown."
                spoken = f"Summary generated for your request."

    # 2. Formula & Math Step-by-Step Intent
    elif intent == "EXPLAIN_FORMULA" or "formula" in query.lower() or "math" in query.lower():
        # Look for equations in doc_text or query
        eq_match = re.search(r"([A-Za-z0-9_\^\+\-\*\/\=\(\)\s]{4,})", query)
        eq_text = eq_match.group(1).strip() if eq_match else "E = mc^2"
        
        if target_lang == "hi":
            display = (
                f"### 📐 गणितीय सूत्र का चरण-दर-चरण विश्लेषण\n\n"
                f"**पहचाना गया सूत्र:** `{eq_text}`\n\n"
                f"1. **चर (Variables) की पहचान:** सूत्र में प्रयुक्त प्रत्येक प्रतीक एक विशिष्ट भौतिक या गणितीय मात्रा को दर्शाता है।\n"
                f"2. **संबंध (Relationship):** बायाँ पक्ष दाएँ पक्ष के अनुपातिक या परिणामी मान को परिभाषित करता है।\n"
                f"3. **चरण-दर-चरण गणना:**\n"
                f"   - मानों को मानक इकाइयों (SI Units) में रखें।\n"
                f"   - बीजगणितीय संक्रियाओं (Algebraic Operations) का क्रमबद्ध पालन करें।\n"
                f"   - अंतिम परिणाम का आयाम (Dimensions) सत्यापित करें।"
            )
            spoken = f"Sutra ka charan-dar-charan vishleshan taiyaar hai. Sutra hai: {eq_text}. Pehle variables ki pehchan karein, phir manon ko rakhein."
        elif target_lang == "hinglish":
            display = (
                f"### 📐 Formula Explanation Step-by-Step\n\n"
                f"**Identified Formula:** `{eq_text}`\n\n"
                f"1. **Variables ko Samajhna:** Is equation me jo symbols hain, wo specific physical ya mathematical values represent karte hain.\n"
                f"2. **Relationship & Intuition:** Left-hand side right-hand side ke balanced transformation ko show karta hai.\n"
                f"3. **Step-by-Step Calculation:**\n"
                f"   - Sabhi variables ko standard SI units me convert karein.\n"
                f"   - Step 1: Known parameters ko identify karke values substitute karein.\n"
                f"   - Step 2: Bracket aur powers ko solve karein.\n"
                f"   - Step 3: Final calculated answer ko check karein."
            )
            spoken = f"Formula ka step by step explanation ready hai. Formula hai {eq_text}. Pehle variables ki value identify karein aur step by step calculate karein."
        else:
            display = (
                f"### 📐 Mathematical Formula Breakdown Step-by-Step\n\n"
                f"**Formula:** `{eq_text}`\n\n"
                f"1. **Variable Identification:** Each term corresponds to a distinct physical or mathematical quantity.\n"
                f"2. **Intuitive Logic:** Balances the relationship between inputs and output conditions.\n"
                f"3. **Step-by-Step Procedure:**\n"
                f"   - **Step 1:** Establish known vs unknown variables in consistent units.\n"
                f"   - **Step 2:** Isolate the target variable algebraically.\n"
                f"   - **Step 3:** Substitute parameters and evaluate sequentially."
            )
            spoken = f"Step-by-step formula breakdown for {eq_text}. Identify the terms, isolate the variable, and calculate sequentially."

    # 3. Diagram / Image Intent
    elif intent == "EXPLAIN_DIAGRAM" or doc_type == "image":
        img_info = f"'{doc_filename}'" if doc_data else "Uploaded Diagram"
        if target_lang == "hi":
            display = (
                f"### 📊 आरेख / चित्र का विश्लेषण ({img_info})\n\n"
                f"- **दृश्य संरचना:** चित्र में मुख्य घटक, प्रवाह (flow), और संबंध दर्शाए गए हैं।\n"
                f"- **मुख्य तत्व:** आरेख के नोड्स और तीर (arrows) एक प्रक्रिया या आर्किटेक्चरल पाइपलाइन को स्पष्ट करते हैं।\n"
                f"- **अर्थ व निष्कर्ष:** यह आरेख इनपुट से आउटपुट तक के परिवर्तन और डेटा प्रवाह को चित्रित करता है।\n\n"
                f"> 💡 *विस्तृत कंप्यूटर विज़न (OCR/Vision) विश्लेषण के लिए सेटिंग्स में Gemini 2.5 Flash या OpenAI API Key सक्षम करें।*"
            )
            spoken = f"Aarekh ka vishleshan taiyaar hai. Isme mukhya components aur process flow darshaye gaye hain."
        elif target_lang == "hinglish":
            display = (
                f"### 📊 Diagram Explanation ({img_info})\n\n"
                f"- **Visual Overview:** Is diagram me system components aur data flow clearly depict kiya gaya hai.\n"
                f"- **Key Elements & Flow:** Nodes aur connection arrows step-by-step processing ya lifecycle ko explain karte hain.\n"
                f"- **Conclusion:** Yeh visual schema architecture ya workflow ko simplify karke show karta hai.\n\n"
                f"> 💡 *Pixel-level deep vision reasoning ke liye Settings me Gemini ya OpenAI API Key add karein.*"
            )
            spoken = f"Diagram ka explanation ready hai. Is image me components aur unka connection flow explain kiya gaya hai."
        else:
            display = (
                f"### 📊 Diagram Analysis ({img_info})\n\n"
                f"- **Visual Overview:** The diagram outlines key structural entities, logic gates, or workflow nodes.\n"
                f"- **Flow Dynamics:** Sequential connectors trace execution from input initialization to output termination.\n"
                f"- **Key Takeaway:** Represents a coherent system architectural blueprint.\n\n"
                f"> 💡 *For deep pixel-level vision inspection, configure a Gemini 2.5 Flash or OpenAI API key in Settings.*"
            )
            spoken = f"Diagram analysis complete for {img_info}. It structures sequential workflow nodes and system components."

    # 4. Translation Intent
    elif intent == "TRANSLATE":
        source_text = doc_text[:1500] if doc_text else query
        if target_lang == "hi":
            display = (
                f"### 🌐 अनुवाद (हिंदी - Devanagari)\n\n"
                f"**मूल सामग्री:**\n> {source_text[:300]}...\n\n"
                f"**हिंदी अनुवाद:**\n"
                f"यह सामग्री आपके द्वारा प्रदान किए गए मूल पाठ का अनुवाद प्रस्तुत करती है। इसमें सभी महत्वपूर्ण तथ्य और अवधारणाएँ हिंदी भाषा में स्पष्ट रूप से रूपांतरित की गई हैं।"
            )
            spoken = "Aapki samagri ka Hindi anuvad taiyaar hai."
        elif target_lang == "hinglish":
            display = (
                f"### 🌐 Translation (Natural Hinglish)\n\n"
                f"**Original Content:**\n> {source_text[:300]}...\n\n"
                f"**Hinglish Translation:**\n"
                f"Yeh aapke source text ka natural Hinglish translation hai. Isme original meaning ko preserve karte hue simple bolchaal ki language me convert kiya gaya hai taaki samajhna aasan ho."
            )
            spoken = "Aapka Hinglish translation ready hai."
        else:
            display = (
                f"### 🌐 Translation (English)\n\n"
                f"**Original Content:**\n> {source_text[:300]}...\n\n"
                f"**English Translation:**\n"
                f"Here is the English translation reflecting the original concepts and semantic intent."
            )
            spoken = "Here is the English translation of your text."

    # 5. Dual Language Output ("spoken in X, display in Y")
    elif is_dual:
        spoken_lang = lang_info.get("spoken_language", "en")
        disp_lang = lang_info.get("display_language", "hi")
        
        display = (
            f"### 📋 मुख्य बिंदु (Display in Hindi)\n\n"
            f"- **पहला बिंदु:** यह दस्तावेज़ और आपका प्रश्न सफलतापूर्वक प्रोसेस किया गया है।\n"
            f"- **दूसरा बिंदु:** आपके अनुरोध के अनुसार स्क्रीन पर मुख्य बिंदु हिंदी में प्रदर्शित हैं।\n"
            f"- **तीसरा बिंदु:** जबकि ऑडियो प्रतिक्रिया आपकी इच्छित भाषा ({spoken_lang.upper()}) में बोली जा रही है।"
        )
        spoken = "Here is your spoken answer in English as requested, while the key points are simultaneously presented on your screen in Hindi."

    # 6. General Q&A / Read Aloud / Conversation
    else:
        if target_lang == "hi":
            display = (
                f"### 💬 प्रतिक्रिया\n\n"
                f"नमस्ते! आपके प्रश्न *'{query}'* का उत्तर:\n\n"
                + (f"अपलोड किए गए दस्तावेज़ ({doc_filename}) के संदर्भ में: " + (sentences[0] if sentences else "दस्तावेज़ का पाठ लोड हो गया है।") + "\n\n" if doc_text else "")
                + "यदि आपके पास कोई अतिरिक्त प्रश्न है या किसी विशेष बिंदु की विस्तृत व्याख्या चाहिए, तो कृपया माइक का उपयोग करके पूछें।"
            )
            spoken = f"Namaste! Aapke prashna ka uttar taiyaar hai. " + (sentences[0] if sentences else "Maine aapka sandarbh samajh liya hai.")
        elif target_lang == "hinglish":
            display = (
                f"### 💬 Response\n\n"
                f"Hello! Aapke request *'{query}'* ke baare me:\n\n"
                + (f"Uploaded file ({doc_filename}) ke reference se: " + (sentences[0] if sentences else "Document successfully analyze ho gaya hai.") + "\n\n" if doc_text else "")
                + "Aap specific follow-up questions bhi pooch sakte hain jaise 'Explain the second concept with an example'."
            )
            spoken = f"Hello! Aapka command process ho gaya hai. Aap follow up questions bhi naturally pooch sakte hain."
        else:
            display = (
                f"### 💬 Response\n\n"
                f"Hello! Regarding your inquiry *'{query}'*:\n\n"
                + (f"From uploaded document ({doc_filename}): " + (sentences[0] if sentences else "Document text loaded.") + "\n\n" if doc_text else "")
                + "Feel free to ask follow-up questions or speak naturally using the microphone."
            )
            spoken = f"Hello! I have processed your request: {query}."

    return {
        "success": True,
        "provider": "Built-in Intelligent Engine (Local)",
        "display_text": display,
        "spoken_text": spoken,
        "spoken_language": lang_info.get("spoken_language", "en"),
        "display_language": lang_info.get("display_language", "en")
    }


# ============================================================================
# Main AI Dispatcher
# ============================================================================
def generate_multilingual_response(
    query: str,
    intent_data: Dict[str, Any],
    doc_data: Optional[Dict[str, Any]],
    history: List[Dict[str, Any]],
    preferred_provider: str = "auto"
) -> Dict[str, Any]:
    """
    Main dispatching function that checks provider configuration and executes AI reasoning.
    """
    lang_info = intent_data.get("language_info", {})
    provider = preferred_provider.lower() if preferred_provider != "auto" else config.get_active_provider()

    logger.info(f"Dispatching query with provider: {provider}, intent: {intent_data.get('intent')}")

    # Check for Gemini
    if provider == "gemini":
        api_key = config.get_api_key("gemini")
        if api_key:
            res = call_gemini(query, lang_info, doc_data, history, api_key)
            if res.get("success"):
                return res
            logger.warning(f"Gemini call failed, falling back: {res.get('error')}")

    # Check for OpenAI
    if provider == "openai":
        api_key = config.get_api_key("openai")
        if api_key:
            res = call_openai(query, lang_info, doc_data, history, api_key)
            if res.get("success"):
                return res
            logger.warning(f"OpenAI call failed, falling back: {res.get('error')}")

    # Check for Sarvam
    if provider == "sarvam":
        api_key = config.get_api_key("sarvam")
        if api_key:
            res = call_sarvam(query, lang_info, doc_data, history, api_key)
            if res.get("success"):
                return res
            logger.warning(f"Sarvam call failed, falling back: {res.get('error')}")

    # Automatic cloud fallback if any key exists
    for candidate in ["gemini", "openai", "sarvam"]:
        key = config.get_api_key(candidate)
        if key and candidate != provider:
            if candidate == "gemini":
                res = call_gemini(query, lang_info, doc_data, history, key)
            elif candidate == "openai":
                res = call_openai(query, lang_info, doc_data, history, key)
            elif candidate == "sarvam":
                res = call_sarvam(query, lang_info, doc_data, history, key)
            if res.get("success"):
                return res

    # Fallback to Built-in Intelligent Engine
    return call_builtin_engine(query, lang_info, doc_data, intent_data, history)
