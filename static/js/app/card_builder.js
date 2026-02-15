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
            const hasCellInteraction =
                representation && representation.supportsCellInteraction();
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
                representation && representation.getMetaLabel
                    ? representation.getMetaLabel(pattern)
                    : null;
            meta.textContent =
                label != null && label !== ""
                    ? representation.getMetaIdPrefix() + id + " | " + label
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

            const fullscreenBtn = document.createElement("button");
            fullscreenBtn.className = "fullscreen-btn";
            fullscreenBtn.textContent = "\u26F6";
            fullscreenBtn.setAttribute("title", "Expand to fullscreen");
            fullscreenBtn.setAttribute("aria-label", "Expand to fullscreen");
            fullscreenBtn.onclick = function (e) {
                e.stopPropagation();
                if (options.onFullscreen) options.onFullscreen(id);
            };

            const submitCommunityBtn = document.createElement("button");
            submitCommunityBtn.className = "submit-community-btn";
            submitCommunityBtn.setAttribute("title", "Share to Community");
            submitCommunityBtn.setAttribute("aria-label", "Share to Community");
            submitCommunityBtn.textContent = "\u2197";
            submitCommunityBtn.onclick = function (e) {
                e.stopPropagation();
                if (options.onShare) options.onShare(id);
            };

            var showNetwork = representation
                ? representation.hasCapability("network")
                : true;
            var showSave = representation ? representation.hasCapability("save") : true;

            const networkBtn = document.createElement("button");
            networkBtn.className = "network-btn";
            networkBtn.textContent = "\uD83E\uDDE0";
            networkBtn.setAttribute("title", "View network visualization");
            networkBtn.setAttribute("aria-label", "View network visualization");
            networkBtn.onclick = function (e) {
                e.stopPropagation();
                if (options.onNetwork) options.onNetwork(id, card);
            };

            const saveBtn = document.createElement("button");
            saveBtn.className = "save-btn";
            saveBtn.textContent = "\u2193";
            saveBtn.setAttribute(
                "title",
                "Download organism (compiling may take a moment)"
            );
            saveBtn.setAttribute(
                "aria-label",
                "Download organism; compiling may take a moment"
            );
            saveBtn.onclick = function (e) {
                e.stopPropagation();
                if (options.onSave) options.onSave(id, saveBtn);
            };

            actions.appendChild(fullscreenBtn);
            actions.appendChild(submitCommunityBtn);
            if (showNetwork) actions.appendChild(networkBtn);
            if (showSave) actions.appendChild(saveBtn);

            if (!representation) {
                card.appendChild(createErrorFallback("No representation"));
                card.appendChild(actions);
                card.appendChild(info);
                this._attachEvents(card, id, options);
                return { card: card, canvas: null, runtime: null };
            }
            var result = representation.createDisplayElement(pattern, options);
            var displayEl = result && result.element;
            if (displayEl) {
                card.appendChild(displayEl);
            } else {
                card.appendChild(
                    createErrorFallback("Display element creation failed")
                );
            }
            var runtime = result && result.runtime;
            if (representation && runtime) {
                representation.prepareRuntime(runtime, pattern);
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
            var hasCellInteraction = rep && rep.supportsCellInteraction();
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
            if (rep && rep.supportsCellInteraction()) {
                var coords = getClickCoordinates(event, canvas);
                var patternsMap = window.PopulationState.patterns;
                var runtime = null;
                if (patternsMap) {
                    runtime = patternsMap.get(patternId);
                    if (
                        runtime == null &&
                        typeof patternId === "string" &&
                        /^\d+$/.test(patternId)
                    ) {
                        runtime = patternsMap.get(parseInt(patternId, 10));
                    }
                    if (runtime == null && typeof patternId === "number") {
                        runtime = patternsMap.get(String(patternId));
                    }
                }
                rep.onCellInteraction(runtime, coords.x, coords.y, interactionType);
            }
        }

        static createErrorFallback(msg) {
            return createErrorFallback(msg);
        }
    }

    window.CardBuilder = new CardBuilder();
})();
