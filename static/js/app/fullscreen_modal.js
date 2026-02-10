/**
 * FullscreenModal: open/close fullscreen pattern view and expose pattern data for the render loop.
 * Researchers change max/min/default canvas size via EvolutionConfig.
 *
 * Dependencies: window.PatternRenderer.setupPattern, EvolutionConfig (FULLSCREEN_CANVAS_*)
 * Exposes: FullscreenModal.openFullscreen, FullscreenModal.closeFullscreen, FullscreenModal.getFullscreenPatternData
 */
(function () {
    "use strict";

    var fullscreenPatternData = null;

    function getConfig() {
        var cfg = window.EvolutionConfig || {};
        return {
            max: cfg.FULLSCREEN_CANVAS_MAX || 1024,
            default: cfg.FULLSCREEN_CANVAS_DEFAULT || 800,
            min: cfg.FULLSCREEN_CANVAS_MIN || 64,
        };
    }

    function closeFullscreen(ids) {
        fullscreenPatternData = null;
        var wrapId = (ids && ids.fullscreenCanvasWrap) || "fullscreen-canvas-wrap";
        var modalId = (ids && ids.fullscreenModal) || "fullscreen-modal";
        var wrap = document.getElementById(wrapId);
        var modal = document.getElementById(modalId);
        if (wrap) wrap.innerHTML = "";
        if (modal) modal.hidden = true;
    }

    function openFullscreen(id, population, ids) {
        if (!population || !id) return;
        var pattern = population.find(function (p) {
            return p.id === id;
        });
        if (!pattern || !pattern.shader) return;

        var modalId = (ids && ids.fullscreenModal) || "fullscreen-modal";
        var wrapId = (ids && ids.fullscreenCanvasWrap) || "fullscreen-canvas-wrap";
        var modal = document.getElementById(modalId);
        var wrap = document.getElementById(wrapId);
        if (!modal || !wrap) return;

        closeFullscreen(ids);
        modal.hidden = false;
        wrap.innerHTML = "";

        var config = getConfig();
        var patternRef = pattern;
        requestAnimationFrame(function () {
            if (modal.hidden) return;
            var size = Math.min(
                wrap.clientWidth || config.default,
                wrap.clientHeight || config.default,
                config.max
            );
            if (size < config.min) size = config.default;
            var canvas = document.createElement("canvas");
            canvas.width = size;
            canvas.height = size;
            wrap.appendChild(canvas);

            var PatternRenderer = window.PatternRenderer;
            var patternData =
                PatternRenderer && PatternRenderer.setupPattern(canvas, patternRef.shader);
            if (!patternData || patternData.error) {
                wrap.innerHTML = "";
                modal.hidden = true;
                return;
            }
            fullscreenPatternData = {
                canvas: canvas,
                gl: patternData.gl,
                program: patternData.program,
                positionBuffer: patternData.positionBuffer,
            };
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
