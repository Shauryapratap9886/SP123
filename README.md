# Vani AI — Multilingual AI Voice Assistant 🎙️🇮🇳

A modern, responsive, and intelligent multimodal voice assistant web application designed to help users understand, summarize, translate, and transform information from voice, text, PDFs, and images through natural Hindi, Hinglish, and English commands.

---

## 🌟 Key Highlights & Features

### 1. Multimodal Input
- **Voice Interaction:** Speak naturally using the microphone in Hindi, Hinglish, or English with real-time audio animation, timer, and live transcript preview.
- **Natural Language Text:** Type queries, ask follow-up questions, or provide instructions.
- **PDF Document Processing:** Extract and parse text from multi-page documents, lecture slides, scanned papers, and notes.
- **Image & Diagram Understanding:** Upload diagrams, charts, flowcharts, or formulas (PNG, JPG, JPEG, WEBP) for step-by-step visual explanation.
- **Combined Context:** Ask questions grounded in uploaded files (e.g. upload a PDF and say, *"Explain this in simple Hinglish."*).

### 2. Intelligent Command Interpretation
- Interprets user intent dynamically:
  - **Summarization:** *"Summarize this PDF in Hindi."*
  - **Translation:** *"Translate this image into English."*
  - **Diagram Explanation:** *"Explain this diagram in simple Hinglish."*
  - **Read Aloud:** *"Read this document aloud."*
  - **Key Notes Extraction:** *"Extract the important points from these notes."*
  - **Formula Breakdown:** *"Explain this mathematical formula step by step."*
  - **Dual-Language Output:** *"Give me a spoken answer in English, but display the key points in Hindi."*
- **Clarification:** Asks clarifying questions when input is ambiguous or absent.
- **Strict Grounding:** Never invents unreadable text or missing document facts. Clearly separates raw extracted text from AI analysis.

### 3. Multilingual Support
- **Hindi (हिंदी):** Natural Devanagari script responses with tailored Hindi speech synthesis.
- **Hinglish:** Natural conversational code-mixed Hindi & English written in Latin script (e.g., *"Yeh concept machine learning ke liye fundamental hai..."*).
- **English:** Fluent, professional English responses.
- **Input Independence:** User can speak or type in any language while selecting a different output language.

### 4. Spoken Voice & Audio Player
- Play, Pause, Resume, Replay, and Stop controls.
- Playback speed adjustment (0.85x, 1.0x, 1.2x).
- Visual sound-wave equalizer animation during recording and playback.
- Export responses to Markdown (`.md`) with one click.

---

## 🏛️ Technical Architecture

```
multilingual-voice-assistant/
├── app.py                      # Main HTTP server & REST API dispatch
├── config.py                   # Environment configuration & provider settings
├── requirements.txt            # Python dependencies (pypdf, pillow, requests, dotenv)
├── .env.example                # Example environment keys template
├── services/
│   ├── ai_service.py           # Unified AI provider interface (Gemini, OpenAI, Sarvam, Built-in)
│   ├── document_processor.py   # PDF text extraction & image processor
│   ├── intent_parser.py        # Intent classifier & multilingual parser
│   ├── tts_service.py          # Server-side neural TTS (Sarvam Bulbul, OpenAI) & browser guidance
│   └── session_manager.py      # Multi-turn conversation context & memory
├── static/
│   ├── index.html              # Modern, accessible, responsive single-page web UI
│   ├── css/
│   │   └── style.css           # Glassmorphism, animations, dark theme, fluid typography
│   ├── js/
│   │   ├── api.js              # REST API client
│   │   ├── voice.js            # Web Speech API (STT & TTS) controller
│   │   └── app.js              # DOM orchestrator, file uploader, chat rendering
│   └── assets/
│       ├── sample_notes.pdf    # Built-in sample PDF notes for instant testing
│       └── sample_diagram.png  # Built-in sample architecture diagram
└── tests/
    ├── test_document_processor.py
    ├── test_intent_parser.py
    └── test_ai_service.py
```

---

## 🚀 Beginner Quickstart Guide

### Prerequisites
- Python 3.10+ (Python 3.14 recommended)
- A modern web browser (Google Chrome, Microsoft Edge, Brave, or Safari with Web Speech support)

