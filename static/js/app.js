// SmartCare AI - BULLETPROOF Cross + Send (2026)
document.addEventListener('DOMContentLoaded', function () {

  // 🔄 REBIND after HTMX updates
  function initSmartCare() {
    // AI AGENT - Login check
    const aiAgent = document.getElementById('ai-agent');
    if (aiAgent) {
      aiAgent.onclick = function (e) {
        e.stopPropagation();
        const authNav = document.getElementById('auth-nav');
        if (authNav && authNav.dataset && authNav.dataset.auth === '1') {
          document.getElementById('assistant-modal').classList.remove('hidden');
          document.body.style.overflow = 'hidden';
        } else {
          window.location.href = '/login';
        }
      };
    }

    // CROSS BUTTON - Close modal
    const closeChat = document.getElementById('close-chat');
    if (closeChat) {
      closeChat.onclick = function (e) {
        e.stopPropagation();
        document.getElementById('assistant-modal').classList.add('hidden');
        document.body.style.overflow = '';
      };
    }

    // OUTSIDE CLICK - Close modal
    const assistantModal = document.getElementById('assistant-modal');
    if (assistantModal) {
      assistantModal.onclick = function (e) {
        if (e.target === assistantModal) {
          assistantModal.classList.add('hidden');
          document.body.style.overflow = '';
        }
      };
    }

    // SEND BUTTON - Chat submit
    const chatSend = document.getElementById('chat-send');
    if (chatSend) {
      chatSend.onclick = function (e) {
        e.preventDefault();
        sendChatMessage();
      };
    }

    // ENTER KEY - Chat submit
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
      chatInput.onkeypress = function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendChatMessage();
        }
      };
    }
  }

  document.getElementById('file-input')?.addEventListener('change', function (e) {
    console.log('File selected:', e.target.files[0]?.name);
    // Don't preventDefault here - let HTMX handle
  });
  //  ==========================ai assistent ======================
  // CHAT SEND FUNCTION
  // Replace your existing sendChatMessage in app.js

  let thinkingTimer = null;

  function startThinkingAnimation() {
    startThinkingAnimation();
    const chatLoading = document.getElementById("chatLoading");
    const loadingText = document.getElementById("loadingText");
    if (!chatLoading || !loadingText) return;

    chatLoading.classList.remove("hidden");

    const base = "Assistant is thinking";
    let dots = 0;

    stopThinkingAnimation(); // prevent multiple timers
    thinkingTimer = setInterval(() => {
      dots = (dots + 1) % 4; // 0..3
      loadingText.textContent = base + ".".repeat(dots);
    }, 350);
  }

  function stopThinkingAnimation() {
    const chatLoading = document.getElementById("chatLoading");
    const loadingText = document.getElementById("loadingText");

    if (thinkingTimer) {
      clearInterval(thinkingTimer);
      thinkingTimer = null;
    }
    if (loadingText) loadingText.textContent = "Analyzing your question...";
    if (chatLoading) chatLoading.classList.add("hidden");
  }

  async function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const messages = document.getElementById('chat-messages');
  const message = (input.value || '').trim();
  const apiKey = document.getElementById('gemini-api-key')?.value || '';


  if (!message) return;

  // 1) Add User Message
  const userMsg = document.createElement('div');
  userMsg.className = 'p-4 bg-blue-500 text-white rounded-2xl max-w-md ml-auto mb-4 shadow-lg';
  userMsg.innerHTML = `<div class="text-sm font-medium"></div>`;
  userMsg.querySelector('div').textContent = message;
  messages.appendChild(userMsg);

  input.value = '';
  messages.scrollTop = messages.scrollHeight;

  // 2) Prepare AI Response Container (final answer will go here)
  const aiResponseContainer = document.createElement('div');
  messages.appendChild(aiResponseContainer);

  // 3) Thinking bubble (animated dots) - uses your existing .typing-dots CSS in base.html
  const thinking = document.createElement('div');
  thinking.className = 'p-4 bg-gray-200 text-gray-800 rounded-2xl max-w-md mr-auto mb-4 shadow-lg';
  thinking.innerHTML = `
    <div class="flex items-center gap-2">
      <span class="font-semibold">Assistant</span>
      <span class="typing-dots inline-flex items-center">
        <span></span><span></span><span></span>
      </span>
    </div>
  `;
  messages.appendChild(thinking);
  messages.scrollTop = messages.scrollHeight;

  try {
    const response = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'message=' + encodeURIComponent(message) +
      '&api_key=' + encodeURIComponent(apiKey)
    });

    // Read entire response (Flask returns one HTML blob, so true token streaming isn't possible here)
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let fullHTML = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      fullHTML += decoder.decode(value, { stream: true });
    }

    // Remove thinking bubble now that we have the answer
    thinking.remove();

    // Put the assistant bubble HTML in DOM
    aiResponseContainer.innerHTML = fullHTML;
    messages.scrollTop = messages.scrollHeight;

    // 4) Typing effect (type plain text, then restore formatted HTML)
    const contentEl = aiResponseContainer.querySelector(".text-sm.leading-relaxed");
    if (!contentEl) return;

    const finalHTML = contentEl.innerHTML;
    const finalText = contentEl.textContent || "";

    contentEl.textContent = "";

    let i = 0;
    const speedMs = 12; // adjust typing speed if you want
    const timer = setInterval(() => {
      contentEl.textContent += finalText[i++] || "";
      messages.scrollTop = messages.scrollHeight;

      if (i >= finalText.length) {
        clearInterval(timer);
        contentEl.innerHTML = finalHTML; // restore formatting
      }
    }, speedMs);

  } catch (err) {
    // Ensure thinking bubble never gets stuck
    try { thinking.remove(); } catch (e) {}

    aiResponseContainer.innerHTML =
      '<div class="text-red-500 p-3">Sorry, assistant is unavailable.</div>';
  }
}


  // Initialize + rebind on HTMX
  initSmartCare();
  document.body.addEventListener('htmx:afterSwap', initSmartCare);
});
// ================ ai agent end ====
//  ================================ml model pridection ================================

