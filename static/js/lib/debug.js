/**
 * Debug overlay module for Eyecatcher.
 * Shows live signal values + optional time-output sampling for the hovered pattern.
 *
 * Depends on: optional Api endpoint POST {apiUrl}/time-output
 * Uses template: #debug-overlay-tpl, and ids dbg-* inside it.
 */
import api from "./api_client.js";
import RepresentationRegistry from "../representation/representation_registry.js";

const SAMPLE_INTERVAL_MS = 400;

const getEl = (id) => document.getElementById(id);

const fmt = (v) => (Number.isFinite(v) ? v.toFixed(3) : "-");

const nowMs = () =>
    typeof performance !== "undefined" && performance.now
        ? performance.now()
        : Date.now();

const postJson = async (url, body, timeoutMs = 20_000) => {
    if (api) {
        const result = await api.request(url, {
            method: "POST",
            body,
            timeoutMs,
        });
        if (!result.ok) throw new Error(result.error || "Request failed");
        return result.data;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
            signal: controller.signal,
        });
        const text = await res.text();
        const data = text ? JSON.parse(text) : null;
        if (!res.ok) {
            const err = new Error(
                data?.error || data?.message || `Request failed (${res.status})`
            );
            err.status = res.status;
            err.data = data;
            throw err;
        }
        return data;
    } finally {
        clearTimeout(timer);
    }
};

class EyecatcherDebug {
    constructor() {
        // Config
        this.apiUrl = "";
        this.getMouseDistance = () => 0;
        this.getPatterns = () => new Map();
        this.getSignalState = () => ({ time: true });
        this.getGenomeForPattern = null;
        this.getRepresentation = null;

        // State
        this.hoveredPatternId = null;
        this.timeSamplingEnabled = false;
        this.lastSampleTime = 0;
        this.lastSampledTimeOutput = null;
        this.pendingSampleRequest = false;

        // DOM
        this.toggleBtn = null;
        this.overlay = null;
        this.el = {};
    }

    _createDOM() {
        // Toggle button
        this.toggleBtn = document.createElement("button");
        this.toggleBtn.id = "debug-toggle";
        this.toggleBtn.textContent = "Debug";
        document.body.appendChild(this.toggleBtn);

        // Overlay container (from template)
        this.overlay = document.createElement("div");
        this.overlay.id = "debug-overlay";
        this.overlay.className = "hidden";

        const tpl = getEl("debug-overlay-tpl");
        if (tpl?.content) this.overlay.appendChild(tpl.content.cloneNode(true));
        document.body.appendChild(this.overlay);

        // Cache element refs
        this.el = {
            time: getEl("dbg-time"),
            mouseSpeed: getEl("dbg-mouseSpeed"),
            activity: getEl("dbg-activity"),
            mousePos: getEl("dbg-mousePos"),
            patternId: getEl("dbg-pattern-id"),
            mouseDist: getEl("dbg-mouseDist"),
            timeOutput: getEl("dbg-v-time"),
            sampleCheckbox: getEl("dbg-sample-time"),
            sampleWarning: getEl("dbg-sample-warning"),
            timeOutputSection: getEl("debug-time-output-section"),
        };
    }

    _setOverlayVisible(visible) {
        this.overlay.classList.toggle("hidden", !visible);
        this.toggleBtn.classList.toggle("hidden", visible);
    }

    _setupEventListeners() {
        this.toggleBtn.addEventListener("click", () => this._setOverlayVisible(true));

        // Double click overlay to close (nice “get out of the way” gesture)
        this.overlay.addEventListener("dblclick", () => this._setOverlayVisible(false));

        const cb = this.el.sampleCheckbox;
        if (cb) {
            cb.addEventListener("change", (e) => {
                this.timeSamplingEnabled = Boolean(e.target.checked);
                this.el.sampleWarning?.classList.toggle(
                    "hidden",
                    !this.timeSamplingEnabled
                );
                if (!this.timeSamplingEnabled) this.lastSampledTimeOutput = null;
            });
        }
    }

    async _sampleTimeOutput(patternId, time, mouseSpeed, mouseDist, activity) {
        if (this.pendingSampleRequest || !this.getGenomeForPattern) return;

        this.pendingSampleRequest = true;
        this.lastSampleTime = nowMs();

        try {
            const genome = await this.getGenomeForPattern(patternId);
            if (!genome) return;

            const data = await postJson(`${this.apiUrl}/time-output`, {
                individual: genome,
                time,
                mouseSpeed,
                mouseDist,
                activity,
            });

            if (this.hoveredPatternId === patternId && this.timeSamplingEnabled) {
                this.lastSampledTimeOutput = data?.timeOutput ?? null;
            }
        } catch (e) {
            // Debug overlay should not be noisy; log once per failure type if you want later.
            // console.warn("Time output sample failed:", e);
        } finally {
            this.pendingSampleRequest = false;
        }
    }

