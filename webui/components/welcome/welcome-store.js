import { createStore } from "/js/AlpineStore.js";
import { getContext } from "/index.js";
import { store as chatsStore } from "/components/sidebar/chats/chats-store.js";
import { store as memoryStore } from "/components/modals/memory/memory-dashboard-store.js";
import { store as projectsStore } from "/components/projects/projects-store.js";
import { store as chatInputStore } from "/components/chat/input/input-store.js";
import * as API from "/js/api.js";

const model = {
  // State
  banners: [],
  bannersLoading: false,
  lastBannerRefresh: 0,
  hasDismissedBanners: false,
  _bannersEventSource: null,

  get isVisible() {
    return !chatsStore.selected;
  },

  init() {
    // Reload banners when settings change
    document.addEventListener("settings-updated", () => {
      this.refreshBannersOnce();
    });
  },

  onCreate() {
    if (this.isVisible) {
      // Initial fetch with client context (ensures API key, unsecured, etc. banners)
      this.refreshBannersOnce();
      // Then start live stream for system resources and other updates
      this.startBannersStream();
    }
  },

  stopBannersStream() {
    if (this._bannersEventSource) {
      this._bannersEventSource.close();
      this._bannersEventSource = null;
    }
  },

  startBannersStream() {
    this.stopBannersStream();
    this.bannersLoading = true;
    const url = "/banners_stream";
    this._bannersEventSource = new EventSource(url, { withCredentials: true });
    this._bannersEventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.error) {
          console.error("Banners stream error:", data.error);
          return;
        }
        const backendBanners = data.banners || [];
        const frontendBanners = this.runFrontendBannerChecks();
        const dismissed = this.getDismissedBannerIds();
        const loadIds = new Set(
          [...frontendBanners, ...backendBanners]
            .filter((b) => b?.id && b.dismissible !== false)
            .map((b) => b.id),
        );
        this.hasDismissedBanners = Array.from(loadIds).some((id) => dismissed.has(id));
        this.banners = this.mergeBanners(frontendBanners, backendBanners);
      } catch (err) {
        console.error("Failed to parse banners stream event:", err);
      } finally {
        this.bannersLoading = false;
      }
    };
    this._bannersEventSource.onerror = () => {
      this.bannersLoading = false;
      this.stopBannersStream();
    };
  },

  // Build frontend context to send to backend
  buildFrontendContext() {
    return {
      url: window.location.href,
      protocol: window.location.protocol,
      hostname: window.location.hostname,
      port: window.location.port,
      browser: navigator.userAgent,
      timestamp: new Date().toISOString(),
    };
  },

  // Frontend banner checks (most checks are on backend; add browser-only checks here)
  runFrontendBannerChecks() {
    return [];
  },

  // Call backend API for additional banners
  async runBackendBannerChecks(frontendBanners, frontendContext) {
    try {
      const response = await API.callJsonApi("/banners", {
        banners: frontendBanners,
        context: frontendContext,
      });
      return response?.banners || [];
    } catch (error) {
      console.error("Failed to fetch backend banners:", error);
      return [];
    }
  },

  // Get list of dismissed banner IDs from storage
  getDismissedBannerIds() {
    const permanent = JSON.parse(
      localStorage.getItem("dismissed_banners") || "[]",
    );
    const temporary = JSON.parse(
      sessionStorage.getItem("dismissed_banners") || "[]",
    );
    return new Set([...permanent, ...temporary]);
  },

  // Merge and filter banners: deduplicate by ID, skip dismissed, sort by priority
  mergeBanners(frontendBanners, backendBanners) {
    const dismissed = this.getDismissedBannerIds();
    const bannerMap = new Map();

    for (const banner of frontendBanners) {
      if (
        banner.id &&
        (banner.dismissible === false || !dismissed.has(banner.id))
      ) {
        bannerMap.set(banner.id, banner);
      }
    }
    for (const banner of backendBanners) {
      if (
        banner.id &&
        (banner.dismissible === false || !dismissed.has(banner.id))
      ) {
        bannerMap.set(banner.id, banner);
      }
    }

    return Array.from(bannerMap.values()).sort(
      (a, b) => (b.priority || 0) - (a.priority || 0),
    );
  },

  // One-shot refresh (for settings-updated, undismiss). Stream handles live updates.
  async refreshBannersOnce() {
    const now = Date.now();
    if (now - this.lastBannerRefresh < 500) return;
    this.lastBannerRefresh = now;
    this.bannersLoading = true;

    try {
      const frontendContext = this.buildFrontendContext();
      const frontendBanners = this.runFrontendBannerChecks();
      const backendBanners = await this.runBackendBannerChecks(
        frontendBanners,
        frontendContext,
      );

      const dismissed = this.getDismissedBannerIds();
      const loadIds = new Set(
        [...frontendBanners, ...backendBanners]
          .filter((b) => b?.id && b.dismissible !== false)
          .map((b) => b.id),
      );
      this.hasDismissedBanners = Array.from(loadIds).some((id) =>
        dismissed.has(id),
      );

      this.banners = this.mergeBanners(frontendBanners, backendBanners);
    } catch (error) {
      console.error("Failed to refresh banners:", error);
      this.banners = this.runFrontendBannerChecks();
      this.hasDismissedBanners = false;
    } finally {
      this.bannersLoading = false;
    }
  },

  get sortedBanners() {
    return [...this.banners].sort(
      (a, b) => (b.priority || 0) - (a.priority || 0),
    );
  },

  /**
   * Dismiss a banner by ID.
   *
   * Usage:
   *   dismissBanner('banner-id')         - Temporary dismiss (sessionStorage, cleared on browser close)
   *   dismissBanner('banner-id', true)   - Permanent dismiss (localStorage, persists across sessions)
   *
   * Dismissed banners are filtered out in mergeBanners() and won't appear until storage is cleared.
   *
   * @param {string} bannerId - The unique ID of the banner to dismiss
   * @param {boolean} permanent - If true, store in localStorage; if false, store in sessionStorage
   */
  dismissBanner(bannerId, permanent = false) {
    this.banners = this.banners.filter((b) => b.id !== bannerId);

    const storage = permanent ? localStorage : sessionStorage;
    const dismissed = JSON.parse(storage.getItem("dismissed_banners") || "[]");
    if (!dismissed.includes(bannerId)) {
      dismissed.push(bannerId);
      storage.setItem("dismissed_banners", JSON.stringify(dismissed));
    }

    this.hasDismissedBanners = this.getDismissedBannerIds().size > 0;
  },

  undismissBanners() {
    localStorage.removeItem("dismissed_banners");
    sessionStorage.removeItem("dismissed_banners");
    this.hasDismissedBanners = false;
    this.refreshBannersOnce();
  },

  getBannerClass(type) {
    const classes = {
      info: "banner-info",
      warning: "banner-warning",
      error: "banner-error",
    };
    return classes[type] || "banner-info";
  },

  getBannerIcon(type) {
    const icons = {
      info: "info",
      warning: "warning",
      error: "error",
    };
    return icons[type] || "info";
  },

  // Execute an action by ID
  executeAction(actionId) {
    switch (actionId) {
      case "new-chat":
        chatsStore.newChat();
        break;
      case "scheduler":
        window.openModal("modals/scheduler/scheduler-modal.html");
        break;
      case "settings":
        // Open settings modal
        const settingsButton = document.getElementById("settings");
        if (settingsButton) {
          settingsButton.click();
        }
        break;
      case "projects":
        projectsStore.openProjectsModal();
        break;
      case "memory":
        memoryStore.openModal();
        break;
      case "files":
        chatInputStore.browseFiles();
        break;
      case "apps":
        window.openModal("modals/apps/apps-modal.html", { title: "My Apps" });
        break;
      case "website":
        window.open("https://agent-zero.ai", "_blank");
        break;
      case "shared-browser":
      case "shared-terminal": {
        const rd = Alpine.store("rightDrawer");
        if (rd) rd.openTab(actionId);
        break;
      }
    }
  },
};

// Create and export the store
const store = createStore("welcomeStore", model);
export { store };
