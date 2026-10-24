/**
 * Voice Interaction Service: Speech-to-Text (STT) and Text-to-Speech (TTS)
 */

class VoiceController {
  constructor() {
    this.recognition = null;
    this.isRecording = false;
    this.speechSynthesis = window.speechSynthesis || null;
    this.currentUtterance = null;
    this.audioElement = null; // for server-synthesized audio playback
    this.availableVoices = [];
    this.playbackState = "stopped"; // 'playing', 'paused', 'stopped'
    this.activeMessageId = null;

    this.onRecordingStart = null;
    this.onInterimResult = null;
    this.onFinalResult = null;
    this.onRecordingEnd = null;
    this.onError = null;

    this.onPlaybackStateChange = null;

    this.initRecognition();
    this.initSynthesis();
  }

  // =========================================================================
  // Speech Recognition (STT)
  // =========================================================================
  initRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn("SpeechRecognition API is not supported in this browser.");
      return;
    }

    this.recognition = new SpeechRecognition();
    this.recognition.continuous = false;
    this.recognition.interimResults = true;
    this.recognition.maxAlternatives = 1;

    this.recognition.onstart = () => {
      this.isRecording = true;
      if (this.onRecordingStart) this.onRecordingStart();
    };

    this.recognition.onresult = (event) => {
      let interim = "";
      let finalTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interim += event.results[i][0].transcript;
        }
      }

      if (interim && this.onInterimResult) {
        this.onInterimResult(interim);
      }
      if (finalTranscript && this.onFinalResult) {
        this.onFinalResult(finalTranscript.trim());
      }
    };

    this.recognition.onerror = (event) => {
      console.error("Speech Recognition Error:", event.error);
      this.isRecording = false;
      let msg = "Microphone error: " + event.error;
      if (event.error === "not-allowed") {
        msg = "Microphone access was denied. Please allow microphone permissions in your browser.";
      } else if (event.error === "no-speech") {
        msg = "No speech detected. Please speak into your microphone.";
      }
      if (this.onError) this.onError(msg, event.error);
    };

    this.recognition.onend = () => {
      this.isRecording = false;
      if (this.onRecordingEnd) this.onRecordingEnd();
    };
  }

  startListening(language = "auto") {
    if (!this.recognition) {
      if (this.onError) this.onError("Speech recognition is not supported in this browser. Please type your query.");
      return;
    }

    if (this.isRecording) {
      this.stopListening();
      return;
    }

    // Stop any ongoing speech playback before listening
    this.stopSpeaking();

    // Configure language code
    if (language === "hi") {
      this.recognition.lang = "hi-IN";
    } else if (language === "hinglish") {
      this.recognition.lang = "en-IN"; // en-IN handles Indian accent and Hinglish code mixing best
    } else {
      this.recognition.lang = "en-US";
    }

    try {
      this.recognition.start();
    } catch (e) {
      console.warn("Recognition start error:", e);
    }
  }

  stopListening() {
    if (this.recognition && this.isRecording) {
      this.recognition.stop();
      this.isRecording = false;
    }
  }

  // =========================================================================
  // Speech Synthesis (TTS)
  // =========================================================================
  initSynthesis() {
    if (!this.speechSynthesis) return;

    const loadVoices = () => {
      this.availableVoices = this.speechSynthesis.getVoices();
    };

    loadVoices();
    if (speechSynthesis.onvoiceschanged !== undefined) {
      speechSynthesis.onvoiceschanged = loadVoices;
    }
  }

  getBestVoice(language) {
    if (!this.availableVoices || this.availableVoices.length === 0) {
      this.availableVoices = this.speechSynthesis ? this.speechSynthesis.getVoices() : [];
    }

    if (language === "hi") {
      // Find Hindi voice
      const hiVoice = this.availableVoices.find(v => v.lang.startsWith("hi") || v.name.toLowerCase().includes("hindi") || v.name.toLowerCase().includes("devanagari"));
      if (hiVoice) return hiVoice;
    }

    if (language === "hinglish") {
      // Find Indian English voice
      const indVoice = this.availableVoices.find(v => v.lang === "en-IN" || v.name.toLowerCase().includes("india"));
      if (indVoice) return indVoice;
    }

    // Default to natural English voice
    const enVoice = this.availableVoices.find(v => v.lang.startsWith("en") && (v.name.includes("Google") || v.name.includes("Natural") || v.name.includes("Samantha")));
    return enVoice || this.availableVoices.find(v => v.lang.startsWith("en")) || this.availableVoices[0];
  }

  speak(text, language = "en", messageId = null, rate = 1.0, serverAudio = null) {
    this.stopSpeaking();

    // If server provided pre-synthesized audio (e.g. from Sarvam Bulbul or OpenAI TTS)
    if (serverAudio && serverAudio.audio_base64) {
      try {
        const audioSrc = `data:${serverAudio.mime_type || "audio/mp3"};base64,${serverAudio.audio_base64}`;
        this.audioElement = new Audio(audioSrc);
        this.audioElement.playbackRate = rate;
        this.activeMessageId = messageId;
        this.playbackState = "playing";

        if (this.onPlaybackStateChange) {
          this.onPlaybackStateChange("playing", messageId);
        }

        this.audioElement.onended = () => {
          this.playbackState = "stopped";
          this.activeMessageId = null;
          if (this.onPlaybackStateChange) this.onPlaybackStateChange("stopped", messageId);
        };

        this.audioElement.onerror = (e) => {
          console.warn("Audio element playback failed, falling back to browser synthesis", e);
          this.speakBrowserSynthesis(text, language, messageId, rate);
        };

        this.audioElement.play();
        return;
      } catch (err) {
        console.warn("Server audio playback failed, falling back to browser speech synthesis", err);
      }
    }

    this.speakBrowserSynthesis(text, language, messageId, rate);
  }

  speakBrowserSynthesis(text, language, messageId, rate) {
    if (!this.speechSynthesis) {
      console.warn("SpeechSynthesis not available.");
      return;
    }

    // Clean text of leftover markdown symbols
    const clean = text
      .replace(/[#*`_~\[\]]/g, "")
      .replace(/https?:\/\/\S+/g, "")
      .trim();

    if (!clean) return;

    this.currentUtterance = new SpeechSynthesisUtterance(clean);
    this.currentUtterance.rate = rate;
    this.currentUtterance.pitch = 1.0;

    const matchedVoice = this.getBestVoice(language);
    if (matchedVoice) {
      this.currentUtterance.voice = matchedVoice;
      this.currentUtterance.lang = matchedVoice.lang;
    } else {
      this.currentUtterance.lang = language === "hi" ? "hi-IN" : "en-US";
    }

    this.activeMessageId = messageId;
    this.playbackState = "playing";

    this.currentUtterance.onstart = () => {
      this.playbackState = "playing";
      if (this.onPlaybackStateChange) this.onPlaybackStateChange("playing", messageId);
    };

    this.currentUtterance.onend = () => {
      this.playbackState = "stopped";
      this.activeMessageId = null;
      if (this.onPlaybackStateChange) this.onPlaybackStateChange("stopped", messageId);
    };

    this.currentUtterance.onerror = (e) => {
      console.warn("Speech synthesis utterance error:", e);
      this.playbackState = "stopped";
      this.activeMessageId = null;
      if (this.onPlaybackStateChange) this.onPlaybackStateChange("stopped", messageId);
    };

    this.speechSynthesis.speak(this.currentUtterance);
  }

  pauseSpeaking() {
    if (this.audioElement && !this.audioElement.paused) {
      this.audioElement.pause();
      this.playbackState = "paused";
      if (this.onPlaybackStateChange) this.onPlaybackStateChange("paused", this.activeMessageId);
    } else if (this.speechSynthesis && this.speechSynthesis.speaking) {
      this.speechSynthesis.pause();
      this.playbackState = "paused";
      if (this.onPlaybackStateChange) this.onPlaybackStateChange("paused", this.activeMessageId);
    }
  }

  resumeSpeaking() {
    if (this.audioElement && this.audioElement.paused) {
      this.audioElement.play();
      this.playbackState = "playing";
      if (this.onPlaybackStateChange) this.onPlaybackStateChange("playing", this.activeMessageId);
    } else if (this.speechSynthesis && this.speechSynthesis.paused) {
      this.speechSynthesis.resume();
      this.playbackState = "playing";
      if (this.onPlaybackStateChange) this.onPlaybackStateChange("playing", this.activeMessageId);
    }
  }

  stopSpeaking() {
    if (this.audioElement) {
      this.audioElement.pause();
      this.audioElement.currentTime = 0;
      this.audioElement = null;
    }
    if (this.speechSynthesis) {
      this.speechSynthesis.cancel();
    }
    const prevId = this.activeMessageId;
    this.playbackState = "stopped";
    this.activeMessageId = null;
    if (this.onPlaybackStateChange) this.onPlaybackStateChange("stopped", prevId);
  }
}

// Global Voice Controller instance
const voiceCtrl = new VoiceController();
