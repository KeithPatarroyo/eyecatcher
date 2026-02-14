/**
 * PatternCardBuilder: builds pattern card DOM (canvas, info, actions, events).
 * Extracted from pattern_renderer.js so WebGL and card layout are separate.
 * Depends: window.RepresentationAdapters, window.PopulationState.
 */
(function () {
    "use strict";

    function createErrorFallback(errorMsg) {
        var fallback = document.createElement("div");
        fallback.className = "pattern-canvas-fallback";
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

    class PatternCardBuilder {
        /**
         * Create a pattern card DOM element with canvas, info, action buttons, and event binding.
         * @param {Object} options - pattern, onShare, onNetwork, onSave, onClick, onUnclick, onMouseEnter, onMouseLeave, onFullscreen, representationId
         * @returns {{ card: HTMLElement, canvas: HTMLCanvasElement|null, patternData: Object|null }}
         */
        createCard(options) {
            const pattern = options.pattern;
            const representationId = options.representationId || null;
            var resolved =
                pattern && pattern.id != null
                    ? window.RepresentationAdapters.resolveForGenomes([pattern])
                    : window.RepresentationAdapters.safeResolve({
                          representationId: representationId,
                      });
            var adapter = resolved.adapter;
            const id = pattern.id;
            const clicks = pattern.clicks !== undefined ? pattern.clicks : 0;
            const hasCellInteraction = adapter && adapter.supportsCellInteraction();
            const card = document.createElement("div");
            card.className =
                "pattern-card" +
                (hasCellInteraction ? " pattern-card--interactive" : "");
            card.dataset.id = id;

            const info = document.createElement("div");
            info.className = "pattern-info";
            const meta = document.createElement("div");
            meta.className = "pattern-meta";
            var label =
                adapter && adapter.getMetaLabel ? adapter.getMetaLabel(pattern) : null;
            meta.textContent =
                label != null && label !== ""
                    ? adapter.getMetaIdPrefix() + id + " | " + label
                    : "ID: " +
                      id +
                      " | Nodes: " +
                      (pattern.nodes ?? 0) +
                      " | Connections: " +
                      (pattern.connections ?? 0);
            const clickCount = document.createElement("div");
            clickCount.className = "click-count" + (clicks === 0 ? " zero" : "");
            clickCount.textContent = String(clicks);
            info.appendChild(meta);
            info.appendChild(clickCount);

            const actions = document.createElement("div");
            actions.className = "pattern-actions";

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

            var showNetwork = adapter ? adapter.hasCapability("network") : true;
            var showSave = adapter ? adapter.hasCapability("save") : true;

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
                "Download pattern (compiling may take a moment)"
            );
            saveBtn.setAttribute(
                "aria-label",
                "Download pattern; compiling may take a moment"
            );
            saveBtn.onclick = function (e) {
                e.stopPropagation();
                if (options.onSave) options.onSave(id, saveBtn);
            };

            actions.appendChild(fullscreenBtn);
            actions.appendChild(submitCommunityBtn);
            if (showNetwork) actions.appendChild(networkBtn);
            if (showSave) actions.appendChild(saveBtn);

            if (!adapter) {
                card.appendChild(createErrorFallback("No adapter"));
                card.appendChild(actions);
                card.appendChild(info);
                this._attachEvents(card, id, options);
                return { card: card, canvas: null, patternData: null };
            }
            var result = adapter.createDisplayElement(pattern, options);
            var displayEl = result && result.element;
            if (displayEl) {
                card.appendChild(displayEl);
            } else {
                card.appendChild(
                    createErrorFallback("Display element creation failed")
                );
            }
            var patternData = result && result.patternData;
            if (adapter && patternData) {
                adapter.preparePatternData(patternData, pattern);
            }
            card.appendChild(actions);
            card.appendChild(info);
            this._attachEvents(card, id, options);
            var isCanvas = displayEl && displayEl instanceof HTMLCanvasElement;
            return {
                card: card,
                canvas: isCanvas ? displayEl : null,
                patternData: patternData || null,
            };
        }

        _attachEvents(card, id, options) {
            var canvas = card.querySelector("canvas");
            var adapter = window.RepresentationAdapters.safeResolve({
                representationId: options.representationId,
            }).adapter;
            var hasCellInteraction = adapter && adapter.supportsCellInteraction();
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
            var adapter = window.RepresentationAdapters.safeResolve({
                representationId: representationId,
            }).adapter;
            if (adapter && adapter.supportsCellInteraction()) {
                var coords = getClickCoordinates(event, canvas);
                var patternsMap = window.PopulationState.patterns;
                var patternData = null;
                if (patternsMap) {
                    patternData = patternsMap.get(patternId);
                    if (
                        patternData == null &&
                        typeof patternId === "string" &&
                        /^\d+$/.test(patternId)
                    ) {
                        patternData = patternsMap.get(parseInt(patternId, 10));
                    }
                    if (patternData == null && typeof patternId === "number") {
                        patternData = patternsMap.get(String(patternId));
                    }
                }
                adapter.onCellInteraction(
                    patternData,
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

    window.PatternCardBuilder = new PatternCardBuilder();
})();
