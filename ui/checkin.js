/**
 * Retro Terminal BB-8 Companion & Question Check-In Controller.
 */

(function () {
  let state = {
    lastEntry: null,
    soundEnabled: true,
    micStatus: { has_mic: false, stt_engine: null, is_recording: false },
    activeTags: new Set(["#work"]),
    isRecording: false,
    source: "text",
    isBubbleOpen: false,
  };

  const questions = [
    "WHAT ARE YOU WORKING ON RIGHT NOW?",
    "STATUS UPDATE: CURRENT TASK LOG?",
    "CHECKPOINT: STILL ON CURRENT ASSIGNMENT?",
    "COMM LINK: REPORT ACTIVE FOCUS?",
    "ACTIVITY CHECK: WHAT IS HAPPENING NOW?",
  ];

  // DOM Elements
  const speechBubble = document.getElementById("speechBubble");
  const bubbleQuestion = document.getElementById("bubbleQuestion");
  const bubbleInput = document.getElementById("bubbleInput");
  const bubbleSendBtn = document.getElementById("bubbleSendBtn");
  const bubbleMicBtn = document.getElementById("bubbleMicBtn");
  const bubbleMicIcon = document.getElementById("bubbleMicIcon");
  const bubbleMicStatus = document.getElementById("bubbleMicStatus");
  const bubbleCloseBtn = document.getElementById("bubbleCloseBtn");
  const bubbleSameBtn = document.getElementById("bubbleSameBtn");
  const bubbleSameLabel = document.getElementById("bubbleSameLabel");
  const bubbleBreakBtn = document.getElementById("bubbleBreakBtn");
  const animSelect = document.getElementById("animSelect");

  // Dock buttons
  const dockDashBtn = document.getElementById("dockDashBtn");
  const dockSoundBtn = document.getElementById("dockSoundBtn");
  const dockHideBtn = document.getElementById("dockHideBtn");
  const bb8Canvas = document.getElementById("bb8Canvas");

  // WebKit Host IPC
  function postToHost(action, payload = {}) {
    if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.bb8) {
      window.webkit.messageHandlers.bb8.postMessage(JSON.stringify({ action, ...payload }));
    } else {
      console.log("[Retro Host Mock]", action, payload);
    }
  }

  // Initialize 3D BB-8 Droid
  let droid3D = null;
  if (bb8Canvas && window.BB8_3D) {
    droid3D = new window.BB8_3D(bb8Canvas, {
      width: 240,
      height: 170,
      defaultMood: "idle",
      onClick: () => {
        toggleQuestionBubble();
      },
      onMoodChange: (mood) => {
        if (animSelect && animSelect.value !== mood) {
          animSelect.value = mood;
        }
      }
    });
  }

  // Connect Animation Dropdown
  if (animSelect && droid3D) {
    animSelect.addEventListener("change", (e) => {
      droid3D.setMood(e.target.value);
    });
  }

  function openQuestionBubble() {
    state.isBubbleOpen = true;
    speechBubble.classList.add("open");

    const q = questions[Math.floor(Math.random() * questions.length)];
    bubbleQuestion.textContent = q;
    bubbleInput.value = "";
    bubbleMicStatus.textContent = "";

    if (droid3D) {
      droid3D.setLookingUp(true);
      droid3D.triggerHop();
    }

    setTimeout(() => {
      bubbleInput.focus();
    }, 150);
  }

  function closeQuestionBubble() {
    state.isBubbleOpen = false;
    speechBubble.classList.remove("open");
    if (droid3D) {
      droid3D.setLookingUp(false);
    }
  }

  function toggleQuestionBubble() {
    if (state.isBubbleOpen) {
      closeQuestionBubble();
    } else {
      openQuestionBubble();
    }
  }

  window.openCheckinQuestion = function () {
    openQuestionBubble();
  };

  // Keyboard teletype sound on input
  bubbleInput.addEventListener("input", () => {
    try {
      if (window.bb8Audio && typeof window.bb8Audio.playKeyClick === "function") {
        window.bb8Audio.playKeyClick();
      }
    } catch (e) {}
  });

  // Answering & Saving
  function submitAnswer(customText = null, customTags = null, customSource = "text") {
    const text = customText || bubbleInput.value.trim();
    if (!text) {
      bubbleInput.focus();
      return;
    }

    const tags = customTags || Array.from(state.activeTags);
    const payload = {
      text: text,
      tags: tags,
      audio_path: null,
      source: customSource,
    };

    // Immediate confirmation text
    bubbleQuestion.textContent = "[OK] TELEMETRY COMMITTED TO DISK!";

    try {
      if (window.bb8Audio && typeof window.bb8Audio.playSuccess === "function") {
        window.bb8Audio.playSuccess();
      }
    } catch (e) {
      console.warn("Audio feedback error", e);
    }

    try {
      if (droid3D && typeof droid3D.triggerHop === "function") {
        droid3D.triggerHop();
      }
    } catch (e) {
      console.warn("Droid animation error", e);
    }

    // Always deliver save command to host
    postToHost("save", payload);

    // Clear input
    bubbleInput.value = "";

    setTimeout(() => {
      closeQuestionBubble();
    }, 950);
  }

  bubbleSendBtn.addEventListener("click", () => submitAnswer());

  bubbleInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      submitAnswer();
    } else if (e.key === "Escape") {
      closeQuestionBubble();
    }
  });

  // Action: Same as last time
  bubbleSameBtn.addEventListener("click", () => {
    if (!state.lastEntry) return;
    submitAnswer(state.lastEntry.text, state.lastEntry.tags, "quick_repeat");
  });

  // Action: Taking a break
  bubbleBreakBtn.addEventListener("click", () => {
    try {
      if (window.bb8Audio && typeof window.bb8Audio.playBreak === "function") {
        window.bb8Audio.playBreak();
      }
    } catch (e) {}
    submitAnswer("Taking a quick break ☕", ["#break"], "quick_break");
  });

  // Tag chip click toggles
  document.querySelectorAll(".tag-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tag = btn.getAttribute("data-tag");
      if (state.activeTags.has(tag)) {
        state.activeTags.delete(tag);
        btn.classList.remove("active");
      } else {
        state.activeTags.add(tag);
        btn.classList.add("active");
      }
      try {
        if (window.bb8Audio && typeof window.bb8Audio.playKeyClick === "function") {
          window.bb8Audio.playKeyClick();
        }
      } catch (e) {}
    });
  });

  // Action: Mic recording (speech to text)
  bubbleMicBtn.addEventListener("click", () => {
    if (!state.isRecording) {
      state.isRecording = true;
      state.source = "voice";
      bubbleMicBtn.classList.add("recording");
      bubbleMicIcon.textContent = "⏹";
      bubbleMicStatus.textContent = "REC: LISTENING... CLICK TO STOP";
      try {
        if (window.bb8Audio && typeof window.bb8Audio.playRecBeep === "function") {
          window.bb8Audio.playRecBeep(true);
        }
      } catch (e) {}
      postToHost("start_recording");
    } else {
      state.isRecording = false;
      bubbleMicBtn.classList.remove("recording");
      bubbleMicIcon.textContent = "🎙";
      bubbleMicStatus.textContent = "PROCESSING SPEECH TO TEXT...";
      try {
        if (window.bb8Audio && typeof window.bb8Audio.playRecBeep === "function") {
          window.bb8Audio.playRecBeep(false);
        }
      } catch (e) {}
      postToHost("stop_recording");
    }
  });

  window.onRecordingStarted = function (res) {
    if (!res.ok) {
      state.isRecording = false;
      bubbleMicBtn.classList.remove("recording");
      bubbleMicIcon.textContent = "🎙";
      bubbleMicStatus.textContent = res.message || "MIC_ERROR";
    }
  };

  window.onRecordingStopped = function (res) {
    state.isRecording = false;
    bubbleMicBtn.classList.remove("recording");
    bubbleMicIcon.textContent = "🎙";
    if (res.ok) {
      state.source = "voice";
      if (res.transcript) {
        bubbleInput.value = res.transcript;
        bubbleMicStatus.textContent = "[STT]: CONVERTED (AUDIO DISCARDED)";
        bubbleInput.focus();
      } else {
        bubbleInput.value = "Voice check-in";
        bubbleMicStatus.textContent = "[STT]: CONVERTED TO TEXT";
      }
    } else {
      bubbleMicStatus.textContent = res.message || "REC_FAILED";
    }
  };

  bubbleCloseBtn.addEventListener("click", () => closeQuestionBubble());

  // Dock buttons
  dockDashBtn.addEventListener("click", () => postToHost("open_dashboard"));
  dockSoundBtn.addEventListener("click", () => {
    state.soundEnabled = !state.soundEnabled;
    dockSoundBtn.textContent = state.soundEnabled ? "[SND]" : "[MUT]";
    if (window.bb8Audio) window.bb8Audio.setEnabled(state.soundEnabled);
    postToHost("toggle_sound", { enabled: state.soundEnabled });
  });
  dockHideBtn.addEventListener("click", () => postToHost("close"));

  // State initialization from Python host
  window.initBB8 = function (data) {
    if (!data) return;
    state.lastEntry = data.last_entry || null;
    state.soundEnabled = data.sound_enabled !== false;
    dockSoundBtn.textContent = state.soundEnabled ? "🔊" : "🔇";
    if (window.bb8Audio) window.bb8Audio.enabled = state.soundEnabled;

    if (droid3D && data.character_size) {
      droid3D.setScale(data.character_size);
    }

    if (state.lastEntry && state.lastEntry.text) {
      const preview = state.lastEntry.text.length > 10
        ? state.lastEntry.text.slice(0, 8) + ".."
        : state.lastEntry.text;
      bubbleSameLabel.textContent = `SAME: "${preview.toUpperCase()}"`;
      bubbleSameBtn.style.display = "inline-flex";
    } else {
      bubbleSameBtn.style.display = "none";
    }

    if (data.mic_status && !data.mic_status.has_mic) {
      bubbleMicBtn.disabled = true;
      bubbleMicBtn.title = "MIC_UNAVAILABLE";
    }
  };

  postToHost("request_state");
})();
