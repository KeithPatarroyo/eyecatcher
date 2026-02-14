/**
 * Shared CPPN adapter: render logic for dual_cppn and single_cppn (config-driven).
 * Uses EvolutionConfig.TOGGLEABLE_SIGNALS for uniforms and flat signalState for enable toggles.
 * Exposes: createCppnAdapter(spec) for use by substrate_adapters/index.js
 */
(function () {
    "use strict";

    /**
     * Build uniform-name-keyed values from signal-id-keyed values using TOGGLEABLE_SIGNALS.
     * @param {Object} signalValues - Keys: signal ids (raw_time, mouse_speed, mouse_dist, activity, ...)
     * @param {Object} [_context] - Optional RenderContext (ignored by CPPN adapter)
     * @returns {Object} Keys: uniform names (u_raw_time, u_mouse_speed, ...)
     */
    function buildUniforms(signalValues, _context) {
        const out = {};
        const list =
            window.EvolutionConfig && window.EvolutionConfig.TOGGLEABLE_SIGNALS;
        if (!list || !signalValues) return out;
        list.forEach(function (s) {
            if (s.uniform && !s.derived) {
                out[s.uniform] =
                    signalValues[s.id] !== undefined ? signalValues[s.id] : 0;
            }
        });
        return out;
    }

    /**
     * Draw one frame for a CPPN shader: set uniforms from uniformValues and signalState, then draw.
     * @param {Object} patternData - { gl, program, positionBuffer, canvas? }
     * @param {Object} uniformValues - Keys: uniform names (u_raw_time, u_mouse_speed, ...)
     * @param {Object} signalState - Flat { signal_id: boolean } for enable toggles
     */
    function renderCppn(patternData, uniformValues, signalState) {
        const { gl, program, positionBuffer } = patternData;
        gl.useProgram(program);

        const sig = signalState || {};
        const list =
            window.EvolutionConfig && window.EvolutionConfig.TOGGLEABLE_SIGNALS;
        const values = uniformValues || {};

        const baseUniforms = new Set();
        if (list) {
            list.forEach(function (s) {
                if (s.uniform && !baseUniforms.has(s.uniform)) {
                    const loc = gl.getUniformLocation(program, s.uniform);
                    if (loc !== null) {
                        const val =
                            values[s.uniform] !== undefined ? values[s.uniform] : 0;
                        gl.uniform1f(loc, val);
                    }
                    baseUniforms.add(s.uniform);
                }
            });
        }

        if (list) {
            list.forEach(function (s) {
                const uniformName = "uEnable_" + s.id;
                const loc = gl.getUniformLocation(program, uniformName);
                if (loc !== null) {
                    gl.uniform1f(loc, sig[s.id] ? 1.0 : 0.0);
                }
            });
        }

        const positionLocation = gl.getAttribLocation(program, "position");
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.enableVertexAttribArray(positionLocation);
        gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);

        gl.clearColor(0, 0, 0, 1);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }

    var PATTERN_CANVAS_SIZE = 256;

    /**
     * Create the display element for one CPPN pattern (canvas + WebGL program).
     * @param {Object} pattern - { id, shader, nodes, connections, ... }
     * @param {Object} [_options] - Optional card options
     * @returns {{ element: HTMLElement, patternData: Object|null }}
     */
    function createDisplayElement(pattern, _options) {
        var PatternRenderer = window.PatternRenderer;
        if (!PatternRenderer || !pattern || !pattern.shader) {
            var fallback = document.createElement("div");
            fallback.className = "pattern-canvas-fallback";
            fallback.textContent = "WebGL not available";
            return { element: fallback, patternData: null };
        }
        var canvas = document.createElement("canvas");
        canvas.className = "pattern-canvas";
        canvas.width = PATTERN_CANVAS_SIZE;
        canvas.height = PATTERN_CANVAS_SIZE;
        var patternData = PatternRenderer.setupPattern(canvas, pattern.shader);
        if (!patternData || patternData.error) {
            var errEl = document.createElement("div");
            errEl.className = "pattern-canvas-fallback";
            errEl.textContent =
                patternData && patternData.error ? patternData.error : "Shader error";
            return { element: errEl, patternData: null };
        }
        return { element: canvas, patternData: patternData };
    }

    /**
     * Create a config-driven CPPN adapter (dual_cppn or single_cppn).
     * @param {Object} spec - { id, outputType, isGenomeFormat, hasSignalControls? }
     * @returns {Object} adapter with id, outputType, lifecycle, getDisplayData, createDisplayElement, render, getMetaLabel
     */
    function createCppnAdapter(spec) {
        return {
            id: spec.id,
            outputType: spec.outputType || "shader",
            lifecycle: "frame",
            isGenomeFormat: spec.isGenomeFormat,
            hasSignalControls: spec.hasSignalControls !== false,
            getDisplayData: function (genomes, options) {
                var SA = window.SubstrateAdapters;
                return SA && SA.fetchViaCompile
                    ? SA.fetchViaCompile(genomes, options)
                    : Promise.reject(
                          new Error("SubstrateAdapters.fetchViaCompile not available")
                      );
            },
            createDisplayElement: createDisplayElement,
            render: renderCppn,
            buildUniforms: buildUniforms,
            getMetaLabel: function (pattern) {
                var n = pattern && (pattern.nodes !== undefined ? pattern.nodes : 0);
                var c =
                    pattern &&
                    (pattern.connections !== undefined ? pattern.connections : 0);
                return "Nodes: " + n + " | Connections: " + c;
            },
        };
    }

    window.createCppnAdapter = createCppnAdapter;
})();
