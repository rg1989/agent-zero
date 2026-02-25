import { createStore } from "/js/AlpineStore.js";
import * as shortcuts from "/js/shortcuts.js";
import { store as fileBrowserStore } from "/components/modals/file-browser/file-browser-store.js";
import { store as messageQueueStore } from "/components/chat/message-queue/message-queue-store.js";
import { store as attachmentsStore } from "/components/chat/attachments/attachmentsStore.js";
import { store as chatsStore } from "/components/sidebar/chats/chats-store.js";
import { store as historyStore } from "/components/modals/history/history-store.js";
import { store as contextStore } from "/components/modals/context/context-store.js";

const BUILTIN_COMMANDS = [
  { command: "/clear",     description: "Clear the current chat history" },
  { command: "/compact",   description: "Ask agent to summarize and compact the conversation" },
  { command: "/save",      description: "Save the current chat" },
  { command: "/stop",      description: "Stop the agent immediately" },
  { command: "/pause",     description: "Pause the agent" },
  { command: "/resume",    description: "Resume the paused agent" },
  { command: "/nudge",     description: "Nudge the agent to continue" },
  { command: "/history",   description: "Open conversation history" },
  { command: "/files",     description: "Open the file browser" },
  { command: "/context",   description: "Open the context window" },
  { command: "/knowledge", description: "Import knowledge files" },
];

