/**
 * FullscreenModal: open/close fullscreen pattern view. Supports shader and grid/image output types.
 * Depends on: RepresentationRegistry, getConfig (experiment_config).
 */
import DOM from "../lib/dom.js";
import RepresentationRegistry from "../representation/representation_registry.js";
import { RepresentationHelpers } from "../representation/representation_registry.js";
import WebGLUtils from "../representation/webgl_utils.js";
import { getConfig } from "../evolution/experiment_config.js";

const getCfg = () => {
    const cfg = getConfig?.() ?? getConfig() ?? {};
    return {
        max: cfg.FULLSCREEN_CANVAS_MAX ?? 1024,
        def: cfg.FULLSCREEN_CANVAS_DEFAULT ?? 800,
        min: cfg.FULLSCREEN_CANVAS_MIN ?? 64,
    };
};

const getIds = (ids) => ({
    modalId: ids?.fullscreenModal ?? "fullscreen-modal",
    wrapId: ids?.fullscreenCanvasWrap ?? "fullscreen-canvas-wrap",
});

const getEls = (ids) => {
    const { modalId, wrapId } = getIds(ids);
    return {
        modal: DOM.byId(modalId),
        wrap: DOM.byId(wrapId),
    };
};

const setAspectRatio = (wrap, representation) => {
    const ratio = representation?.preferredAspectRatio ?? 1;
    wrap.style.setProperty("--pattern-aspect-ratio", String(ratio));
};

const clearWrap = (wrap) => {
    wrap.innerHTML = "";
    wrap.style.setProperty("--pattern-aspect-ratio", "1");
};

const renderImage = (wrap, pattern, id, cfg) => {
    const img = document.createElement("img");
    img.className = "organism-canvas organism-image fullscreen-organism-image";
    img.src = pattern.image;
    img.alt = `Pattern ${id}`;

    const maxW = Math.min(wrap.clientWidth || cfg.def, cfg.max);
    const maxH = Math.min(wrap.clientHeight || cfg.def, cfg.max);
    img.style.maxWidth = `${maxW}px`;
    img.style.maxHeight = `${maxH}px`;

    wrap.appendChild(img);
};

class FullscreenModal {
    constructor() {
        this._fullscreenRuntime = null;
        this._fullscreenRepresentation = null;
    }

    closeFullscreen(ids) {
        this._fullscreenRuntime = null;
        this._fullscreenRepresentation = null;

        const { modal, wrap } = getEls(ids);
        if (wrap) clearWrap(wrap);
        if (modal) DOM.setHidden(modal, true);
    }

    openFullscreen(id, population, ids) {
        if (!population || !id) return;

        const pattern = population.find((p) => p.id === id);
        if (!pattern) return;

        const { modal, wrap } = getEls(ids);
        if (!modal || !wrap) return;

        // Resolve representation from the genome if possible.
        const resolved = RepresentationRegistry?.resolve?.({
            genomes: [pattern],
        });
        let representation = resolved?.representation ?? null;
        if (!representation) {
            representation = RepresentationRegistry?.findByGenome?.(pattern) ?? null;
        }

        const hasImage = pattern.image != null;
        const hasRule = Boolean(pattern.rule);
        const canLiveRender = Boolean(representation);

        // If we can't show anything meaningful, bail early.
        if (!hasImage && !hasRule && !canLiveRender) return;

        this.closeFullscreen(ids);
        DOM.setHidden(modal, false);
        wrap.innerHTML = "";

        setAspectRatio(wrap, representation);

        const cfg = getCfg();

        // Image-only fullscreen (no live canvas).
        if (hasImage && !canLiveRender) {
            renderImage(wrap, pattern, id, cfg);
            return;
        }

        // Live canvas fullscreen (shader / NCA / whatever the representation supports).
        this._fullscreenRepresentation = representation;

        requestAnimationFrame(() => {
            if (modal.hidden) return;

            let size = Math.min(
                wrap.clientWidth || cfg.def,
                wrap.clientHeight || cfg.def,
                cfg.max
            );
            if (size < cfg.min) size = cfg.def;

            const canvas = document.createElement("canvas");
            canvas.className = "organism-canvas";
            canvas.width = size;
            canvas.height = size;
            wrap.appendChild(canvas);

            const runtime = WebGLUtils?.setupPattern?.(canvas, pattern.rule || "");
            if (!runtime || runtime.error) {
                wrap.innerHTML = "";
                DOM.setHidden(modal, true);
                this._fullscreenRepresentation = null;
                return;
            }

            this._fullscreenRuntime = {
                canvas,
                gl: runtime.gl,
                program: runtime.program,
                positionBuffer: runtime.positionBuffer,
                patternId: id,
                ...(pattern.grid !== undefined ? { grid: pattern.grid } : null),
            };

            if (representation && RepresentationHelpers) {
                RepresentationHelpers.prepareRuntime(this._fullscreenRuntime, pattern);
            }
        });
    }

    getFullscreenRuntime() {
        return this._fullscreenRuntime;
    }
}

const fullscreenModal = new FullscreenModal();
export default fullscreenModal;
