/**
 * FullscreenModal: open/close fullscreen pattern view. Supports shader and grid/image output types.
 * Dependencies: window.WebGLUtils.setupPattern, RepresentationRegistry, EvolutionConfig (FULLSCREEN_CANVAS_*)
 */
(function () {
    "use strict";

    class FullscreenModal {
        constructor() {
            this._fullscreenRuntime = null;
            this._fullscreenRepresentation = null;
        }

        _getConfig() {
            var cfg = window.EvolutionConfig || {};
            return {
                max: cfg.FULLSCREEN_CANVAS_MAX || 1024,
                default: cfg.FULLSCREEN_CANVAS_DEFAULT || 800,
                min: cfg.FULLSCREEN_CANVAS_MIN || 64,
            };
        }

        closeFullscreen(ids) {
            this._fullscreenRuntime = null;
            this._fullscreenRepresentation = null;
            var wrapId = (ids && ids.fullscreenCanvasWrap) || "fullscreen-canvas-wrap";
            var modalId = (ids && ids.fullscreenModal) || "fullscreen-modal";
            var wrap = document.getElementById(wrapId);
            var modal = document.getElementById(modalId);
            if (wrap) {
                wrap.innerHTML = "";
                wrap.style.setProperty("--pattern-aspect-ratio", "1");
            }
            if (modal) modal.hidden = true;
        }

        openFullscreen(id, population, ids) {
            if (!population || !id) return;
            var pattern = population.find(function (p) {
                return p.id === id;
            });
            if (!pattern) return;

            var representationId = window.PopulationState.representationId || null;
            var resolved = window.RepresentationRegistry.resolve({
                genomes: [pattern],
            });
            var representation = resolved.representation;
            if (!representation) {
                representation = window.RepresentationRegistry.findByGenome(pattern);
            }

            var hasShader = pattern.shader;
            var hasImage = pattern.image != null;
            var useLiveCanvas = !!representation;
            if (!hasShader && !hasImage && !useLiveCanvas) return;

            var modalId = (ids && ids.fullscreenModal) || "fullscreen-modal";
            var wrapId = (ids && ids.fullscreenCanvasWrap) || "fullscreen-canvas-wrap";
            var modal = document.getElementById(modalId);
            var wrap = document.getElementById(wrapId);
            if (!modal || !wrap) return;

            this.closeFullscreen(ids);
            modal.hidden = false;
            wrap.innerHTML = "";

            var aspectRatio =
                (representation && representation.preferredAspectRatio) || 1;
            wrap.style.setProperty("--pattern-aspect-ratio", String(aspectRatio));

            var config = this._getConfig();
            var patternRef = pattern;
            var self = this;

            if (hasImage && !useLiveCanvas) {
                var img = document.createElement("img");
                img.className =
                    "organism-canvas organism-image fullscreen-organism-image";
                img.src = patternRef.image;
                img.alt = "Pattern " + id;
                var maxW = Math.min(wrap.clientWidth || config.default, config.max);
                var maxH = Math.min(wrap.clientHeight || config.default, config.max);
                img.style.maxWidth = maxW + "px";
                img.style.maxHeight = maxH + "px";
                wrap.appendChild(img);
                return;
            }

            this._fullscreenRepresentation = representation;
            requestAnimationFrame(function () {
                if (modal.hidden) return;
                var size = Math.min(
                    wrap.clientWidth || config.default,
                    wrap.clientHeight || config.default,
                    config.max
                );
                if (size < config.min) size = config.default;
                var canvas = document.createElement("canvas");
                canvas.className = "organism-canvas";
                canvas.width = size;
                canvas.height = size;
                wrap.appendChild(canvas);

                var WebGLUtils = window.WebGLUtils;
                var runtime =
                    WebGLUtils &&
                    WebGLUtils.setupPattern(canvas, patternRef.shader || "");
                if (!runtime || runtime.error) {
                    wrap.innerHTML = "";
                    modal.hidden = true;
                    self._fullscreenRepresentation = null;
                    return;
                }
                self._fullscreenRuntime = {
                    canvas: canvas,
                    gl: runtime.gl,
                    program: runtime.program,
                    positionBuffer: runtime.positionBuffer,
                    patternId: id,
                };
                if (patternRef.grid !== undefined)
                    self._fullscreenRuntime.grid = patternRef.grid;
                if (representation && window.RepresentationHelpers) {
                    window.RepresentationHelpers.prepareRuntime(
                        self._fullscreenRuntime,
                        patternRef
                    );
                }
            });
        }

        getFullscreenRuntime() {
            return this._fullscreenRuntime;
        }
    }

    window.FullscreenModal = new FullscreenModal();
})();
