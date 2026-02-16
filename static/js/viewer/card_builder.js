/**
 * CardBuilder: builds organism card DOM (display element, info, actions, events).
 * WebGL setup lives in webgl_utils.js.
 * Depends: window.PopulationState, window.RepresentationHelpers.
 */
import RepresentationRegistry from "../representation/representation_registry.js";

const clamp01 = (x) => Math.min(1, Math.max(0, x));

const createErrorFallback = (errorMsg) => {
    const fallback = document.createElement("div");
    fallback.className = "organism-canvas-fallback";

    if (errorMsg && errorMsg.length > 80) {
        fallback.setAttribute("title", errorMsg);
        fallback.textContent = "Shader error (hover for details)";
        return fallback;
    }

    fallback.textContent = errorMsg || "WebGL not available";
    return fallback;
};

const getClickCoordinates = (event, canvas) => {
    const rect = canvas.getBoundingClientRect();
    return {
        x: clamp01((event.clientX - rect.left) / rect.width),
        y: clamp01((event.clientY - rect.top) / rect.height),
    };
};

const createActionButton = ({ text, className, title, ariaLabel, onClick }) => {
    const btn = document.createElement("button");
    btn.className = className;
    btn.textContent = text;
    btn.title = title;
    btn.setAttribute("aria-label", ariaLabel);
    btn.addEventListener("click", (e) => {
        e.stopPropagation();
        onClick?.();
    });
    return btn;
};

const getOrganismFlexible = (patternId) => {
    const PS = window.PopulationState;
    if (!PS?.getOrganism) return null;

    // Try as-is, as string, as int, and back again, since ids sometimes drift types.
    const direct = PS.getOrganism(patternId);
    if (direct) return direct;

    const asString = typeof patternId === "string" ? patternId : String(patternId);
    const fromString = PS.getOrganism(asString);
    if (fromString) return fromString;

    if (/^\d+$/.test(asString)) {
        const asInt = parseInt(asString, 10);
        const fromInt = PS.getOrganism(asInt);
        if (fromInt) return fromInt;
    }

    return null;
};

class CardBuilder {
    /**
     * Create an organism card DOM element with display element, info, action buttons, and event binding.
     * @param {Object} options - pattern, onShare, onNetwork, onSave, onClick, onUnclick, onMouseEnter, onMouseLeave, onFullscreen, representationId
     * @returns {{ card: HTMLElement, canvas: HTMLCanvasElement|null, runtime: Object|null }}
     */
    createCard(options) {
        const { pattern, representationId = null } = options;
        const Helpers = window.RepresentationHelpers;

        const resolved =
            pattern && pattern.id != null
                ? RepresentationRegistry.resolve({ genomes: [pattern] })
                : RepresentationRegistry.resolve({ representationId });

        const representation = resolved?.representation ?? null;
        const id = pattern?.id;
        const fitness = pattern?.fitness ?? 0;

        const hasCellInteraction =
            representation &&
            Helpers?.supportsCellInteraction?.(
                representation.substrate,
                representation.phenotype
            );

        const card = document.createElement("div");
        card.className = `organism-card${hasCellInteraction ? " organism-card--interactive" : ""}`;
        card.dataset.id = id;
        card.dataset.representationId = representationId ?? "";
        card.dataset.cellInteractive = hasCellInteraction ? "true" : "";

        const actions = this._buildActions(options, id, representation);
        const info = this._buildInfo(pattern, id, fitness, representation);

        if (!representation) {
            card.appendChild(createErrorFallback("No representation"));
            card.appendChild(actions);
            card.appendChild(info);
            this._attachEvents(card, {
                id,
                representationId,
                hasCellInteraction,
                options,
            });
            return { card, canvas: null, runtime: null };
        }

        const displayResult = Helpers?.createDisplayElement?.(
            representation,
            pattern,
            options
        );
        const displayEl = displayResult?.element ?? null;
        const runtime = displayResult?.runtime ?? null;

        card.appendChild(
            displayEl || createErrorFallback("Display element creation failed")
        );

        if (Helpers && runtime) Helpers.prepareRuntime(runtime, pattern);

        card.appendChild(actions);
        card.appendChild(info);

        this._attachEvents(card, {
            id,
            representationId,
            hasCellInteraction: Boolean(hasCellInteraction),
            options,
        });

        const canvas = displayEl instanceof HTMLCanvasElement ? displayEl : null;
        return { card, canvas, runtime: runtime || null };
    }

