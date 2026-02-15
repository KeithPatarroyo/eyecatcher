/**
 * ShaderSubstrate: phenotype expressed on a shader surface (fullscreen quad).
 * Uses WebGLUtils for WebGL setup. Maps environment signals to uniforms via TOGGLEABLE_SIGNALS.
 * No representation-specific code; any phenotype with substrate="shader" works.
 */
(function () {
    "use strict";

    var Substrate = window.Substrate;

    function buildParamsFromSignals(signalValues) {
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

    function drawFullscreenQuad(gl, program, positionBuffer, params, signalState) {
        gl.useProgram(program);
        var sig = signalState || {};
        var list = window.EvolutionConfig && window.EvolutionConfig.TOGGLEABLE_SIGNALS;
        var values = params || {};
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

    class ShaderSubstrate extends Substrate {
        createDisplayElement(phenotype, patternPayload) {
            var shader = patternPayload && patternPayload.shader;
            if (!shader) {
                var fallback = document.createElement("div");
                fallback.className = "organism-canvas-fallback";
                fallback.textContent = "No shader";
                return { element: fallback, state: null };
            }
            var canvas = document.createElement("canvas");
            canvas.className = "organism-canvas";
            canvas.width = 256;
            canvas.height = 256;
            var wu = window.WebGLUtils;
            if (!wu || !wu.setupPattern) {
                var err = document.createElement("div");
                err.className = "organism-canvas-fallback";
                err.textContent = "WebGLUtils not available";
                return { element: err, state: null };
            }
            var state = wu.setupPattern(canvas, shader);
            if (state && state.error) {
                var errEl = document.createElement("div");
                errEl.className = "organism-canvas-fallback";
                errEl.textContent = state.error || "Shader error";
                return { element: errEl, state: null };
            }
            return { element: canvas, state: state };
        }

        buildParams(phenotype, signalValues) {
            return buildParamsFromSignals(signalValues);
        }

        render(state, params, signalState) {
            if (!state || !state.gl || !state.program) return;
            var gl = state.gl;
            var program = state.program;
            var positionBuffer = state.positionBuffer;
            drawFullscreenQuad(gl, program, positionBuffer, params, signalState);
        }
    }

    window.ShaderSubstrate = ShaderSubstrate;
})();