### Step 1: Clone / Navigate to Project Directory
```powershell
cd C:\Users\shaur\.gemini\antigravity\scratch\multilingual-voice-assistant
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: (Optional) Set Up API Keys
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
*(You can also configure API keys dynamically in the running app via the in-app Settings modal!)*

### Step 4: Start the Application Server
```powershell
python app.py
```

### Step 5: Open in Your Browser
Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 🔌 API Providers & Setup Links

| Provider | Purpose | Free Tier Available? | Setup Link |
| :--- | :--- | :---: | :--- |
| **Google Gemini API** *(Recommended)* | Multimodal reasoning, deep vision analysis, document comprehension, Hindi & Hinglish text generation | **Yes** (Generous free tier on AI Studio) | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| **OpenAI API** | GPT-4o-mini reasoning, image vision, Whisper transcription, OpenAI neural TTS | Paid / Free Trial credits | [OpenAI API Keys](https://platform.openai.com/api-keys) |
| **Sarvam AI** | Specialized Indian language LLMs (Sarvam-2B), Saaras STT, Bulbul Indic TTS | Free Trial Tier | [Sarvam AI Platform](https://www.sarvam.ai) |
| **Browser Web Speech** | Zero-latency local speech-to-text and text-to-speech across devices | **100% Free** (No API keys needed) | Built into Chrome, Edge, Safari |
| **Built-in Smart Engine** | Offline document summarization, formula step-by-step breakdown, translation | **100% Free** (Local offline Python logic) | Built-in |

---

## ⚡ What Works Immediately vs. What Needs API Keys

| Feature | Without API Keys (Default / Offline) | With Cloud API Keys (Gemini / OpenAI / Sarvam) |
| :--- | :---: | :---: |
| **Speech-to-Text (Mic Input)** | ✅ Works immediately via Web Speech API | ✅ Works via Web Speech API or Sarvam Saaras |
| **Text-to-Speech (Audio Playback)** | ✅ Works immediately via Browser Synthesis | ✅ Enhanced with Sarvam Bulbul or OpenAI Neural TTS |
| **PDF Text Extraction** | ✅ Full text extraction via `pypdf` | ✅ Full text extraction via `pypdf` |
| **Image & Diagram Analysis** | ✅ Geometry, format & structural heuristics | ✅ Pixel-level multimodal vision & OCR |
| **Hinglish / Hindi / English Output** | ✅ Structured templates & NLP heuristics | ✅ Full generative neural responses |
| **Multi-Turn Conversation Memory** | ✅ Maintained in session memory | ✅ Maintained in session memory |
| **Markdown & Export to File** | ✅ Instant download as `.md` | ✅ Instant download as `.md` |

---

## 🧪 Testing Instructions

### 1. Test Voice Input & Speech-to-Text
1. Click the **Microphone (🎙️)** button.
2. Allow microphone access when prompted by the browser.
3. Speak: *"Explain this in simple Hinglish."*
4. Notice the pulsing listening state, timer, and live transcription.
5. The assistant transcribes your speech and answers aloud.

### 2. Test PDF Document Summarization
1. Click the **Attachment (📎)** paperclip icon or drag-and-drop a PDF.
2. Alternatively, click the quick sample chip: **"📄 Class Notes in Hinglish"**.
3. Type or speak: *"Summarize this PDF in Hindi."*
4. Inspect the separate **"Extracted Document Content"** drawer above the answer, showing raw extracted text.
5. Listen to the spoken Hindi response using the playback toolbar.

### 3. Test Diagram & Image Understanding
1. Upload `static/assets/sample_diagram.png` (or any chart/image).
2. Type or speak: *"Explain this diagram in simple Hinglish."*
3. The assistant identifies components and explains the data flow step by step.

### 4. Test Dual-Language Command
1. Click the quick chip or type:
   `Give me a spoken answer in English, but display the key points in Hindi.`
2. The assistant displays formatted Devanagari Hindi text on screen while speaking in English aloud.

### 5. Test Multi-Turn Follow-Up
1. After uploading notes and getting an explanation, type:
   `Now explain the second concept with an example.`
2. The assistant retrieves previous conversation context and provides a contextual follow-up.

---

## 🛡️ Quality & Privacy Standards
- **Zero Inventions:** Clear distinction between raw extracted text and generated commentary.
- **Client-Side Data Safety:** Document bytes are processed locally in memory.
- **Graceful Fallbacks:** In-app status indicators immediately communicate if a permission is denied or an external service is unavailable.