    _buildInfo(pattern, id, fitness, representation) {
        const Helpers = window.RepresentationHelpers;

        const info = document.createElement("div");
        info.className = "organism-info";

        const meta = document.createElement("div");
        meta.className = "organism-meta";

        const label =
            representation && Helpers
                ? Helpers.getMetaLabel(representation.phenotype, pattern)
                : null;
        const idPrefix = Helpers ? Helpers.getMetaIdPrefix() : "ID: ";

        meta.textContent =
            label != null && label !== ""
                ? `${idPrefix}${id} | ${label}`
                : `ID: ${id} | Nodes: ${pattern?.nodes ?? 0} | Connections: ${pattern?.connections ?? 0}`;

        const badge = document.createElement("div");
        badge.className = `fitness-badge${fitness === 0 ? " zero" : ""}`;
        badge.textContent = String(fitness);

        info.appendChild(meta);
        info.appendChild(badge);
        return info;
    }

    _buildActions(options, id, representation) {
        const Helpers = window.RepresentationHelpers;

        const actions = document.createElement("div");
        actions.className = "organism-actions";

        actions.appendChild(
            createActionButton({
                text: "⛶",
                className: "fullscreen-btn",
                title: "Expand to fullscreen",
                ariaLabel: "Expand to fullscreen",
                onClick: () => options.onFullscreen?.(id),
            })
        );

        actions.appendChild(
            createActionButton({
                text: "↗",
                className: "submit-community-btn",
                title: "Share to Community",
                ariaLabel: "Share to Community",
                onClick: () => options.onShare?.(id),
            })
        );

        const showNetwork = representation
            ? Helpers?.hasCapability?.(representation.capabilities, "network")
            : true;
        const showSave = representation
            ? Helpers?.hasCapability?.(representation.capabilities, "save")
            : true;

        if (showNetwork) {
            actions.appendChild(
                createActionButton({
                    text: "🧠",
                    className: "network-btn",
                    title: "View network visualization",
                    ariaLabel: "View network visualization",
                    onClick: () =>
                        options.onNetwork?.(id, actions.closest(".organism-card")),
                })
            );
        }

        if (showSave) {
            // Keep button reference so onSave can update UI state (spinner/disabled/etc.)
            const saveBtn = createActionButton({
                text: "↓",
                className: "save-btn",
                title: "Download organism (compiling may take a moment)",
                ariaLabel: "Download organism; compiling may take a moment",
                onClick: () => options.onSave?.(id, saveBtn),
            });
            actions.appendChild(saveBtn);
        }

        return actions;
    }

    _attachEvents(card, { id, representationId, hasCellInteraction, options }) {
        // Card-level click/contextmenu/mouseenter/mouseleave are handled by grid delegation (see GridRenderer).
        // Only ensure data attributes are set; no per-card listeners for those.
    }

    /** Instance delegate so window.CardBuilder.runCellInteraction works (static lives on the class). */
    runCellInteraction(ev, card) {
        return this.constructor.runCellInteraction(ev, card);
    }

    /**
     * Run FBO/cell interaction for a canvas click. Called by grid when ev.target is canvas and card.contains(ev.target).
     * No return value; grid already decided not to trigger fitness.
     */
    static runCellInteraction(ev, card) {
        const canvas = ev.target?.nodeName === "CANVAS" ? ev.target : null;
        if (!canvas) return;

        const representationId = card.dataset.representationId || null;
        const id = card.dataset.id;
        let rep =
            RepresentationRegistry?.resolve?.({ representationId })?.representation ??
            null;
        if (!rep) rep = RepresentationRegistry?.resolve?.({})?.representation ?? null;
        const Helpers = window.RepresentationHelpers;
        const supportsInteraction =
            rep &&
            Helpers?.supportsCellInteraction?.(rep.substrate, rep.phenotype) &&
            rep.substrate?.handleInteraction;
        if (!supportsInteraction) return;

        const coords = getClickCoordinates(ev, canvas);
        const runtime =
            window.GridRenderer?.getRuntime?.(id) ??
            getOrganismFlexible(id)?.runtime ??
            null;
        rep.substrate.handleInteraction(
            runtime,
            coords.x,
            coords.y,
            ev.type === "contextmenu" ? "contextmenu" : "click"
        );
    }

    static createErrorFallback(msg) {
        return createErrorFallback(msg);
    }
}

const cardBuilder = new CardBuilder();
export default cardBuilder;
export { CardBuilder };
window.CardBuilder = cardBuilder;
