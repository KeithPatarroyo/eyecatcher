/**
 * CardBuilder: builds organism card DOM (display element, info, actions, events).
 * WebGL setup lives in webgl_utils.js.
 * Depends: window.RepresentationRegistry, window.PopulationState, window.RepresentationHelpers.
 */
(() => {
    "use strict";

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
            const Registry = window.RepresentationRegistry;

            const resolved =
                pattern && pattern.id != null
                    ? Registry.resolve({ genomes: [pattern] })
                    : Registry.resolve({ representationId });

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
            const canvas = card.querySelector("canvas") || null;

            const fireCellInteraction = (event, interactionType) => {
                if (!canvas) return;
                if (!hasCellInteraction) return;
                if (event.target !== canvas) return;

                const rep =
                    window.RepresentationRegistry?.resolve?.({ representationId })
                        ?.representation ?? null;
                const Helpers = window.RepresentationHelpers;

                if (!rep) return;
                if (!Helpers?.supportsCellInteraction?.(rep.substrate, rep.phenotype))
                    return;
                if (!rep.substrate?.handleInteraction) return;

                const coords = getClickCoordinates(event, canvas);
                const org = getOrganismFlexible(id);
                const runtime = org?.runtime ?? null;

                rep.substrate.handleInteraction(
                    runtime,
                    coords.x,
                    coords.y,
                    interactionType
                );
            };

            if (options.onClick) {
                card.addEventListener("click", (e) => {
                    // If the click is on the canvas and we have cell interaction, let it be a canvas event first.
                    if (canvas && e.target === canvas && hasCellInteraction) {
                        fireCellInteraction(e, "click");
                        return;
                    }
                    options.onClick(id, card);
                    fireCellInteraction(e, "click");
                });
            }

            if (options.onUnclick) {
                card.addEventListener("contextmenu", (e) => {
                    e.preventDefault();
                    if (canvas && e.target === canvas && hasCellInteraction) {
                        fireCellInteraction(e, "contextmenu");
                        return;
                    }
                    options.onUnclick(id, card);
                    fireCellInteraction(e, "contextmenu");
                });
            }

            if (options.onMouseEnter)
                card.addEventListener("mouseenter", () => options.onMouseEnter(id));
            if (options.onMouseLeave)
                card.addEventListener("mouseleave", () => options.onMouseLeave(id));
        }

        static createErrorFallback(msg) {
            return createErrorFallback(msg);
        }
    }

    window.CardBuilder = new CardBuilder();
})();
