/**
 * Backend API Client for Multilingual AI Voice Assistant
 */

const API = {
  sessionId: localStorage.getItem("vani_session_id") || "sess_" + Math.random().toString(36).substring(2, 11),

  initSession() {
    localStorage.setItem("vani_session_id", this.sessionId);
  },

  async getConfig() {
    try {
      const res = await fetch("/api/config");
      return await res.json();
    } catch (e) {
      console.error("Failed to load config:", e);
      return null;
    }
  },

  async updateConfig(payload) {
    try {
      const res = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      return await res.json();
    } catch (e) {
      console.error("Failed to update config:", e);
      return { success: false, error: e.message };
    }
  },

  async uploadFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          const base64Data = reader.result;
          const payload = {
            session_id: API.sessionId,
            filename: file.name,
            mime_type: file.type || "application/octet-stream",
            base64_data: base64Data
          };

          const res = await fetch("/api/upload", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
          const data = await res.json();
          resolve(data);
        } catch (err) {
          reject(err);
        }
      };
      reader.onerror = (error) => reject(error);
      reader.readAsDataURL(file);
    });
  },

  async sendMessage(message, languagePreference = "auto", provider = "auto") {
    try {
      const payload = {
        session_id: this.sessionId,
        message: message,
        language_preference: languagePreference,
        provider: provider
      };

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      return await res.json();
    } catch (e) {
      console.error("Chat API error:", e);
      return {
        success: false,
        error: "Network error communicating with server."
      };
    }
  },

  async clearSession() {
    try {
      const res = await fetch("/api/session/clear", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: this.sessionId })
      });
      return await res.json();
    } catch (e) {
      console.error("Clear session error:", e);
      return { success: false };
    }
  },

  async getSample(type = "notes") {
    try {
      const res = await fetch(`/api/sample?type=${encodeURIComponent(type)}`);
      return await res.json();
    } catch (e) {
      return null;
    }
  }
};

API.initSession();
