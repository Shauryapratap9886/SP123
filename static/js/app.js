/**
 * Multilingual AI Voice Assistant - Main Application Orchestrator
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const chatFeed = document.getElementById("chatFeed");
  const welcomeHero = document.getElementById("welcomeHero");
  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const micBtn = document.getElementById("micBtn");
  const filePicker = document.getElementById("filePicker");
  const uploadTriggerBtn = document.getElementById("uploadTriggerBtn");
  const attachmentTray = document.getElementById("attachmentTray");
  const trayThumb = document.getElementById("trayThumb");
  const trayFilename = document.getElementById("trayFilename");
  const trayFilesize = document.getElementById("trayFilesize");
  const trayRemoveBtn = document.getElementById("trayRemoveBtn");
  const recordingDrawer = document.getElementById("recordingDrawer");
  const recTimer = document.getElementById("recTimer");
  const interimTranscript = document.getElementById("interimTranscript");
  const stopRecBtn = document.getElementById("stopRecBtn");
  const langPreference = document.getElementById("langPreference");
  const providerBadge = document.getElementById("providerBadge");
  const providerBadgeText = document.getElementById("providerBadgeText");
  const clearChatBtn = document.getElementById("clearChatBtn");
  const toastContainer = document.getElementById("toastContainer");

  // Settings Modal Elements
  const settingsModal = document.getElementById("settingsModal");
  const openSettingsBtn = document.getElementById("openSettingsBtn");
  const closeSettingsBtn = document.getElementById("closeSettingsBtn");
  const saveSettingsBtn = document.getElementById("saveSettingsBtn");
  const settingProvider = document.getElementById("settingProvider");
  const geminiKeyInput = document.getElementById("geminiKeyInput");
  const openaiKeyInput = document.getElementById("openaiKeyInput");
  const sarvamKeyInput = document.getElementById("sarvamKeyInput");
  const settingVoiceRate = document.getElementById("settingVoiceRate");

  // State
  let activeAttachment = null; // { type, filename, size, thumbnail_uri, extracted_text }
  let isSending = false;
  let recStartTime = null;
  let recInterval = null;
  let lastFinalTranscript = "";

  // =========================================================================
  // Initialize App Configuration
  // =========================================================================
  async function loadConfig() {
    const cfg = await API.getConfig();
    if (cfg) {
      updateProviderBadge(cfg.active_provider);
      if (settingProvider) settingProvider.value = cfg.preferred_provider || "auto";
    }
  }

  function updateProviderBadge(provider) {
    if (!providerBadgeText) return;
    const names = {
      gemini: "Gemini 2.5 Flash",
      openai: "GPT-4o-mini",
      sarvam: "Sarvam AI",
      builtin: "Built-in Local"
    };
    providerBadgeText.textContent = names[provider] || provider.toUpperCase();
  }

  function showToast(msg, type = "info") {
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.innerHTML = `<span>${type === "error" ? "⚠️" : "✨"}</span><span>${msg}</span>`;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 250);
    }, 3500);
  }

  // =========================================================================
  // File Upload & Drag-and-Drop
  // =========================================================================
  uploadTriggerBtn.addEventListener("click", () => filePicker.click());

  filePicker.addEventListener("change", async (e) => {
    if (e.target.files && e.target.files[0]) {
      await handleFileUpload(e.target.files[0]);
      filePicker.value = "";
    }
  });

  // Global window drag and drop
  window.addEventListener("dragover", (e) => e.preventDefault());
  window.addEventListener("drop", async (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  async function handleFileUpload(file) {
    const validExtensions = [".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".md"];
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    if (!validExtensions.includes(ext)) {
      showToast("Unsupported format. Please upload PDF, PNG, JPG, or TXT.", "error");
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      showToast("File size exceeds 25 MB.", "error");
      return;
    }

    showToast(`Uploading and extracting: ${file.name}...`);
    try {
      const resp = await API.uploadFile(file);
      if (resp.success) {
        activeAttachment = {
          filename: file.name,
          size: (file.size / 1024).toFixed(1) + " KB",
          type: resp.document.type,
          summary: resp.document.summary,
          thumbnail_uri: resp.thumbnail_uri,
          extracted_text: resp.full_extracted_text || resp.extracted_text_preview || ""
        };
        renderAttachmentTray();
        showToast("File processed successfully!");
      } else {
        showToast(resp.error || "Failed to parse document.", "error");
      }
    } catch (err) {
      showToast("Upload failed: " + err.message, "error");
    }
  }

  function renderAttachmentTray() {
    if (!activeAttachment) {
      attachmentTray.classList.remove("active");
      return;
    }
    trayFilename.textContent = activeAttachment.filename;
    trayFilesize.textContent = `${activeAttachment.type.toUpperCase()} • ${activeAttachment.size}`;

    if (activeAttachment.type === "image" && activeAttachment.thumbnail_uri) {
      trayThumb.innerHTML = `<img src="${activeAttachment.thumbnail_uri}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 4px;">`;
    } else {
      trayThumb.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
        </svg>
      `;
    }
    attachmentTray.classList.add("active");
  }

  trayRemoveBtn.addEventListener("click", () => {
    activeAttachment = null;
    renderAttachmentTray();
  });

  // =========================================================================
  // Voice Interaction (Microphone Recording)
  // =========================================================================
  micBtn.addEventListener("click", () => {
    if (voiceCtrl.isRecording) {
      voiceCtrl.stopListening();
    } else {
      const selectedLang = langPreference.value;
      voiceCtrl.startListening(selectedLang);
    }
  });

  stopRecBtn.addEventListener("click", () => {
    voiceCtrl.stopListening();
    if (lastFinalTranscript) {
      chatInput.value = lastFinalTranscript;
      handleSendMessage(true);
    }
  });

  voiceCtrl.onRecordingStart = () => {
    micBtn.classList.add("recording");
    recordingDrawer.classList.add("active");
    lastFinalTranscript = "";
    interimTranscript.textContent = "Listening... Speak in Hindi, Hinglish, or English";

    recStartTime = Date.now();
    recTimer.textContent = "00:00";
    recInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - recStartTime) / 1000);
      const mins = String(Math.floor(elapsed / 60)).padStart(2, "0");
      const secs = String(elapsed % 60).padStart(2, "0");
      recTimer.textContent = `${mins}:${secs}`;
    }, 1000);
  };

  voiceCtrl.onInterimResult = (text) => {
    interimTranscript.textContent = text;
    chatInput.value = text;
    updateSendBtnState();
  };

  voiceCtrl.onFinalResult = (text) => {
    lastFinalTranscript = text;
    interimTranscript.textContent = text;
    chatInput.value = text;
    updateSendBtnState();
  };

  voiceCtrl.onRecordingEnd = () => {
    micBtn.classList.remove("recording");
    recordingDrawer.classList.remove("active");
    clearInterval(recInterval);

    if (lastFinalTranscript.trim()) {
      handleSendMessage(true); // Voice-triggered query
    }
  };

  voiceCtrl.onError = (msg) => {
    showToast(msg, "error");
    micBtn.classList.remove("recording");
    recordingDrawer.classList.remove("active");
    clearInterval(recInterval);
  };

  // Synchronize audio visualizer wave animation with voiceCtrl playback states
  voiceCtrl.onPlaybackStateChange = (state, messageId) => {
    document.querySelectorAll(".voice-playback-bar").forEach(bar => {
      const barMsgId = bar.getAttribute("data-message-id");
      const playBtn = bar.querySelector(".play-toggle-btn");
      const waveBars = bar.querySelector(".audio-wave-bars");

      if (barMsgId === messageId) {
        if (state === "playing") {
          playBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="4" width="4" height="16"></rect>
              <rect x="14" y="4" width="4" height="16"></rect>
            </svg>
          `;
          waveBars.classList.add("playing");
        } else if (state === "paused") {
          playBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="5 3 19 12 5 21 5 3"></polygon>
            </svg>
          `;
          waveBars.classList.remove("playing");
        } else {
          // stopped
          playBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="5 3 19 12 5 21 5 3"></polygon>
            </svg>
          `;
          waveBars.classList.remove("playing");
        }
      } else {
        waveBars.classList.remove("playing");
      }
    });
  };

  // =========================================================================
  // Chat Messaging & Rendering
  // =========================================================================
  chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
    updateSendBtnState();
  });

  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(false);
    }
  });

  sendBtn.addEventListener("click", () => handleSendMessage(false));

  function updateSendBtnState() {
    const hasText = chatInput.value.trim().length > 0;
    const hasDoc = activeAttachment !== null;
    if (hasText || hasDoc) {
      sendBtn.classList.add("active");
    } else {
      sendBtn.classList.remove("active");
    }
  }

  async function handleSendMessage(wasSpoken = false) {
    const text = chatInput.value.trim();
    if (!text && !activeAttachment) return;
    if (isSending) return;

    isSending = true;
    chatInput.value = "";
    chatInput.style.height = "auto";
    updateSendBtnState();

    // Hide welcome hero on first message
    if (welcomeHero) welcomeHero.style.display = "none";
    chatFeed.style.display = "flex";

    // 1. Render User Message
    const userMsgId = "msg_user_" + Date.now();
    renderUserMessage(userMsgId, text, activeAttachment, wasSpoken);

    // 2. Render Loading Skeleton
    const loadingCard = renderLoadingCard();

    try {
      const selectedLang = langPreference.value;
      const response = await API.sendMessage(text, selectedLang, "auto");
      loadingCard.remove();

      if (response && response.success) {
        const botMsgId = "msg_bot_" + Date.now();
        renderAssistantMessage(botMsgId, response);

        // Auto speak if assistant flagged should_speak or if user used voice
        if (response.should_speak || wasSpoken) {
          const rate = parseFloat(settingVoiceRate ? settingVoiceRate.value : 1.0);
          voiceCtrl.speak(
            response.spoken_text,
            response.spoken_language,
            botMsgId,
            rate,
            response.tts_audio
          );
        }
      } else {
        renderErrorMessage(response.error || "An error occurred while generating the response.");
      }
    } catch (err) {
      loadingCard.remove();
      renderErrorMessage("Communication error: " + err.message);
    } finally {
      isSending = false;
      window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
    }
  }

  function renderUserMessage(id, text, attachment, wasSpoken) {
    const card = document.createElement("div");
    card.className = "message-card user";
    card.id = id;

    let attachmentHtml = "";
    if (attachment) {
      attachmentHtml = `
        <div class="attachment-pill">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
          <span>${attachment.filename} (${attachment.size})</span>
        </div>
      `;
    }

    card.innerHTML = `
      <div class="avatar">U</div>
      <div class="message-body">
        <div class="message-header">
          <div class="sender-info">
            <span class="sender-name">You</span>
            ${wasSpoken ? '<span class="tag-pill">🎙️ Spoken</span>' : ''}
          </div>
          <span class="time-stamp">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
        ${attachmentHtml}
        <div class="markdown-content">${escapeHtml(text || "Please analyze this uploaded document.")}</div>
      </div>
    `;
    chatFeed.appendChild(card);
  }

  function renderLoadingCard() {
    const card = document.createElement("div");
    card.className = "message-card assistant";
    card.innerHTML = `
      <div class="avatar">V</div>
      <div class="message-body">
        <div class="message-header">
          <div class="sender-info">
            <span class="sender-name">Vani AI</span>
            <span class="tag-pill">Analyzing multimodal context...</span>
          </div>
        </div>
        <div class="markdown-content" style="color: var(--text-muted);">
          Processing your instruction and interpreting document details...
        </div>
      </div>
    `;
    chatFeed.appendChild(card);
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
    return card;
  }

  function renderAssistantMessage(id, data) {
    const card = document.createElement("div");
    card.className = "message-card assistant";
    card.id = id;

    // Distinguish extracted raw document content
    let extractedBoxHtml = "";
    if (data.has_extracted_content && data.extracted_content_preview) {
      extractedBoxHtml = `
        <div class="extracted-content-box">
          <div class="extracted-header" onclick="this.nextElementSibling.classList.toggle('collapsed')">
            <div class="extracted-title">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>
              <span>Extracted Document Content (Raw Grounding)</span>
            </div>
            <span style="font-size: 0.72rem; color: #64748b;">Click to toggle</span>
          </div>
          <div class="extracted-body">${escapeHtml(data.extracted_content_preview)}</div>
        </div>
      `;
    }

    // Format markdown
    const formattedHtml = typeof marked !== "undefined" ? marked.parse(data.display_text) : escapeHtml(data.display_text);

    card.innerHTML = `
      <div class="avatar">V</div>
      <div class="message-body">
        <div class="message-header">
          <div class="sender-info">
            <span class="sender-name">Vani AI</span>
            <span class="tag-pill">${data.provider || "AI Engine"}</span>
            <span class="tag-pill" style="background: rgba(6, 182, 212, 0.15); color: #38bdf8;">${formatIntentName(data.intent)}</span>
          </div>
          <span class="time-stamp">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        </div>

        ${extractedBoxHtml}

        <div class="markdown-content">${formattedHtml}</div>

        <!-- Audio Player & Action Toolbar -->
        <div class="action-toolbar">
          <div class="voice-playback-bar" data-message-id="${id}">
            <button class="play-toggle-btn" title="Play / Pause Spoken Response">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3"></polygon>
              </svg>
            </button>
            <button class="stop-speech-btn" title="Stop Speaking">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                <rect x="5" y="5" width="14" height="14"></rect>
              </svg>
            </button>
            <div class="audio-wave-bars">
              <div class="wave-bar"></div>
              <div class="wave-bar"></div>
              <div class="wave-bar"></div>
              <div class="wave-bar"></div>
            </div>
            <select class="speed-select" title="Speech speed">
              <option value="0.85">0.85x</option>
              <option value="1.0" selected>1.0x</option>
              <option value="1.2">1.2x</option>
            </select>
          </div>

          <div class="secondary-actions">
            <button class="text-btn copy-btn" title="Copy to clipboard">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              <span>Copy</span>
            </button>
            <button class="text-btn download-btn" title="Download as Markdown">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
              <span>Export</span>
            </button>
          </div>
        </div>

      </div>
    `;

    chatFeed.appendChild(card);

    // Bind audio controls for this message card
    const playToggleBtn = card.querySelector(".play-toggle-btn");
    const stopSpeechBtn = card.querySelector(".stop-speech-btn");
    const speedSelect = card.querySelector(".speed-select");
    const copyBtn = card.querySelector(".copy-btn");
    const downloadBtn = card.querySelector(".download-btn");

    playToggleBtn.addEventListener("click", () => {
      if (voiceCtrl.activeMessageId === id) {
        if (voiceCtrl.playbackState === "playing") {
          voiceCtrl.pauseSpeaking();
        } else if (voiceCtrl.playbackState === "paused") {
          voiceCtrl.resumeSpeaking();
        } else {
          const rate = parseFloat(speedSelect.value);
          voiceCtrl.speak(data.spoken_text, data.spoken_language, id, rate, data.tts_audio);
        }
      } else {
        const rate = parseFloat(speedSelect.value);
        voiceCtrl.speak(data.spoken_text, data.spoken_language, id, rate, data.tts_audio);
      }
    });

    stopSpeechBtn.addEventListener("click", () => voiceCtrl.stopSpeaking());

    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(data.display_text);
      showToast("Response copied to clipboard!");
    });

    downloadBtn.addEventListener("click", () => {
      const blob = new Blob([data.display_text], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `vani_assistant_${Date.now()}.md`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("Exported response as markdown.");
    });
  }

  function renderErrorMessage(err) {
    const card = document.createElement("div");
    card.className = "message-card assistant";
    card.style.borderLeftColor = "var(--accent-danger)";
    card.innerHTML = `
      <div class="avatar" style="background: var(--accent-danger);">!</div>
      <div class="message-body">
        <div class="message-header">
          <span class="sender-name" style="color: var(--accent-danger);">Error</span>
        </div>
        <div class="markdown-content" style="color: #fca5a5;">
          ${escapeHtml(err)}
        </div>
      </div>
    `;
    chatFeed.appendChild(card);
  }

  function formatIntentName(intent) {
    const map = {
      SUMMARIZE: "Summary",
      TRANSLATE: "Translation",
      EXPLAIN_DIAGRAM: "Diagram Analysis",
      EXPLAIN_FORMULA: "Math Formula",
      EXTRACT_POINTS: "Key Takeaways",
      READ_ALOUD: "Read Aloud",
      QUESTION_ANSWER: "Explanation"
    };
    return map[intent] || "Assistant";
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // =========================================================================
  // Quick Prompt Chips
  // =========================================================================
  document.querySelectorAll(".sample-chip").forEach(chip => {
    chip.addEventListener("click", async () => {
      const sampleType = chip.getAttribute("data-sample");

      if (sampleType === "notes-hinglish") {
        const sample = await API.getSample("notes");
        if (sample) {
          activeAttachment = {
            filename: sample.filename,
            size: "1.2 KB",
            type: "text",
            extracted_text: sample.text
          };
          renderAttachmentTray();
        }
        langPreference.value = "hinglish";
        chatInput.value = "Explain the main concepts in simple Hinglish.";
        handleSendMessage(false);
      } else if (sampleType === "dual-language") {
        chatInput.value = "Give me a spoken answer in English, but display the key points in Hindi.";
        handleSendMessage(false);
      } else if (sampleType === "math-formula") {
        const sample = await API.getSample("math");
        if (sample) {
          activeAttachment = {
            filename: sample.filename,
            size: "0.8 KB",
            type: "text",
            extracted_text: sample.text
          };
          renderAttachmentTray();
        }
        chatInput.value = "Explain this mathematical formula step by step.";
        handleSendMessage(false);
      } else if (sampleType === "read-aloud") {
        const sample = await API.getSample("notes");
        if (sample) {
          activeAttachment = {
            filename: sample.filename,
            size: "1.2 KB",
            type: "text",
            extracted_text: sample.text
          };
          renderAttachmentTray();
        }
        chatInput.value = "Read this document aloud.";
        handleSendMessage(false);
      }
    });
  });

  // =========================================================================
  // Settings Modal Management
  // =========================================================================
  openSettingsBtn.addEventListener("click", () => settingsModal.classList.add("active"));
  providerBadge.addEventListener("click", () => settingsModal.classList.add("active"));
  closeSettingsBtn.addEventListener("click", () => settingsModal.classList.remove("active"));
  settingsModal.addEventListener("click", (e) => {
    if (e.target === settingsModal) settingsModal.classList.remove("active");
  });

  saveSettingsBtn.addEventListener("click", async () => {
    const payload = {
      preferred_provider: settingProvider.value
    };
    if (geminiKeyInput.value.trim()) payload.gemini_api_key = geminiKeyInput.value.trim();
    if (openaiKeyInput.value.trim()) payload.openai_api_key = openaiKeyInput.value.trim();
    if (sarvamKeyInput.value.trim()) payload.sarvam_api_key = sarvamKeyInput.value.trim();

    const res = await API.updateConfig(payload);
    if (res.success) {
      updateProviderBadge(res.active_provider);
      showToast("Configuration saved successfully!");
      settingsModal.classList.remove("active");
    } else {
      showToast("Failed to save configuration.", "error");
    }
  });

  // =========================================================================
  // Clear Context & Reset Session
  // =========================================================================
  clearChatBtn.addEventListener("click", async () => {
    voiceCtrl.stopSpeaking();
    voiceCtrl.stopListening();
    await API.clearSession();
    chatFeed.innerHTML = "";
    chatFeed.style.display = "none";
    welcomeHero.style.display = "block";
    activeAttachment = null;
    renderAttachmentTray();
    showToast("Session reset. Conversation memory cleared.");
  });

  // Initialize
  loadConfig();
});