const model = {
  paused: false,
  message: "",

  // Slash command autocomplete state
  showSuggestions: false,
  suggestions: [],
  activeSuggestion: -1,
  _allCommands: [...BUILTIN_COMMANDS],
  _commandsLoaded: false,

  _skillToCommand(name) {
    const gsdMatch = name.match(/^gsd-(.+)$/);
    if (gsdMatch) return `/gsd:${gsdMatch[1]}`;
    return `/${name}`;
  },

  async _loadCommands() {
    if (this._commandsLoaded) return;
    try {
      const resp = await shortcuts.callJsonApi("/skills", { action: "list" });
      if (resp?.ok) {
        const skillCmds = (resp.data || []).map(skill => ({
          command: this._skillToCommand(skill.name),
          description: (skill.description || "").slice(0, 72),
        }));
        // Built-ins always stay at the top; skills append after
        this._allCommands = [...BUILTIN_COMMANDS, ...skillCmds];
        this._commandsLoaded = true;
      }
    } catch (e) {
      console.warn("Could not load skills for autocomplete", e);
    }
  },

  handleInput() {
    this.adjustTextareaHeight();
    const val = this.message;
    if (val.startsWith("/")) {
      // Show built-ins immediately (they're always in _allCommands)
      this._filterCommands(val);
      // Load skills in the background if not yet fetched, then re-filter
      if (!this._commandsLoaded) {
        this._loadCommands().then(() => this._filterCommands(val));
      }
    } else {
      this._hideSuggestions();
    }
  },

  _filterCommands(val) {
    const query = val.toLowerCase();
    this.suggestions = this._allCommands
      .filter(c => c.command.toLowerCase().startsWith(query))
      .slice(0, 20);
    this.showSuggestions = this.suggestions.length > 0;
    this.activeSuggestion = this.suggestions.length > 0 ? 0 : -1;
  },

  _hideSuggestions() {
    this.showSuggestions = false;
    this.suggestions = [];
    this.activeSuggestion = -1;
  },

  navigateSuggestions(direction) {
    if (!this.showSuggestions) return false;
    const count = this.suggestions.length;
    if (direction === "up") {
      this.activeSuggestion = (this.activeSuggestion - 1 + count) % count;
    } else {
      this.activeSuggestion = (this.activeSuggestion + 1) % count;
    }
    return true;
  },

  selectSuggestion(cmd) {
    this.message = cmd.command + " ";
    this._hideSuggestions();
    document.getElementById("chat-input")?.focus();
  },

  confirmSuggestion() {
    if (!this.showSuggestions || this.activeSuggestion < 0) return false;
    const cmd = this.suggestions[this.activeSuggestion];
    if (cmd) { this.selectSuggestion(cmd); return true; }
    return false;
  },

  async _handleBuiltinCommand(message) {
    const [cmd] = message.trim().toLowerCase().split(/\s+/);
    switch (cmd) {
      case "/clear":
        if (confirm("Clear the current chat?")) chatsStore.resetChat();
        return true;
      case "/save":
        chatsStore.saveChat();
        return true;
      case "/stop":
        await this.stopAgent();
        return true;
      case "/pause":
        await this.pauseAgent(true);
        return true;
      case "/resume":
        await this.pauseAgent(false);
        return true;
      case "/nudge":
        await this.nudge();
        return true;
      case "/history":
        historyStore.open();
        return true;
      case "/files":
        await this.browseFiles();
        return true;
      case "/context":
        contextStore.open();
        return true;
      case "/knowledge":
        await this.loadKnowledge();
        return true;
      case "/compact":
        // Replace with a compact instruction and let it send normally
        this.message = "Please compact our conversation: provide a brief summary of the key points, decisions made, and any ongoing tasks so we can continue efficiently.";
        return false;
      default:
        return false;
    }
  },

  _getSendState() {
    const hasInput = this.message.trim() || attachmentsStore?.attachments?.length > 0;
    const hasQueue = !!messageQueueStore?.hasQueue;
    const running = !!chatsStore.selectedContext?.running;

    if (hasQueue && !hasInput) return "all";
    if ((running || hasQueue) && hasInput) return "queue";
    return "normal";
  },

  get inputPlaceholder() {
    const state = this._getSendState();
    if (state === "all") return "Press Enter to send queued messages";
    return "Type your message here...";
  },

  // Computed: send button icon type
  get sendButtonIcon() {
    const state = this._getSendState();
    if (state === "all") return "send_and_archive";
    if (state === "queue") return "schedule_send";
    return "send";
  },

  // Computed: send button CSS class
  get sendButtonClass() {
    const state = this._getSendState();
    if (state === "all") return "send-queue send-all";
    if (state === "queue") return "send-queue queue";
    return "";
  },

  // Computed: send button title
  get sendButtonTitle() {
    const state = this._getSendState();
    if (state === "all") return "Send all queued messages";
    if (state === "queue") return "Add to queue";
    return "Send message";
  },

  init() {
    console.log("Input store initialized");
    // Pre-load commands in the background for fast autocomplete
    this._loadCommands();
  },

  async sendMessage() {
    const message = this.message.trim();
    if (message.startsWith("/")) {
      const handled = await this._handleBuiltinCommand(message);
      if (handled) {
        this.reset();
        return;
      }
    }
    // Delegate to the global function
    if (globalThis.sendMessage) {
      await globalThis.sendMessage();
    }
  },

  adjustTextareaHeight() {
    const chatInput = document.getElementById("chat-input");
    if (chatInput) {
      chatInput.style.height = "auto";
      chatInput.style.height = chatInput.scrollHeight + "px";
    }
  },

  async stopAgent() {
    try {
      const context = globalThis.getContext?.();
      if (!globalThis.sendJsonData)
        throw new Error("sendJsonData not available");
      await globalThis.sendJsonData("/stop", { context });
      if (globalThis.toast) {
        globalThis.toast("Agent stopped", "info", 1500);
      }
    } catch (e) {
      if (globalThis.toastFetchError) {
        globalThis.toastFetchError("Error stopping agent", e);
      }
    }
  },

  async pauseAgent(paused) {
    const prev = this.paused;
    this.paused = paused;
    try {
      const context = globalThis.getContext?.();
      if (!globalThis.sendJsonData)
        throw new Error("sendJsonData not available");
      await globalThis.sendJsonData("/pause", { paused, context });
    } catch (e) {
      this.paused = prev;
      if (globalThis.toastFetchError) {
        globalThis.toastFetchError("Error pausing agent", e);
      }
    }
  },

  async nudge() {
    try {
      const context = globalThis.getContext();
      await globalThis.sendJsonData("/nudge", { ctxid: context });
    } catch (e) {
      if (globalThis.toastFetchError) {
        globalThis.toastFetchError("Error nudging agent", e);
      }
    }
  },

  async loadKnowledge() {
    try {
      const resp = await shortcuts.callJsonApi("/knowledge_path_get", {
        ctxid: shortcuts.getCurrentContextId(),
      });
      if (!resp.ok) throw new Error("Error getting knowledge path");
      const path = resp.path;

      // open file browser and wait for it to close
      await fileBrowserStore.open(path);

      // progress notification
      shortcuts.frontendNotification({
        type: shortcuts.NotificationType.PROGRESS,
        message: "Loading knowledge...",
        priority: shortcuts.NotificationPriority.NORMAL,
        displayTime: 999,
        group: "knowledge_load",
        frontendOnly: true,
      });

      // then reindex knowledge
      await globalThis.sendJsonData("/knowledge_reindex", {
        ctxid: shortcuts.getCurrentContextId(),
      });

      // finished notification
      shortcuts.frontendNotification({
        type: shortcuts.NotificationType.SUCCESS,
        message: "Knowledge loaded successfully",
        priority: shortcuts.NotificationPriority.NORMAL,
        displayTime: 2,
        group: "knowledge_load",
        frontendOnly: true,
      });
    } catch (e) {
      // error notification
      shortcuts.frontendNotification({
        type: shortcuts.NotificationType.ERROR,
        message: "Error loading knowledge",
        priority: shortcuts.NotificationPriority.NORMAL,
        displayTime: 5,
        group: "knowledge_load",
        frontendOnly: true,
      });
    }
  },

  // previous implementation without projects
  async _loadKnowledge() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".txt,.pdf,.csv,.html,.json,.md";
    input.multiple = true;

    input.onchange = async () => {
      try {
        const formData = new FormData();
        for (let file of input.files) {
          formData.append("files[]", file);
        }

        formData.append("ctxid", globalThis.getContext());

        const response = await globalThis.fetchApi("/import_knowledge", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          if (globalThis.toast)
            globalThis.toast(await response.text(), "error");
        } else {
          const data = await response.json();
          if (globalThis.toast) {
            globalThis.toast(
              "Knowledge files imported: " + data.filenames.join(", "),
              "success"
            );
          }
        }
      } catch (e) {
        if (globalThis.toastFetchError) {
          globalThis.toastFetchError("Error loading knowledge", e);
        }
      }
    };

    input.click();
  },

  async browseFiles(path) {
    if (!path) {
      try {
        const resp = await shortcuts.callJsonApi("/chat_files_path_get", {
          ctxid: shortcuts.getCurrentContextId(),
        });
        if (resp.ok) path = resp.path;
      } catch (_e) {
        console.error("Error getting chat files path", _e);
      }
    }
    await fileBrowserStore.open(path);
  },

  reset() {
    this.message = "";
    attachmentsStore.clearAttachments();
    this.adjustTextareaHeight();
  }
};

const store = createStore("chatInput", model);

export { store };
