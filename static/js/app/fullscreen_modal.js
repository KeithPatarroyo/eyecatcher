/**
 * FullscreenModal: open/close fullscreen pattern view. Supports shader and grid/image output types.
 * Researchers change max/min/default canvas size via EvolutionConfig.
 * CSS --pattern-aspect-ratio (default 1) controls aspect; set by openFullscreen for non-square.
 *
 * Dependencies: window.PatternRenderer.setupPattern, SubstrateAdapters, EvolutionConfig (FULLSCREEN_CANVAS_*)
 */
(function () {
    "use strict";

    var fullscreenPatternData = null;
    var fullscreenAdapter = null;

    function getConfig() {
        var cfg = window.EvolutionConfig || {};
        return {
            max: cfg.FULLSCREEN_CANVAS_MAX || 1024,
            default: cfg.FULLSCREEN_CANVAS_DEFAULT || 800,
            min: cfg.FULLSCREEN_CANVAS_MIN || 64,
        };
    }

    function closeFullscreen(ids) {
        if (
            fullscreenAdapter &&
            typeof fullscreenAdapter.onTeardown === "function" &&
            fullscreenPatternData &&
            fullscreenPatternData.gl
        ) {
            fullscreenAdapter.onTeardown(
                fullscreenPatternData,
                fullscreenPatternData.gl
            );
        }
        fullscreenPatternData = null;
        fullscreenAdapter = null;
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

    function openFullscreen(id, population, ids) {
        if (!population || !id) return;
        var pattern = population.find(function (p) {
            return p.id === id;
        });
        if (!pattern) return;

        var state =
            window.PopulationState && window.PopulationState.getState
                ? window.PopulationState.getState()
                : {};
        var substrateId = state.substrateId || null;
        var adapter =
            window.SubstrateAdapters && window.SubstrateAdapters.safeResolve
                ? (
                      window.SubstrateAdapters.safeResolve({
                          substrateId: substrateId,
                          genomes: [pattern],
                      }) || {}
                  ).adapter
                : null;
        if (
            !adapter &&
            window.SubstrateAdapters &&
            window.SubstrateAdapters.findAdapterByGenome
        ) {
            adapter = window.SubstrateAdapters.findAdapterByGenome(pattern);
        }

        var hasShader = pattern.shader;
        var hasImage = pattern.image != null;
        var useLiveCanvas = adapter && typeof adapter.onSetup === "function";
        if (!hasShader && !hasImage && !useLiveCanvas) return;

        var modalId = (ids && ids.fullscreenModal) || "fullscreen-modal";
        var wrapId = (ids && ids.fullscreenCanvasWrap) || "fullscreen-canvas-wrap";
        var modal = document.getElementById(modalId);
        var wrap = document.getElementById(wrapId);
        if (!modal || !wrap) return;

        closeFullscreen(ids);
        modal.hidden = false;
        wrap.innerHTML = "";

        var aspectRatio = (adapter && adapter.preferredAspectRatio) || 1;

        wrap.style.setProperty("--pattern-aspect-ratio", String(aspectRatio));

        var config = getConfig();
        var patternRef = pattern;

        if (hasImage && !useLiveCanvas) {
            var img = document.createElement("img");
            img.className = "pattern-canvas pattern-image fullscreen-pattern-image";
            img.src = patternRef.image;
            img.alt = "Pattern " + id;
            var maxW = Math.min(wrap.clientWidth || config.default, config.max);
            var maxH = Math.min(wrap.clientHeight || config.default, config.max);
            img.style.maxWidth = maxW + "px";
            img.style.maxHeight = maxH + "px";
            wrap.appendChild(img);
            return;
        }

        fullscreenAdapter = adapter;
        requestAnimationFrame(function () {
            if (modal.hidden) return;
            var size = Math.min(
                wrap.clientWidth || config.default,
                wrap.clientHeight || config.default,
                config.max
            );
            if (size < config.min) size = config.default;
            var canvas = document.createElement("canvas");
            canvas.className = "pattern-canvas";
            canvas.width = size;
            canvas.height = size;
            wrap.appendChild(canvas);

            var PatternRenderer = window.PatternRenderer;
            var patternData =
                PatternRenderer &&
                PatternRenderer.setupPattern(canvas, patternRef.shader || "");
            if (!patternData || patternData.error) {
                wrap.innerHTML = "";
                modal.hidden = true;
                fullscreenAdapter = null;
                return;
            }
            fullscreenPatternData = {
                canvas: canvas,
                gl: patternData.gl,
                program: patternData.program,
                positionBuffer: patternData.positionBuffer,
                patternId: id,
            };
            if (patternRef.grid !== undefined)
                fullscreenPatternData.grid = patternRef.grid;
            if (adapter && typeof adapter.preparePatternData === "function") {
                adapter.preparePatternData(fullscreenPatternData, patternRef);
            }
            if (
                adapter &&
                typeof adapter.onSetup === "function" &&
                fullscreenPatternData.gl
            ) {
                adapter.onSetup(fullscreenPatternData, fullscreenPatternData.gl);
            }
        });
    }

    function getFullscreenPatternData() {
        return fullscreenPatternData;
    }

    window.FullscreenModal = {
        openFullscreen: openFullscreen,
        closeFullscreen: closeFullscreen,
        getFullscreenPatternData: getFullscreenPatternData,
    };
})();