    init(config) {
        this.apiUrl = config.apiUrl || "";
        this.getMouseDistance = config.getMouseDistance || (() => 0);
        this.getPatterns = config.getPatterns || (() => new Map());
        this.getSignalState = config.getSignalState || (() => ({ time: true }));
        this.getGenomeForPattern = config.getGenomeForPattern || null;
        this.getRepresentation = config.getRepresentation || null;

        this._createDOM();
        this._setupEventListeners();
    }

    update(state) {
        if (!this.overlay || this.overlay.classList.contains("hidden")) return;

        const { time, mouseSpeed, activity, mouseX, mouseY } = state || {};

        // Global signals
        if (this.el.time) this.el.time.textContent = fmt(time);
        if (this.el.mouseSpeed) this.el.mouseSpeed.textContent = fmt(mouseSpeed);
        if (this.el.activity) this.el.activity.textContent = fmt(activity);
        if (this.el.mousePos) {
            const x = Number.isFinite(mouseX) ? Math.round(mouseX) : "-";
            const y = Number.isFinite(mouseY) ? Math.round(mouseY) : "-";
            this.el.mousePos.textContent = `${x}, ${y}`;
        }

        const representation = this.getRepresentation ? this.getRepresentation() : null;
        const hasTimeOutput = representation?.capabilities?.timeOutput === true;

        const signalState = this.getSignalState ? this.getSignalState() : null;
        const timeEnabled = hasTimeOutput && signalState?.time;

        const timeEl = this.el.timeOutput;

        // Hovered pattern info
        const patterns = this.getPatterns ? this.getPatterns() : new Map();
        const id = this.hoveredPatternId;

        if (id != null && patterns?.has?.(id)) {
            const runtime = patterns.get(id);
            const dist = runtime?.canvas ? this.getMouseDistance(runtime.canvas) : 0;

            if (this.el.patternId) this.el.patternId.textContent = `#${id}`;
            if (this.el.mouseDist) this.el.mouseDist.textContent = fmt(dist);

            if (!timeEl) return;

            if (!hasTimeOutput) {
                timeEl.textContent = "-";
                timeEl.classList.remove("disabled", "sampled");
                return;
            }

            // Live mode / sampling mode
            if (this.timeSamplingEnabled && timeEnabled) {
                const tNow = nowMs();
                if (
                    !this.pendingSampleRequest &&
                    tNow - this.lastSampleTime >= SAMPLE_INTERVAL_MS
                ) {
                    this._sampleTimeOutput(id, time, mouseSpeed, dist, activity);
                }

                if (this.lastSampledTimeOutput != null) {
                    timeEl.textContent = fmt(this.lastSampledTimeOutput);
                    timeEl.classList.remove("disabled");
                    timeEl.classList.add("sampled");
                } else {
                    timeEl.textContent = "...";
                    timeEl.classList.remove("disabled", "sampled");
                }
                return;
            }

            timeEl.textContent = timeEnabled ? "unique" : "disabled";
            timeEl.classList.toggle("disabled", !timeEnabled);
            timeEl.classList.remove("sampled");
            return;
        }

        // No hover
        if (this.el.patternId) this.el.patternId.textContent = "(hover to see)";
        if (this.el.mouseDist) this.el.mouseDist.textContent = "-";
        if (timeEl) {
            timeEl.textContent = "-";
            timeEl.classList.remove("disabled", "sampled");
        }
        this.lastSampledTimeOutput = null;
    }

    setHoveredPatternId(id) {
        if (id !== this.hoveredPatternId) this.lastSampledTimeOutput = null;
        this.hoveredPatternId = id;
    }

    getHoveredPatternId() {
        return this.hoveredPatternId;
    }

    updateForRepresentation(representationId) {
        const rep = RepresentationRegistry?.get?.(representationId);
        const show = rep?.capabilities?.timeOutput === true;
        if (this.el.timeOutputSection)
            this.el.timeOutputSection.style.display = show ? "" : "none";
    }
}

export default EyecatcherDebug;
if (typeof window !== "undefined") {
    window.EyecatcherDebug = new EyecatcherDebug();
}
