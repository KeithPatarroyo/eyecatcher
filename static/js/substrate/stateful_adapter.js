/**
 * Stateful (FBO ping-pong) substrate adapter class.
 * Use for representations that maintain GPU state between frames (e.g. CA, NCA).
 * Requires: PatternRenderer (createFBO, swapFBOs, destroyFBO) for shared FBO helpers.
 */
(function () {
    "use strict";

    var VERTEX_SHADER_SOURCE =
        "#version 300 es\n" +
        "in vec2 position;\n" +
        "out vec2 vUV;\n" +
        "void main() {\n" +
        "  vUV = position * 0.5 + 0.5;\n" +
        "  gl_Position = vec4(position, 0.0, 1.0);\n" +
        "}\n";

    var DEFAULT_DISPLAY_FRAGMENT_SOURCE =
        "#version 300 es\n" +
        "precision highp float;\n" +
        "uniform sampler2D u_state;\n" +
        "in vec2 vUV;\n" +
        "out vec4 fragColor;\n" +
        "void main() {\n" +
        "  fragColor = vec4(texture(u_state, vUV).rgb, 1.0);\n" +
        "}\n";

    function createProgram(gl, vsSource, fsSource) {
        var vs = gl.createShader(gl.VERTEX_SHADER);
        gl.shaderSource(vs, vsSource);
        gl.compileShader(vs);
        if (!gl.getShaderParameter(vs, gl.COMPILE_STATUS)) {
            gl.deleteShader(vs);
            return null;
        }
        var fs = gl.createShader(gl.FRAGMENT_SHADER);
        gl.shaderSource(fs, fsSource);
        gl.compileShader(fs);
        if (!gl.getShaderParameter(fs, gl.COMPILE_STATUS)) {
            gl.deleteShader(vs);
            gl.deleteShader(fs);
            return null;
        }
        var program = gl.createProgram();
        gl.attachShader(program, vs);
        gl.attachShader(program, fs);
        gl.linkProgram(program);
        gl.deleteShader(vs);
        gl.deleteShader(fs);
        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
            gl.deleteProgram(program);
            return null;
        }
        return program;
    }

    function createFBOStateful(gl, width, height, options) {
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

    var SubstrateAdapter = window.SubstrateAdapter;

    class StatefulAdapter extends SubstrateAdapter {
        /**
         * @param {Object} spec - id, outputType, isGenomeFormat, gridSize?, stepIntervalMs?, ...
         */
        constructor(spec) {
            spec = spec || {};
            super({
                id: spec.id,
                outputType: spec.outputType,
                isGenomeFormat: spec.isGenomeFormat,
                hasSignalControls: false,
                capabilities: spec.capabilities || {
                    save: true,
                    network: false,
                    timeOutput: false,
                    adjustWeight: false,
                },
            });
            this._spec = spec;
            this._gridSize = spec.gridSize || 64;
            this._stepIntervalMs = spec.stepIntervalMs || 100;
            this._texFormat = spec.texFormat || "RGBA";
            this._wrap = spec.wrap || "CLAMP";
            this._displayShaderSource =
                spec.displayShaderSource || DEFAULT_DISPLAY_FRAGMENT_SOURCE;

            this.onCellInteraction = spec.onInteraction || function () {};
            this.onBeforeRender = spec.onBeforeRender || function () {};
            this.onAfterRender = spec.onAfterRender || function () {};
            this.preparePatternData = spec.preparePatternData || function () {};
            this.getMetaLabel =
                spec.getMetaLabel ||
                function () {
                    return "";
                };
            if (spec.gridOverlap) this.gridOverlap = spec.gridOverlap;
        }

        onSetup(entry, gl) {
            var w = this._gridSize;
            var h = this._gridSize;
            var spec = this._spec;
            var initialPixels = spec.initState ? spec.initState(w, h, entry) : null;

            var fboOpts = {
                format: this._texFormat,
                wrap: this._wrap,
                initialPixels: initialPixels,
            };
            var fboRead = createFBOStateful(gl, w, h, fboOpts);
            var fboWrite = createFBOStateful(gl, w, h, {
                format: this._texFormat,
                wrap: this._wrap,
            });

            var displayProgram = createProgram(
                gl,
                VERTEX_SHADER_SOURCE,
                this._displayShaderSource
            );
            if (!displayProgram) {
                window.PatternRenderer.destroyFBO(gl, fboRead);
                window.PatternRenderer.destroyFBO(gl, fboWrite);
                return;
            }

            entry.fboRead = fboRead;
            entry.fboWrite = fboWrite;
            entry.displayProgram = displayProgram;
            entry.statefulGridSize = w;
            entry._lastStepTime = 0;

            if (spec.createExtraPrograms) {
                var extra = spec.createExtraPrograms(gl);
                if (extra && typeof extra === "object") {
                    for (var key in extra) {
                        if (Object.prototype.hasOwnProperty.call(extra, key)) {
                            entry[key] = extra[key];
                        }
                    }
                }
            }
        }

        onTeardown(entry, gl) {
            if (!entry) return;
            if (entry.fboRead) {
                window.PatternRenderer.destroyFBO(gl, entry.fboRead);
            }
            if (entry.fboWrite) {
                window.PatternRenderer.destroyFBO(gl, entry.fboWrite);
            }
            entry.fboRead = null;
            entry.fboWrite = null;
            if (entry.displayProgram) {
                gl.deleteProgram(entry.displayProgram);
                entry.displayProgram = null;
            }
            if (this._spec.teardownExtra) this._spec.teardownExtra(entry, gl);
        }

        render(patternData, uniformValues, _signalState) {
            var gl = patternData.gl;
            var program = patternData.program;
            var positionBuffer = patternData.positionBuffer;
            var fboRead = patternData.fboRead;
            var fboWrite = patternData.fboWrite;
            var displayProgram = patternData.displayProgram;
            var canvas = patternData.canvas;
            var w = patternData.statefulGridSize || this._gridSize;
            var h = w;
            var spec = this._spec;
            var stepIntervalMs = this._stepIntervalMs;

            if (!fboRead || !fboWrite || !displayProgram || !canvas) return;

            var now =
                typeof performance !== "undefined" && performance.now
                    ? performance.now()
                    : Date.now();
            var timeSinceStep = now - (patternData._lastStepTime || 0);
            var shouldStep = timeSinceStep >= stepIntervalMs;

            if (spec.beforeStep && typeof spec.beforeStep === "function") {
                spec.beforeStep(patternData, gl);
            }

            if (shouldStep && program) {
                gl.activeTexture(gl.TEXTURE0);
                gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
                var posLoc = gl.getAttribLocation(program, "position");
                gl.enableVertexAttribArray(posLoc);
                gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

                gl.useProgram(program);
                var stepUniforms = spec.stepUniforms
                    ? spec.stepUniforms(patternData, uniformValues || {})
                    : {};
                for (var name in stepUniforms) {
                    if (!Object.prototype.hasOwnProperty.call(stepUniforms, name))
                        continue;
                    var loc = gl.getUniformLocation(program, name);
                    if (loc === null) continue;
                    var val = stepUniforms[name];
                    if (Array.isArray(val)) {
                        if (val.length === 2) gl.uniform2f(loc, val[0], val[1]);
                        else if (val.length === 1) gl.uniform1f(loc, val[0]);
                    } else {
                        gl.uniform1f(loc, val);
                    }
                }
                gl.uniform1i(gl.getUniformLocation(program, "u_state"), 0);
                gl.uniform2f(
                    gl.getUniformLocation(program, "u_texelSize"),
                    1 / w,
                    1 / h
                );
                gl.bindTexture(gl.TEXTURE_2D, fboRead.texture);
                gl.bindFramebuffer(gl.FRAMEBUFFER, fboWrite.fbo);
                gl.viewport(0, 0, w, h);
                gl.clearColor(0, 0, 0, 1);
                gl.clear(gl.COLOR_BUFFER_BIT);
                gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

                var tmp = fboRead;
                patternData.fboRead = fboWrite;
                patternData.fboWrite = tmp;
                patternData._lastStepTime = now;
            }

            gl.bindFramebuffer(gl.FRAMEBUFFER, null);
            gl.viewport(0, 0, canvas.width, canvas.height);
            gl.useProgram(displayProgram);
            gl.uniform1i(gl.getUniformLocation(displayProgram, "u_state"), 0);
            gl.bindTexture(gl.TEXTURE_2D, patternData.fboRead.texture);
            var posLocD = gl.getAttribLocation(displayProgram, "position");
            gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
            gl.enableVertexAttribArray(posLocD);
            gl.vertexAttribPointer(posLocD, 2, gl.FLOAT, false, 0, 0);
            gl.clearColor(0, 0, 0, 1);
            gl.clear(gl.COLOR_BUFFER_BIT);
            gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
        }
    }

    function createStatefulAdapter(spec) {
        return new StatefulAdapter(spec);
    }

    window.StatefulAdapter = StatefulAdapter;
    window.createStatefulAdapter = createStatefulAdapter;
})();
