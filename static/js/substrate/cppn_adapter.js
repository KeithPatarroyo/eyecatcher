/**
 * CPPN adapter class for dual_cppn and single_cppn (config-driven).
 * Uses EvolutionConfig.TOGGLEABLE_SIGNALS for uniforms and flat signalState for enable toggles.
 */
(function () {
    "use strict";

    var PATTERN_CANVAS_SIZE = 256;
    var SubstrateAdapter = window.SubstrateAdapter;

    function buildUniforms(signalValues, _context) {
        var out = {};
        var list = window.EvolutionConfig && window.EvolutionConfig.TOGGLEABLE_SIGNALS;
        if (!list || !signalValues) return out;
        list.forEach(function (s) {
            if (s.uniform && !s.derived) {
                out[s.uniform] =
                    signalValues[s.id] !== undefined ? signalValues[s.id] : 0;
            }
        });
        return out;
    }

    function renderCppn(patternData, uniformValues, signalState) {
        var gl = patternData.gl;
        var program = patternData.program;
        var positionBuffer = patternData.positionBuffer;
        gl.useProgram(program);

        var sig = signalState || {};
        var list = window.EvolutionConfig && window.EvolutionConfig.TOGGLEABLE_SIGNALS;
        var values = uniformValues || {};
        var baseUniforms = new Set();
        if (list) {
            list.forEach(function (s) {
                if (s.uniform && !baseUniforms.has(s.uniform)) {
                    var loc = gl.getUniformLocation(program, s.uniform);
                    if (loc !== null) {
                        var val =
                            values[s.uniform] !== undefined ? values[s.uniform] : 0;
                        gl.uniform1f(loc, val);
                    }
                    baseUniforms.add(s.uniform);
                }
            });
        }
        if (list) {
            list.forEach(function (s) {
                var uniformName = "uEnable_" + s.id;
                var loc = gl.getUniformLocation(program, uniformName);
                if (loc !== null) {
                    gl.uniform1f(loc, sig[s.id] ? 1.0 : 0.0);
                }
            });
        }
        var positionLocation = gl.getAttribLocation(program, "position");
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.enableVertexAttribArray(positionLocation);
        gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);
        gl.clearColor(0, 0, 0, 1);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }

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

    class CppnAdapter extends SubstrateAdapter {
        /**
         * @param {Object} spec - { id, outputType, isGenomeFormat, hasSignalControls? }
         */
        constructor(spec) {
            spec = spec || {};
            super({
                id: spec.id,
                outputType: spec.outputType || "shader",
                lifecycle: "frame",
                isGenomeFormat: spec.isGenomeFormat,
                hasSignalControls: spec.hasSignalControls !== false,
            });
        }

        getDisplayData(genomes, options) {
            var SA = window.SubstrateAdapters;
            return SA && SA.fetchViaCompile
                ? SA.fetchViaCompile(genomes, options)
                : Promise.reject(
                      new Error("SubstrateAdapters.fetchViaCompile not available")
                  );
        }

        createDisplayElement(pattern, options) {
            return createDisplayElement(pattern, options);
        }

        render(patternData, uniformValues, signalState) {
            return renderCppn(patternData, uniformValues, signalState);
        }

        buildUniforms(signalValues, context) {
            return buildUniforms(signalValues, context);
        }

        getMetaLabel(pattern) {
            var n = pattern && (pattern.nodes !== undefined ? pattern.nodes : 0);
            var c =
                pattern &&
                (pattern.connections !== undefined ? pattern.connections : 0);
            return "Nodes: " + n + " | Connections: " + c;
        }
    }

    function createCppnAdapter(spec) {
        return new CppnAdapter(spec);
    }

    window.CppnAdapter = CppnAdapter;
    window.createCppnAdapter = createCppnAdapter;
})();
