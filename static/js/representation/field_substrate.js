/**
 * FieldSubstrate: phenotype expressed on a continuous field (fullscreen quad).
 * Uses WebGLUtils for WebGL setup. Signal-to-uniform mapping from base buildParams (phenotype.sensorySystem.inputs).
 */
(function () {
    "use strict";

    var Substrate = window.Substrate;

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

    class FieldSubstrate extends Substrate {
        createDisplayElement(phenotype, patternPayload) {
            var rule = patternPayload && patternPayload.rule;
            if (!rule) {
                return {
                    element: this._createFallback("No rule"),
                    state: null,
                };
            }
            var canvas = this._createCanvas(256, 256);
            var wu = window.WebGLUtils;
            if (!wu || !wu.setupPattern) {
                return {
                    element: this._createFallback("WebGLUtils not available"),
                    state: null,
                };
            }
            var state = wu.setupPattern(canvas, rule);
            if (state && state.error) {
                return {
                    element: this._createFallback(state.error || "Rule error"),
                    state: null,
                };
            }
            return { element: canvas, state: state };
        }

        render(state, params, signalState) {
            if (!state || !state.gl || !state.program) return;
            var gl = state.gl;
            var program = state.program;
            var positionBuffer = state.positionBuffer;
            drawFullscreenQuad(gl, program, positionBuffer, params, signalState);
        }
    }

    window.FieldSubstrate = FieldSubstrate;
})();
