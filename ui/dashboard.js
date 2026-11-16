/**
 * Dashboard Controller for BB-8 Buddy.
 */

(function () {
  let state = {
    analytics: null,
    entries: [],
    config: {},
    selectedPeriod: "today",
    selectedTag: null,
    searchQuery: "",
  };

  // DOM Elements
  const streakVal = document.getElementById("streakVal");
  const trackedTimeVal = document.getElementById("trackedTimeVal");
  const checkinCountVal = document.getElementById("checkinCountVal");
  const topTagVal = document.getElementById("topTagVal");
  const statusBadge = document.getElementById("statusBadge");

  const timelineFeed = document.getElementById("timelineFeed");
  const timelineEmptyState = document.getElementById("timelineEmptyState");
  const tagFilterChips = document.getElementById("tagFilterChips");
  const timelineSearchInput = document.getElementById("timelineSearchInput");
  const periodFilter = document.getElementById("periodFilter");

  const tagDistList = document.getElementById("tagDistList");
  const commonActivitiesList = document.getElementById("commonActivitiesList");

  const checkinNowBtn = document.getElementById("checkinNowBtn");
  const exportMdBtn = document.getElementById("exportMdBtn");
  const exportCsvBtn = document.getElementById("exportCsvBtn");
  const refreshBtn = document.getElementById("refreshBtn");

  // Quick Activity Log Elements
  const dashQuickLogInput = document.getElementById("dashQuickLogInput");
  const dashQuickLogBtn = document.getElementById("dashQuickLogBtn");
  const quickTagPills = document.getElementById("quickTagPills");
  let activeQuickTags = new Set(["#work"]);

  // Settings elements
  const intervalSelect = document.getElementById("intervalSelect");
  const customIntervalInput = document.getElementById("customIntervalInput");
  const idleThresholdSelect = document.getElementById("idleThresholdSelect");
  const presenceModeSelect = document.getElementById("presenceModeSelect");
  const characterSizeSelect = document.getElementById("characterSizeSelect");
  const soundToggleCheckbox = document.getElementById("soundToggleCheckbox");
  const notificationsToggleCheckbox = document.getElementById("notificationsToggleCheckbox");
  const saveSettingsBtn = document.getElementById("saveSettingsBtn");
  const saveStatusMsg = document.getElementById("saveStatusMsg");

  // WebKit IPC
  function postToHost(action, payload = {}) {
    if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.bb8_dash) {
      window.webkit.messageHandlers.bb8_dash.postMessage(JSON.stringify({ action, ...payload }));
    } else {
      console.log("[Dash Host Mock]", action, payload);
    }
  }

  // Data receiver from Python backend
  window.onDashboardData = function (data) {
    if (!data) return;
    state.analytics = data.analytics || {};
    state.entries = data.entries || [];
    state.config = data.config || {};

    updateMetrics();
    renderTimeline();
    renderAnalytics();
    updateSettingsUI();
  };

  window.onFilteredData = function (data) {
    if (!data) return;
    state.analytics = data.analytics || state.analytics;
    state.entries = data.entries || [];
    updateMetrics();
    renderTimeline();
    renderAnalytics();
  };

  function updateMetrics() {
    const a = state.analytics || {};
    streakVal.textContent = a.streak_days || 0;
    trackedTimeVal.textContent = `${a.total_duration_hours || 0.0}h`;
    checkinCountVal.textContent = a.total_entries || 0;

    if (a.tag_breakdown && a.tag_breakdown.length > 0) {
      topTagVal.textContent = a.tag_breakdown[0].tag;
    } else {
      topTagVal.textContent = "None";
    }

    if (state.config.interval_minutes && statusBadge) {
      const statusText = statusBadge.querySelector(".status-text");
      if (statusText) {
        statusText.textContent = `Monitoring • Every ${state.config.interval_minutes}m`;
      } else {
        statusBadge.textContent = `Monitoring • Every ${state.config.interval_minutes}m`;
      }
    }
  }

  function renderTimeline() {
    timelineFeed.innerHTML = "";
    const query = state.searchQuery.toLowerCase();

    const filtered = state.entries.filter((entry) => {
      // Tag filter
      if (state.selectedTag && (!entry.tags || !entry.tags.includes(state.selectedTag))) {
        return false;
      }
      // Text search query
      if (query) {
        const textMatch = entry.text && entry.text.toLowerCase().includes(query);
        const tagMatch = entry.tags && entry.tags.some((t) => t.toLowerCase().includes(query));
        if (!textMatch && !tagMatch) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      timelineEmptyState.style.display = "block";
    } else {
      timelineEmptyState.style.display = "none";
      filtered.forEach((item) => {
        const card = createTimelineCard(item);
        timelineFeed.appendChild(card);
      });
    }

    renderTagFilterChips();
  }

  function createTimelineCard(item) {
    const card = document.createElement("div");
    card.className = "timeline-item";

    const dt = new Date(item.timestamp);
    const timeStr = isNaN(dt.getTime())
      ? item.timestamp.slice(11, 16)
      : dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const dateStr = isNaN(dt.getTime())
      ? item.timestamp.slice(0, 10)
      : dt.toLocaleDateString([], { month: "short", day: "numeric" });

    // Duration badge
    const dur = item.duration_minutes || 0;
    const durBadge = dur > 0 ? `<span class="item-duration-badge">+${dur}m</span>` : "";

    // Tags
    const tagsHtml = (item.tags || [])
      .map((t) => `<span class="item-tag">${escapeHtml(t)}</span>`)
      .join(" ");

    // Source badge
    let srcText = "⌨️ Text";
    if (item.source === "voice") srcText = "🎤 Voice";
    else if (item.source === "quick_break") srcText = "☕ Break";
    else if (item.source === "quick_repeat") srcText = "⚡ Repeat";

    // Audio Play Button if audio_path exists
    let audioHtml = "";
    if (item.audio_path) {
      audioHtml = `
        <button class="item-action-btn audio-play-btn" title="Play Voice Note" data-audio="${encodeURIComponent(item.audio_path)}">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
          </svg>
          <span>Voice</span>
        </button>
      `;
    }

    card.innerHTML = `
      <div class="item-time-col">
        <span class="item-time">${timeStr}</span>
        <span class="item-date">${dateStr}</span>
        ${durBadge}
      </div>
      <div class="item-content-col">
        <div class="item-text">${escapeHtml(item.text)}</div>
        <div class="item-meta-row">
          ${tagsHtml}
          <span class="item-source-badge">${srcText}</span>
          ${audioHtml}
        </div>
      </div>
      <div class="item-actions-col">
        <button class="item-action-btn delete-btn" title="Delete Entry" data-id="${item.id}">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>
    `;

    // Bind delete
    card.querySelector(".delete-btn").addEventListener("click", () => {
      if (confirm("Delete this check-in entry?")) {
        postToHost("delete_entry", { id: item.id });
      }
    });

    // Bind audio playback if available
    const audioBtn = card.querySelector(".audio-play-btn");
    if (audioBtn) {
      audioBtn.addEventListener("click", () => {
        const path = decodeURIComponent(audioBtn.getAttribute("data-audio"));
        const audio = new Audio("file://" + path);
        audio.play().catch((err) => alert("Could not play audio: " + err));
      });
    }

    return card;
  }

  function renderTagFilterChips() {
    tagFilterChips.innerHTML = "";

    // "All Tags" chip
    const allBtn = document.createElement("button");
    allBtn.className = "tag-filter-btn" + (!state.selectedTag ? " active" : "");
    allBtn.textContent = "All";
    allBtn.addEventListener("click", () => {
      state.selectedTag = null;
      renderTimeline();
    });
    tagFilterChips.appendChild(allBtn);

    // Extract all unique tags
    const allTags = new Set(state.config.custom_tags || []);
    state.entries.forEach((e) => (e.tags || []).forEach((t) => allTags.add(t)));

    allTags.forEach((t) => {
      const btn = document.createElement("button");
      btn.className = "tag-filter-btn" + (state.selectedTag === t ? " active" : "");
      btn.textContent = t.startsWith("#") ? t : `#${t}`;
      btn.addEventListener("click", () => {
        state.selectedTag = state.selectedTag === t ? null : t;
        renderTimeline();
      });
      tagFilterChips.appendChild(btn);
    });
  }

  function renderAnalytics() {
    const a = state.analytics || {};

    // 1. Tag Distribution
    tagDistList.innerHTML = "";
    const tags = a.tag_breakdown || [];
    if (tags.length === 0) {
      tagDistList.innerHTML = '<p style="color: var(--text-dim); font-size: 12.5px; padding: 12px 0;">No category distribution data recorded yet.</p>';
    } else {
      tags.forEach((item) => {
        const row = document.createElement("div");
        row.className = "tag-dist-item";
        row.innerHTML = `
          <div class="tag-dist-header">
            <span class="tag-dist-name">${escapeHtml(item.tag)}</span>
            <span class="tag-dist-stat">${item.percentage}% (${item.duration_minutes}m)</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${item.percentage}%;"></div>
          </div>
        `;
        tagDistList.appendChild(row);
      });
    }

    // 2. Common Activities
    commonActivitiesList.innerHTML = "";
    const acts = a.top_activities || [];
    if (acts.length === 0) {
      commonActivitiesList.innerHTML = '<p style="color: var(--text-dim); font-size: 12.5px; padding: 12px 0;">No frequent activities recorded yet.</p>';
    } else {
      acts.forEach((act) => {
        const item = document.createElement("div");
        item.className = "activity-rank-item";
        item.innerHTML = `
          <span class="activity-rank-text">${escapeHtml(act.activity)}</span>
          <span class="activity-rank-badge">${act.count}×</span>
        `;
        commonActivitiesList.appendChild(item);
      });
    }
  }

  function updateSettingsUI() {
    const c = state.config;
    if (c.interval_minutes) {
      if ([15, 30, 45, 60].includes(c.interval_minutes)) {
        intervalSelect.value = String(c.interval_minutes);
        customIntervalInput.style.display = "none";
      } else {
        intervalSelect.value = "custom";
        customIntervalInput.style.display = "inline-block";
        customIntervalInput.value = c.interval_minutes;
      }
    }

    if (c.idle_threshold_minutes !== undefined) {
      idleThresholdSelect.value = String(c.idle_threshold_minutes);
    }
    if (c.presence_mode) {
      presenceModeSelect.value = c.presence_mode;
    }
    if (c.character_size && characterSizeSelect) {
      characterSizeSelect.value = c.character_size;
    }
    if (c.sound_enabled !== undefined) {
      soundToggleCheckbox.checked = c.sound_enabled;
    }
    if (c.notifications_enabled !== undefined) {
      notificationsToggleCheckbox.checked = c.notifications_enabled;
    }
  }

  // Event Listeners: Tabs
  document.querySelectorAll(".nav-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".nav-tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      const targetId = `pane-${tab.getAttribute("data-tab")}`;
      const pane = document.getElementById(targetId);
      if (pane) pane.classList.add("active");
    });
  });

  // Event Listeners: Period filter
  periodFilter.querySelectorAll(".filter-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      periodFilter.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      state.selectedPeriod = chip.getAttribute("data-period");
      postToHost("filter", {
        period: state.selectedPeriod,
        tag: state.selectedTag,
        query: state.searchQuery,
      });
    });
  });

  // Search input with Esc key clear
  timelineSearchInput.addEventListener("input", (e) => {
    state.searchQuery = e.target.value.trim();
    renderTimeline();
  });

  timelineSearchInput.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      timelineSearchInput.value = "";
      state.searchQuery = "";
      renderTimeline();
    }
  });

  // Direct Activity Logging from Dashboard
  function submitQuickLog() {
    if (!dashQuickLogInput) return;
    const text = dashQuickLogInput.value.trim();
    if (!text) {
      dashQuickLogInput.focus();
      return;
    }

    const tags = Array.from(activeQuickTags);
    // Auto-detect any #hashtags in typed text
    const words = text.split(/\s+/);
    words.forEach((w) => {
      if (w.startsWith("#") && w.length > 1 && !tags.includes(w)) {
        tags.push(w);
      }
    });

    postToHost("save_entry", {
      text: text,
      tags: tags,
      source: "dashboard",
    });

    dashQuickLogInput.value = "";
    dashQuickLogInput.blur();
  }

  if (dashQuickLogBtn) {
    dashQuickLogBtn.addEventListener("click", submitQuickLog);
  }

  if (dashQuickLogInput) {
    dashQuickLogInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        submitQuickLog();
      }
    });
  }

  // Quick Tag Pill Toggles
  if (quickTagPills) {
    quickTagPills.querySelectorAll(".quick-tag-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        const tag = pill.getAttribute("data-tag");
        if (activeQuickTags.has(tag)) {
          activeQuickTags.delete(tag);
          pill.classList.remove("active");
        } else {
          activeQuickTags.add(tag);
          pill.classList.add("active");
        }
      });
    });
  }

  // Actions
  checkinNowBtn.addEventListener("click", () => {
    if (dashQuickLogInput) {
      dashQuickLogInput.focus();
    }
    postToHost("checkin_now");
  });
  exportMdBtn.addEventListener("click", () => postToHost("export_markdown"));
  exportCsvBtn.addEventListener("click", () => postToHost("export_csv"));
  refreshBtn.addEventListener("click", () => {
    refreshBtn.classList.add("spinning");
    setTimeout(() => refreshBtn.classList.remove("spinning"), 600);
    postToHost("refresh");
  });

  // Settings
  intervalSelect.addEventListener("change", () => {
    if (intervalSelect.value === "custom") {
      customIntervalInput.style.display = "inline-block";
      customIntervalInput.focus();
    } else {
      customIntervalInput.style.display = "none";
    }
  });

  saveSettingsBtn.addEventListener("click", () => {
    let interval = parseInt(intervalSelect.value, 10);
    if (intervalSelect.value === "custom") {
      interval = parseInt(customIntervalInput.value, 10) || 30;
    }

    const updates = {
      interval_minutes: interval,
      idle_threshold_minutes: parseInt(idleThresholdSelect.value, 10),
      presence_mode: presenceModeSelect.value,
      character_size: characterSizeSelect ? characterSizeSelect.value : "small",
      sound_enabled: soundToggleCheckbox.checked,
      notifications_enabled: notificationsToggleCheckbox.checked,
    };

    postToHost("save_settings", { settings: updates });

    if (saveStatusMsg) {
      saveStatusMsg.textContent = "✓ Preferences saved successfully";
      saveStatusMsg.classList.add("show");
      setTimeout(() => {
        saveStatusMsg.classList.remove("show");
      }, 3000);
    }
  });

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Initial request
  postToHost("refresh");
})();
