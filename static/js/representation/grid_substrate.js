/**
 * GridSubstrate: phenotype expressed on a 2D grid with FBO ping-pong.
 * Step shader, display shader, and toggle shader come from phenotype.
 * Built-in interaction "toggle": click to flip cells. "draw" (future): paint while dragging.
 */
(function () {
    "use strict";

    var Substrate = window.Substrate;
    var MAX_TOGGLES_PER_PASS = 64;
    var TOGGLE_BRUSH_RADIUS = 1;

    function gridToRgbaPixelArray(grid) {
        var rows = Array.isArray(grid) ? grid.length : 0;
        if (rows === 0) return new Uint8Array(0);
        var cols = Array.isArray(grid[0]) ? grid[0].length : 0;
        var n = rows * cols;
        var out = new Uint8Array(n * 4);
        for (var r = 0; r < rows; r++) {
            for (var c = 0; c < cols; c++) {
                var v = grid[r][c] > 0.5 || grid[r][c] === 1 ? 255 : 0;
                var i = (r * cols + c) * 4;
                out[i] = v;
                out[i + 1] = v;
                out[i + 2] = v;
                out[i + 3] = 255;
            }
        }
        return out;
    }

    function createFBOWithOptions(gl, width, height, options) {
        options = options || {};
        var useFloat = options.format === "RGBA16F";
        var wrap = options.wrap === "REPEAT" ? gl.REPEAT : gl.CLAMP_TO_EDGE;
        var initialPixels = options.initialPixels || null;

        var texture = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, texture);
        if (useFloat && gl.RGBA16F) {
            gl.texImage2D(
                gl.TEXTURE_2D,
                0,
                gl.RGBA16F,
                width,
                height,
                0,
                gl.RGBA,
                gl.HALF_FLOAT,
                initialPixels
            );
        } else {
            gl.texImage2D(
                gl.TEXTURE_2D,
                0,
                gl.RGBA,
                width,
                height,
                0,
                gl.RGBA,
                gl.UNSIGNED_BYTE,
                initialPixels
            );
        }
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, wrap);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, wrap);

        var fbo = gl.createFramebuffer();
        gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
        gl.framebufferTexture2D(
            gl.FRAMEBUFFER,
            gl.COLOR_ATTACHMENT0,
            gl.TEXTURE_2D,
            texture,
            0
        );
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        gl.bindTexture(gl.TEXTURE_2D, null);

        return { fbo: fbo, texture: texture, width: width, height: height };
    }

    function runTogglePass(state) {
        var toggles = state.toggleMask;
        if (!toggles || toggles.length === 0 || !state.toggleProgram) return;
        var n = Math.min(toggles.length, MAX_TOGGLES_PER_PASS);
        var gl = state.gl;
        var fboRead = state.fboRead;
        var fboWrite = state.fboWrite;
        var w = state.gridSize;
        var toggleProgram = state.toggleProgram;
        var positionBuffer = state.positionBuffer;

        gl.useProgram(toggleProgram);
        gl.bindTexture(gl.TEXTURE_2D, fboRead.texture);
        gl.bindFramebuffer(gl.FRAMEBUFFER, fboWrite.fbo);
        gl.viewport(0, 0, w, w);
        gl.uniform1i(gl.getUniformLocation(toggleProgram, "u_state"), 0);
        gl.uniform2f(gl.getUniformLocation(toggleProgram, "u_gridSize"), w, w);
        gl.uniform1f(
            gl.getUniformLocation(toggleProgram, "u_brushRadius"),
            TOGGLE_BRUSH_RADIUS
        );
        gl.uniform1i(gl.getUniformLocation(toggleProgram, "u_toggleCount"), n);
        for (var t = 0; t < n; t++) {
            var u = gl.getUniformLocation(toggleProgram, "u_toggles[" + t + "]");
            if (u) gl.uniform2f(u, toggles[t].x, toggles[t].y);
        }
        var posLoc = gl.getAttribLocation(toggleProgram, "position");
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.enableVertexAttribArray(posLoc);
        gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

        var tmp = state.fboRead;
        state.fboRead = state.fboWrite;
        state.fboWrite = tmp;
        state.toggleMask = [];
    }

    class GridSubstrate extends Substrate {
        createDisplayElement(phenotype, patternPayload) {
            var stepShader =
                (patternPayload && patternPayload.shader) ||
                (phenotype && phenotype.stepShader);
            if (!stepShader) {
                var fallback = document.createElement("div");
                fallback.className = "organism-canvas-fallback";
                fallback.textContent = "No step shader";
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
            var state = wu.setupPattern(canvas, stepShader);
            if (state && state.error) {
                var errEl = document.createElement("div");
                errEl.className = "organism-canvas-fallback";
                errEl.textContent = state.error || "Shader error";
                return { element: errEl, state: null };
            }
            state.canvas = canvas;
            state.patternPayload = patternPayload || {};
            state.phenotype = phenotype || {};
            state.toggleMask = [];
            return { element: canvas, state: state };
        }

        setup(state, phenotype) {
            if (!state || !state.gl) return;
            var gl = state.gl;
            var w = (phenotype && phenotype.gridSize) || 64;
            var stepIntervalMs = (phenotype && phenotype.stepIntervalMs) || 180;
            var texFormat = (phenotype && phenotype.stateFormat) || "RGBA";
            var wrap = (phenotype && phenotype.wrap) || "REPEAT";

            var initialPixels = null;
            var grid = state.patternPayload && state.patternPayload.grid;
            if (
                grid &&
                Array.isArray(grid) &&
                grid.length === w &&
                grid[0] &&
                grid[0].length === w
            ) {
                initialPixels = gridToRgbaPixelArray(grid);
            }

            var fboOpts = {
                format: texFormat,
                wrap: wrap,
                initialPixels: initialPixels,
            };
            var fboRead = createFBOWithOptions(gl, w, w, fboOpts);
            var fboWrite = createFBOWithOptions(gl, w, w, {
                format: texFormat,
                wrap: wrap,
            });

            var wu = window.WebGLUtils;
            var displayShaderSource =
                (phenotype && phenotype.displayShader) ||
                "#version 300 es\nprecision highp float;\nuniform sampler2D u_state;\nin vec2 vUV;\nout vec4 fragColor;\nvoid main() { fragColor = vec4(texture(u_state, vUV).rgb, 1.0); }";
            var displayResult = wu.createProgram(
                gl,
                wu.VERTEX_SHADER_SOURCE,
                displayShaderSource
            );
            if (!displayResult || displayResult.error) {
                wu.destroyFBO(gl, fboRead);
                wu.destroyFBO(gl, fboWrite);
                return;
            }

            state.fboRead = fboRead;
            state.fboWrite = fboWrite;
            state.displayProgram = displayResult;
            state.gridSize = w;
            state.stepIntervalMs = stepIntervalMs;
            state._lastStepTime = 0;

            if (phenotype && phenotype.toggleShader) {
                var toggleResult = wu.createProgram(
                    gl,
                    wu.VERTEX_SHADER_SOURCE,
                    phenotype.toggleShader
                );
                if (toggleResult && !toggleResult.error) {
                    state.toggleProgram = toggleResult;
                }
            }
        }

        teardown(state) {
            if (!state) return;
            var wu = window.WebGLUtils;
            if (wu) {
                if (state.fboRead) wu.destroyFBO(state.gl, state.fboRead);
                if (state.fboWrite) wu.destroyFBO(state.gl, state.fboWrite);
            }
            state.fboRead = null;
            state.fboWrite = null;
            if (state.displayProgram && state.gl) {
                state.gl.deleteProgram(state.displayProgram);
                state.displayProgram = null;
            }
            if (state.toggleProgram && state.gl) {
                state.gl.deleteProgram(state.toggleProgram);
                state.toggleProgram = null;
            }
        }

        buildParams(phenotype, signalValues) {
            return {};
        }

        render(state, params, signalState) {
            if (
                !state ||
                !state.gl ||
                !state.fboRead ||
                !state.fboWrite ||
                !state.displayProgram
            )
                return;
            var gl = state.gl;
            var program = state.program;
            var positionBuffer = state.positionBuffer;
            var fboRead = state.fboRead;
            var fboWrite = state.fboWrite;
            var displayProgram = state.displayProgram;
            var canvas = state.canvas;
            var w = state.gridSize;
            var stepIntervalMs = state.stepIntervalMs || 180;

            if (state.toggleMask && state.toggleMask.length > 0) {
                runTogglePass(state);
            }

            var now =
                typeof performance !== "undefined" && performance.now
                    ? performance.now()
                    : Date.now();
            var timeSinceStep = now - (state._lastStepTime || 0);
            var shouldStep = timeSinceStep >= stepIntervalMs;

            if (shouldStep && program) {
                gl.activeTexture(gl.TEXTURE0);
                gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
                var posLoc = gl.getAttribLocation(program, "position");
                gl.enableVertexAttribArray(posLoc);
                gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

                gl.useProgram(program);
                gl.uniform1i(gl.getUniformLocation(program, "u_state"), 0);
                gl.uniform2f(
                    gl.getUniformLocation(program, "u_texelSize"),
                    1 / w,
                    1 / w
                );
                gl.bindTexture(gl.TEXTURE_2D, fboRead.texture);
                gl.bindFramebuffer(gl.FRAMEBUFFER, fboWrite.fbo);
                gl.viewport(0, 0, w, w);
                gl.clearColor(0, 0, 0, 1);
                gl.clear(gl.COLOR_BUFFER_BIT);
                gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

                var tmp = state.fboRead;
                state.fboRead = state.fboWrite;
                state.fboWrite = tmp;
                state._lastStepTime = now;
            }

            gl.bindFramebuffer(gl.FRAMEBUFFER, null);
            gl.viewport(0, 0, canvas.width, canvas.height);
            gl.useProgram(displayProgram);
            gl.uniform1i(gl.getUniformLocation(displayProgram, "u_state"), 0);
            gl.bindTexture(gl.TEXTURE_2D, state.fboRead.texture);
            var posLocD = gl.getAttribLocation(displayProgram, "position");
            gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
            gl.enableVertexAttribArray(posLocD);
            gl.vertexAttribPointer(posLocD, 2, gl.FLOAT, false, 0, 0);
            gl.clearColor(0, 0, 0, 1);
            gl.clear(gl.COLOR_BUFFER_BIT);
            gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
        }

        handleInteraction(state, x, y, interactionType) {
            if (!state) return;
            if (state.toggleMask == null) state.toggleMask = [];
            state.toggleMask.push({ x: x, y: y });
        }
    }

    window.GridSubstrate = GridSubstrate;
})();
