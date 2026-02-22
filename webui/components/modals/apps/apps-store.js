import { createStore } from "/js/AlpineStore.js";
import * as API from "/js/api.js";

const model = {
  apps: [],
  loading: false,
  error: null,

  async onModalOpen() {
    await this.refresh();
  },

  async refresh() {
    this.loading = true;
    this.error = null;
    try {
      const data = await API.callJsonApi("/webapp", { action: "list" });
      this.apps = (data.apps || []).sort((a, b) => a.name.localeCompare(b.name));
    } catch (e) {
      this.error = "Failed to load apps: " + e.message;
    } finally {
      this.loading = false;
    }
  },

  async startApp(name) {
    const app = this.apps.find((a) => a.name === name);
    if (app) app._busy = true;
    try {
      await API.callJsonApi("/webapp", { action: "start", name });
      await this.refresh();
    } catch (e) {
      this.error = `Failed to start '${name}': ` + e.message;
    }
  },

  async stopApp(name) {
    const app = this.apps.find((a) => a.name === name);
    if (app) app._busy = true;
    try {
      await API.callJsonApi("/webapp", { action: "stop", name });
      await this.refresh();
    } catch (e) {
      this.error = `Failed to stop '${name}': ` + e.message;
    }
  },

  async restartApp(name) {
    const app = this.apps.find((a) => a.name === name);
    if (app) app._busy = true;
    try {
      await API.callJsonApi("/webapp", { action: "restart", name });
      await this.refresh();
    } catch (e) {
      this.error = `Failed to restart '${name}': ` + e.message;
    }
  },

  async removeApp(name) {
    try {
      await API.callJsonApi("/webapp", { action: "remove", name });
      await this.refresh();
    } catch (e) {
      this.error = `Failed to remove '${name}': ` + e.message;
    }
  },

  async toggleAutostart(name, current) {
    try {
      await API.callJsonApi("/webapp", { action: "autostart", name, enabled: !current });
      await this.refresh();
    } catch (e) {
      this.error = `Failed to update autostart for '${name}': ` + e.message;
    }
  },

  openApp(name) {
    window.open(`/${name}/`, "_blank");
  },

  statusColor(status) {
    if (status === "running") return "#00ff9d";
    if (status === "registered") return "#aaaaaa";
    return "#ff6b6b";
  },

  statusIcon(status) {
    if (status === "running") return "play_circle";
    if (status === "registered") return "radio_button_unchecked";
    return "stop_circle";
  },
};

const store = createStore("appsStore", model);
export { store };
