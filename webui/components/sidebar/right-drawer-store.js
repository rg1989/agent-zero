import { createStore } from "/js/AlpineStore.js";
import * as API from "/js/api.js";

const POLL_MS = 2000;

// Colors ordered for maximum perceptual distance between consecutive tabs.
// Adjacent hue gaps: Cyan→Magenta +135°, Magenta→Green ~190°, Green→Purple +135°,
// Purple→Orange ~110°, Orange→Blue +180°, Blue→Yellow ~165°, Yellow→Cyan +135° (wrap).
const TAB_COLORS = [
    "#00f2fe", // Cyan
    "#ff007f", // Magenta
    "#00ff9d", // Green
    "#bf00ff", // Purple
    "#ffb86c", // Orange
    "#3a86ff", // Blue
    "#ffd700", // Yellow
];

const model = {
    isOpen: false,
    apps: [],    // [{ name, color }]
    active: null,

    // Stable color assignment: once an app gets a color it keeps it for the session.
    _colorMap: {},
    _colorCounter: 0,

    init() {
        this._poll();
        setInterval(() => this._poll(), POLL_MS);
    },

    _colorFor(name) {
        if (!this._colorMap[name]) {
            this._colorMap[name] = TAB_COLORS[this._colorCounter % TAB_COLORS.length];
            this._colorCounter++;
        }
        return this._colorMap[name];
    },

    async _poll() {
        try {
            const data = await API.callJsonApi("/webapp", { action: "drawer_state" });
            const { open, apps: serverApps, active } = data.drawer || {};

            const openBool = Boolean(open);
            const serverNames = Array.isArray(serverApps) ? serverApps : [];
            const activeStr = active || null;

            // Build apps list preserving existing colors, assigning new ones for additions.
            const newApps = serverNames.map(name => ({ name, color: this._colorFor(name) }));

            const namesChanged = JSON.stringify(this.apps.map(a => a.name)) !== JSON.stringify(serverNames);
            if (namesChanged) this.apps = newApps;
            if (openBool !== this.isOpen) this.isOpen = openBool;
            if (activeStr !== this.active) this.active = activeStr;
        } catch (_) {
            // silently ignore poll errors
        }
    },

    async _sync() {
        try {
            await API.callJsonApi("/webapp", {
                action: "set_drawer",
                open: this.isOpen,
                apps: this.apps.map(a => a.name),
                active: this.active,
            });
        } catch (_) {}
    },

    async setActive(name) {
        this.active = name;
        await this._sync();
    },

    async closeTab(name) {
        this.apps = this.apps.filter(a => a.name !== name);
        if (this.active === name) {
            this.active = this.apps.length > 0 ? this.apps[this.apps.length - 1].name : null;
        }
        if (this.apps.length === 0) this.isOpen = false;
        await this._sync();
    },

    async toggleDrawer() {
        if (this.apps.length === 0) return;
        this.isOpen = !this.isOpen;
        await this._sync();
    },

    activeColor() {
        const app = this.apps.find(a => a.name === this.active);
        return app ? app.color : TAB_COLORS[0];
    },
};

export const store = createStore("rightDrawer", model);