//  ================================ end ml model pridection ================================


// =============================
// Drag & Drop Upload Support
// =============================
// ===================================
// ===================================
// Upload gating + filename display
// ===================================
// =====================================================
// Upload auth gating that stays correct after HTMX swaps
// =====================================================
(function () {
  function isLoggedInNow() {
    const authNav = document.getElementById("auth-nav");
    return authNav?.dataset.auth === "1";
  }
function isLoggedIn() {
  const authNav = document.getElementById('auth-nav');
  return authNav && authNav.dataset && authNav.dataset.auth === '1';
}

async function syncGeminiKeyToServer(apiKey) {
  const res = await fetch('/set-gemini-key', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: 'api_key=' + encodeURIComponent(apiKey)
  });
  return res.ok;
}

function initGeminiKeyUI() {
  const section = document.getElementById('gemini-key-section');
  const input = document.getElementById('gemini-key-input');
  const saveBtn = document.getElementById('gemini-key-save');
  const status = document.getElementById('gemini-key-status');

  if (!section || !input || !saveBtn || !status) return;

  if (!isLoggedIn()) {
    section.classList.add('hidden');
    return;
  }

  const existing = localStorage.getItem('gemini_api_key') || '';
  if (!existing) {
    section.classList.remove('hidden');
  } else {
    section.classList.add('hidden');
    // keep server session synced when modal opens
    syncGeminiKeyToServer(existing);
  }

  saveBtn.onclick = async () => {
    const key = (input.value || '').trim();
    if (!key) {
      status.textContent = "Please enter an API key.";
      return;
    }

    status.textContent = "Saving…";
    const ok = await syncGeminiKeyToServer(key);
    if (ok) {
      localStorage.setItem('gemini_api_key', key);
      status.textContent = "✅ Saved. Assistant is now enabled.";
      section.classList.add('hidden');
      input.value = "";
    } else {
      status.textContent = "❌ Failed to save key. Check server logs.";
    }
  };
}

  function setUploadUIState() {
    const loggedIn = isLoggedInNow();

    const dropZone = document.getElementById("drop-zone");
    const uploadBtn = document.getElementById("upload-btn");
    const uploadTitle = document.getElementById("upload-title");
    const uploadSubtitle = document.getElementById("upload-subtitle");

    if (!dropZone || !uploadBtn) return;

    if (!loggedIn) {
      dropZone.classList.add("opacity-50", "cursor-not-allowed");
      uploadBtn.classList.add("opacity-50", "cursor-not-allowed");

      if (uploadTitle) uploadTitle.textContent = "Login required";
      if (uploadSubtitle) uploadSubtitle.textContent = "Click to login before uploading reports";
    } else {
      dropZone.classList.remove("opacity-50", "cursor-not-allowed");
      uploadBtn.classList.remove("opacity-50", "cursor-not-allowed");

      if (uploadTitle) uploadTitle.textContent = "Drag & drop a file here";
      if (uploadSubtitle) uploadSubtitle.textContent = "or click to choose (PDF / JPG / PNG)";
    }
  }

  function redirectToLogin() {
    window.location.href = "/login";
  }

  function bindUploadHandlersOnce() {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("report-file");
    const uploadForm = document.getElementById("upload-form");
    const uploadBtn = document.getElementById("upload-btn");
    const fileName = document.getElementById("file-name");

    if (!dropZone || !fileInput || !uploadBtn) return;

    // Prevent double-binding if this runs multiple times
    if (dropZone.dataset.bound === "1") return;
    dropZone.dataset.bound = "1";

    function updateFileName(file) {
      if (!fileName) return;
      fileName.textContent = file ? "Selected: " + file.name : "";
    }

    // Always update selected filename
    fileInput.addEventListener("change", () => {
      updateFileName(fileInput.files && fileInput.files[0]);
    });

    // Click behavior: if logged out => login, else open picker
    dropZone.addEventListener("click", () => {
      if (!isLoggedInNow()) return redirectToLogin();
      fileInput.click();
    });

    // Block submit when logged out (HTMX would otherwise POST and get 401)
    if (uploadForm) {
      uploadForm.addEventListener("submit", (e) => {
        if (!isLoggedInNow()) {
          e.preventDefault();
          e.stopPropagation();
          redirectToLogin();
        }
      });
    }

    uploadBtn.addEventListener("click", (e) => {
      if (!isLoggedInNow()) {
        e.preventDefault();
        e.stopPropagation();
        redirectToLogin();
      }
    });

    // Drag/drop always attaches, but only works when logged in
    ["dragenter", "dragover"].forEach((evt) => {
      dropZone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (!isLoggedInNow()) return;
        dropZone.classList.add("border-blue-400");
      });
    });

    ["dragleave", "drop"].forEach((evt) => {
      dropZone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove("border-blue-400");
      });
    });

    dropZone.addEventListener("drop", (e) => {
      if (!isLoggedInNow()) return redirectToLogin();

      const files = e.dataTransfer.files;
      if (!files || !files.length) return;

      fileInput.files = files;
      updateFileName(files[0]);
    });
  }

  // Run once on load
  document.addEventListener("DOMContentLoaded", () => {
    bindUploadHandlersOnce();
    setUploadUIState();
  });

  // Re-run UI state after HTMX swaps (logout/login updates auth-nav)
  document.addEventListener("htmx:afterSwap", () => {
    setUploadUIState();
  });

  // Also after HTMX requests complete (belt-and-suspenders)
  document.addEventListener("htmx:afterRequest", () => {
    setUploadUIState();
  });
})();

