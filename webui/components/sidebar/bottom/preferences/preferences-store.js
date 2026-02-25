import { createStore } from "/js/AlpineStore.js";
import * as css from "/js/css.js";
import { store as speechStore } from "/components/chat/speech/speech-store.js";
import { applyModeSteps } from "/components/messages/process-group/process-group-dom.js";

// Preferences store centralizes user preference toggles and side-effects
const model = {
  // UI toggles (initialized with safe defaults, loaded from localStorage in init)
  get autoScroll() {
    return this._autoScroll;
  },
  set autoScroll(value) {
    this._autoScroll = value;
    this._applyAutoScroll(value);
  },
  _autoScroll: true,

  get themeMode() {
    return this._themeMode;
  },
  set themeMode(value) {
    this._themeMode = value;
    this._applyThemeMode(value);
  },
  _themeMode: "neon",

  themeModeOptions: [
    { label: "Light", value: "light" },
    { label: "Dark", value: "dark" },
    { label: "Neon", value: "neon" },
  ],

  // Backwards compatibility getter
  get darkMode() {
    return this._themeMode !== "light";
  },

  get speech() {
    return this._speech;
  },
  set speech(value) {
    this._speech = value;
    this._applySpeech(value);
  },
  _speech: false,

  get showUtils() {
    return this._showUtils;
  },
  set showUtils(value) {
    this._showUtils = value;
    this._applyShowUtils(value);
  },
  _showUtils: false,

  // Chat container width preference for HiDPI/large screens
  get chatWidth() {
    return this._chatWidth;
  },
  set chatWidth(value) {
    this._chatWidth = value;
    this._applyChatWidth(value);
  },
  _chatWidth: "55", // Default width in em (standard)

  // Width presets: { label, value in em }
  chatWidthOptions: [
    { label: "MIN", value: "40" },
    { label: "WIDE", value: "55" },
    { label: "2X", value: "80" },
    { label: "FULL", value: "full" },
  ],

  // Detail mode for process groups/steps expansion
  get detailMode() {
    return this._detailMode;
  },
  set detailMode(value) {
    this._detailMode = value;
    this._applyDetailMode(value);
  },
  _detailMode: "current", // Default: show current step only

  // Detail mode options for UI sidebar
  detailModeOptions: [
    { label: "NO", value: "collapsed", title: "All collapsed" },
    { label: "LIST", value: "list", title: "Steps collapsed" },
    { label: "STEP", value: "current", title: "Current step only" },
    { label: "ALL", value: "expanded", title: "All expanded" },
  ],

  // Initialize preferences and apply current state
  init() {
    try {
      // Load persisted preferences with safe fallbacks
      try {
        const storedThemeMode = localStorage.getItem("themeMode");
        // Migration: if old darkMode key exists but themeMode doesn't, migrate
        if (!storedThemeMode) {
          const storedDarkMode = localStorage.getItem("darkMode");
          if (storedDarkMode === "false") {
            this._themeMode = "light";
          } else {
            this._themeMode = "neon"; // Default to neon (preserves current behavior)
          }
        } else if (this.themeModeOptions.some(opt => opt.value === storedThemeMode)) {
          this._themeMode = storedThemeMode;
        } else {
          this._themeMode = "neon"; // Default
        }
      } catch {
        this._themeMode = "neon"; // Default to neon mode if localStorage is unavailable
      }

      try {
        const storedSpeech = localStorage.getItem("speech");
        this._speech = storedSpeech === "true";
      } catch {
        this._speech = false; // Default to speech off if localStorage is unavailable
      }

      // Load chat width preference
      try {
        const storedChatWidth = localStorage.getItem("chatWidth");
        if (storedChatWidth && this.chatWidthOptions.some(opt => opt.value === storedChatWidth)) {
          this._chatWidth = storedChatWidth;
        }
      } catch {
        this._chatWidth = "55"; // Default to standard
      }

      // Load detail mode preference
      try {
        const storedDetailMode = localStorage.getItem("detailMode");
        if (storedDetailMode && this.detailModeOptions.some(opt => opt.value === storedDetailMode)) {
          this._detailMode = storedDetailMode;
        }
      } catch {
        this._detailMode = "current"; // Default
      }

      // load utility messages preference
      try{
        const storedShowUtils = localStorage.getItem("showUtils");
        this._showUtils = storedShowUtils === "true";
      } catch {
        this._showUtils = false; // Default to speech off if localStorage is unavailable
      }

      // Apply all preferences
      this._applyThemeMode(this._themeMode);
      this._applyAutoScroll(this._autoScroll);
      this._applySpeech(this._speech);
      this._applyShowUtils(this._showUtils);
      this._applyChatWidth(this._chatWidth);
      this._applyDetailMode(this._detailMode);
    } catch (e) {
      console.error("Failed to initialize preferences store", e);
    }
  },

  _applyAutoScroll(value) {
    // nothing for now
  },

  _applyThemeMode(value) {
    document.body.classList.remove("light-mode", "dark-mode", "neon-mode");
    document.body.classList.add(`${value}-mode`);
    localStorage.setItem("themeMode", value);
  },

  _applySpeech(value) {
    localStorage.setItem("speech", value);
    if (!value) speechStore.stopAudio();
  },


  _applyShowUtils(value) {
    localStorage.setItem("showUtils", value);
    css.toggleCssProperty(
      ".process-step.message-util",
      "display",
      value ? undefined : "none"
    );
  },

  _applyChatWidth(value) {
    localStorage.setItem("chatWidth", value);
    // Set CSS custom property for chat max-width
    const root = document.documentElement;
    if (value === "full") {
      root.style.setProperty("--chat-max-width", "100%");
    } else {
      root.style.setProperty("--chat-max-width", `${value}em`);
    }
  },

  _applyDetailMode(value) {
    localStorage.setItem("detailMode", value);
    // Apply mode to all existing DOM elements
    applyModeSteps(this._detailMode, this._showUtils);
  },
};

export const store = createStore("preferences", model);
