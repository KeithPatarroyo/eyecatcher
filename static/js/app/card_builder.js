/**
 * CardBuilder: builds organism card DOM (canvas, info, actions, events).
 * Card layout and events; WebGL setup lives in webgl_utils.js.
 * Depends: window.RepresentationRegistry, window.PopulationState.
 */
(function () {
    "use strict";

    function createErrorFallback(errorMsg) {
        var fallback = document.createElement("div");
        fallback.className = "organism-canvas-fallback";
        fallback.textContent = errorMsg || "WebGL not available";
        if (errorMsg && errorMsg.length > 80) {
            fallback.setAttribute("title", errorMsg);
            fallback.textContent = "Shader error (hover for details)";
        }
        return fallback;
    }

    function getClickCoordinates(event, canvas) {
        var rect = canvas.getBoundingClientRect();
        return {
            x: Math.min(1.0, Math.max(0.0, (event.clientX - rect.left) / rect.width)),
            y: Math.min(1.0, Math.max(0.0, (event.clientY - rect.top) / rect.height)),
        };
    }

    function createActionButton(text, className, title, ariaLabel, onClick) {
        var btn = document.createElement("button");
        btn.className = className;
        btn.textContent = text;
        btn.setAttribute("title", title);
        btn.setAttribute("aria-label", ariaLabel);
        btn.onclick = function (e) {
            e.stopPropagation();
            if (onClick) onClick();
        };
        return btn;
    }

    class CardBuilder {
        /**
         * Create an organism card DOM element with canvas, info, action buttons, and event binding.
         * @param {Object} options - pattern, onShare, onNetwork, onSave, onClick, onUnclick, onMouseEnter, onMouseLeave, onFullscreen, representationId
         * @returns {{ card: HTMLElement, canvas: HTMLCanvasElement|null, runtime: Object|null }}
         */
        createCard(options) {
            const pattern = options.pattern;
            const representationId = options.representationId || null;
            var resolved =
                pattern && pattern.id != null
                    ? window.RepresentationRegistry.resolve({ genomes: [pattern] })
                    : window.RepresentationRegistry.resolve({
                          representationId: representationId,
                      });
            var representation = resolved.representation;
            const id = pattern.id;
            const fitness = pattern.fitness !== undefined ? pattern.fitness : 0;
            const Helpers = window.RepresentationHelpers;
            const hasCellInteraction =
                representation &&
                Helpers &&
                Helpers.supportsCellInteraction(
                    representation.substrate,
                    representation.phenotype
                );
            const card = document.createElement("div");
            card.className =
                "organism-card" +
                (hasCellInteraction ? " organism-card--interactive" : "");
            card.dataset.id = id;

            const info = document.createElement("div");
            info.className = "organism-info";
            const meta = document.createElement("div");
            meta.className = "organism-meta";
            var label =
                representation && Helpers
                    ? Helpers.getMetaLabel(representation.phenotype, pattern)
                    : null;
            var idPrefix = Helpers ? Helpers.getMetaIdPrefix() : "ID: ";
            meta.textContent =
                label != null && label !== ""
                    ? idPrefix + id + " | " + label
                    : "ID: " +
                      id +
                      " | Nodes: " +
                      (pattern.nodes ?? 0) +
                      " | Connections: " +
                      (pattern.connections ?? 0);
            const fitnessBadge = document.createElement("div");
            fitnessBadge.className = "fitness-badge" + (fitness === 0 ? " zero" : "");
            fitnessBadge.textContent = String(fitness);
            info.appendChild(meta);
            info.appendChild(fitnessBadge);

            const actions = document.createElement("div");
            actions.className = "organism-actions";

            actions.appendChild(
                createActionButton(
                    "\u26F6",
                    "fullscreen-btn",
                    "Expand to fullscreen",
                    "Expand to fullscreen",
                    function () {
                        if (options.onFullscreen) options.onFullscreen(id);
                    }
                )
            );
            actions.appendChild(
                createActionButton(
                    "\u2197",
                    "submit-community-btn",
                    "Share to Community",
                    "Share to Community",
                    function () {
                        if (options.onShare) options.onShare(id);
                    }
                )
            );
            var showNetwork = representation
                ? Helpers.hasCapability(representation.capabilities, "network")
                : true;
            var showSave = representation
                ? Helpers.hasCapability(representation.capabilities, "save")
                : true;
            if (showNetwork) {
                actions.appendChild(
                    createActionButton(
                        "\uD83E\uDDE0",
                        "network-btn",
                        "View network visualization",
                        "View network visualization",
                        function () {
                            if (options.onNetwork) options.onNetwork(id, card);
                        }
                    )
                );
            }
            if (showSave) {
                var saveBtn = createActionButton(
                    "\u2193",
                    "save-btn",
                    "Download organism (compiling may take a moment)",
                    "Download organism; compiling may take a moment",
                    function () {
                        if (options.onSave) options.onSave(id, saveBtn);
                    }
                );
                actions.appendChild(saveBtn);
            }

            if (!representation) {
                card.appendChild(createErrorFallback("No representation"));
                card.appendChild(actions);
                card.appendChild(info);
                this._attachEvents(card, id, options);
                return { card: card, canvas: null, runtime: null };
            }
            var result =
                Helpers &&
                Helpers.createDisplayElement(representation, pattern, options);
            var displayEl = result && result.element;
            if (displayEl) {
                card.appendChild(displayEl);
            } else {
                card.appendChild(
                    createErrorFallback("Display element creation failed")
                );
            }
            var runtime = result && result.runtime;
            if (Helpers && runtime) {
                Helpers.prepareRuntime(runtime, pattern);
            }
            card.appendChild(actions);
            card.appendChild(info);
            this._attachEvents(card, id, options);
            var isCanvas = displayEl && displayEl instanceof HTMLCanvasElement;
            return {
                card: card,
                canvas: isCanvas ? displayEl : null,
                runtime: runtime || null,
            };
        }

        _attachEvents(card, id, options) {
            var canvas = card.querySelector("canvas");
            var rep = window.RepresentationRegistry.resolve({
                representationId: options.representationId,
            }).representation;
            var Helpers = window.RepresentationHelpers;
            var hasCellInteraction =
                rep &&
                Helpers &&
                Helpers.supportsCellInteraction(rep.substrate, rep.phenotype);
            var self = this;

            if (options.onClick) {
                card.addEventListener("click", function (e) {
                    if (canvas && e.target === canvas && hasCellInteraction) {
                        self._fireCellInteraction(
                            e,
                            canvas,
                            options.representationId,
                            id,
                            "click"
                        );
                        return;
                    }
                    options.onClick(id, card);
                    self._fireCellInteraction(
                        e,
                        canvas,
                        options.representationId,
                        id,
                        "click"
                    );
                });
            }
            if (options.onUnclick) {
                card.addEventListener("contextmenu", function (e) {
                    e.preventDefault();
                    if (canvas && e.target === canvas && hasCellInteraction) {
                        self._fireCellInteraction(
                            e,
                            canvas,
                            options.representationId,
                            id,
                            "contextmenu"
                        );
                        return;
                    }
                    options.onUnclick(id, card);
                    self._fireCellInteraction(
                        e,
                        canvas,
                        options.representationId,
                        id,
                        "contextmenu"
                    );
                });
            }
            if (options.onMouseEnter) {
                card.addEventListener("mouseenter", function () {
                    options.onMouseEnter(id);
                });
            }
            if (options.onMouseLeave) {
                card.addEventListener("mouseleave", function () {
                    options.onMouseLeave(id);
                });
            }
        }

        _fireCellInteraction(
            event,
            canvas,
            representationId,
            patternId,
            interactionType
        ) {
            if (!canvas) return;
            var rep = window.RepresentationRegistry.resolve({
                representationId: representationId,
            }).representation;
            var Helpers = window.RepresentationHelpers;
            if (
                rep &&
                Helpers &&
                Helpers.supportsCellInteraction(rep.substrate, rep.phenotype) &&
                rep.substrate.handleInteraction
            ) {
                var coords = getClickCoordinates(event, canvas);
                var org =
                    window.PopulationState.getOrganism(patternId) ||
                    (typeof patternId === "string" && /^\d+$/.test(patternId)
                        ? window.PopulationState.getOrganism(parseInt(patternId, 10))
                        : null) ||
                    (typeof patternId === "number"
                        ? window.PopulationState.getOrganism(String(patternId))
                        : null);
                var runtime = org ? org.runtime : null;
                rep.substrate.handleInteraction(
                    runtime,
                    coords.x,
                    coords.y,
                    interactionType
                );
            }
        }

        static createErrorFallback(msg) {
            return createErrorFallback(msg);
        }
    }

    window.CardBuilder = new CardBuilder();
})();
