/**
 * CA (Conway's Game of Life) substrate adapter.
 * Stateful 2D grid: FBO ping-pong, initial state from pattern.grid.
 * Canvas click toggles cell (black <-> white); toggle mask applied before each GOL step.
 */
(function () {
    "use strict";

    const GOL_GRID_SIZE = 64;
    const MAX_TOGGLES_PER_PASS = 64;
    /** Minimum ms between GOL steps to reduce flicker and screen burn-in risk. */
    const GOL_STEP_INTERVAL_MS = 180;
    /** Toggle brush radius in cells (0 = single cell, 1 = 3×3, 2 = 5×5). Change this to adjust brush size. */
    const TOGGLE_BRUSH_RADIUS = 1;

    var VERTEX_SHADER_SOURCE =
        "#version 300 es\n" +
        "in vec2 position;\n" +
        "out vec2 vUV;\n" +
        "void main() {\n" +
        "  vUV = position * 0.5 + 0.5;\n" +
        "  gl_Position = vec4(position, 0.0, 1.0);\n" +
        "}\n";

    var DISPLAY_FRAGMENT_SOURCE =
        "#version 300 es\n" +
        "precision highp float;\n" +
        "uniform sampler2D u_state;\n" +
        "in vec2 vUV;\n" +
        "out vec4 fragColor;\n" +
        "void main() {\n" +
        "  float v = texture(u_state, vUV).r;\n" +
        "  fragColor = vec4(v, v, v, 1.0);\n" +
        "}\n";

    var TOGGLE_FRAGMENT_SOURCE =
        "#version 300 es\n" +
        "precision highp float;\n" +
        "uniform sampler2D u_state;\n" +
        "uniform vec2 u_gridSize;\n" +
        "uniform int u_toggleCount;\n" +
        "uniform float u_brushRadius;\n" +
        "uniform vec2 u_toggles[64];\n" +
        "in vec2 vUV;\n" +
        "out vec4 fragColor;\n" +
        "void main() {\n" +
        "  float v = texture(u_state, vUV).r;\n" +
        "  vec2 cell = min(floor(vUV * u_gridSize), u_gridSize - 1.0);\n" +
        "  for (int i = 0; i < 64; i++) {\n" +
        "    if (i >= u_toggleCount) break;\n" +
        "    vec2 tc = u_toggles[i];\n" +
        "    vec2 toggleCell = min(floor(vec2(tc.x, 1.0 - tc.y) * u_gridSize), u_gridSize - 1.0);\n" +
        "    float dist = max(abs(cell.x - toggleCell.x), abs(cell.y - toggleCell.y));\n" +
        "    if (dist <= u_brushRadius) {\n" +
        "      v = 1.0 - v;\n" +
        "      break;\n" +
        "    }\n" +
        "  }\n" +
        "  fragColor = vec4(v, v, v, 1.0);\n" +
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

    function createFBOWithRepeat(gl, width, height, initialPixelsRGBA) {
        var texture = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.texImage2D(
            gl.TEXTURE_2D,
            0,
            gl.RGBA,
            width,
            height,
            0,
            gl.RGBA,
            gl.UNSIGNED_BYTE,
            initialPixelsRGBA || null
        );
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);

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

    function copyGrid(grid) {
        if (!grid || !Array.isArray(grid) || grid.length === 0) return null;
        var rows = grid.length;
        var cols = Array.isArray(grid[0]) ? grid[0].length : 0;
        if (cols === 0) return null;
        var out = [];
        for (var r = 0; r < rows; r++) {
            out.push(Array.isArray(grid[r]) ? grid[r].slice(0, cols) : []);
        }
        return out;
    }

    function onSetup(entry, gl) {
        var grid = entry.grid;
        grid = copyGrid(grid) || grid;
        var w = GOL_GRID_SIZE;
        var h = GOL_GRID_SIZE;
        var pixels = null;
        if (grid && Array.isArray(grid) && grid.length > 0) {
            var rows = grid.length;
            var cols = Array.isArray(grid[0]) ? grid[0].length : 0;
            if (rows === w && cols === h) {
                pixels = gridToRgbaPixelArray(grid);
            }
        }
        if (!pixels || pixels.length !== w * h * 4) {
            pixels = new Uint8Array(w * h * 4);
        }

        var fboRead = createFBOWithRepeat(gl, w, h, pixels);
        var fboWrite = createFBOWithRepeat(gl, w, h, null);

        var displayProgram = createProgram(
            gl,
            VERTEX_SHADER_SOURCE,
            DISPLAY_FRAGMENT_SOURCE
        );
        var toggleProgram = createProgram(
            gl,
            VERTEX_SHADER_SOURCE,
            TOGGLE_FRAGMENT_SOURCE
        );
        if (!displayProgram || !toggleProgram) {
            if (displayProgram) gl.deleteProgram(displayProgram);
            if (toggleProgram) gl.deleteProgram(toggleProgram);
            gl.deleteFramebuffer(fboRead.fbo);
            gl.deleteTexture(fboRead.texture);
            gl.deleteFramebuffer(fboWrite.fbo);
            gl.deleteTexture(fboWrite.texture);
            return;
        }

        entry.fboRead = fboRead;
        entry.fboWrite = fboWrite;
        entry.displayProgram = displayProgram;
        entry.toggleProgram = toggleProgram;
        entry.golGridSize = w;
        if (entry.toggleMask == null) entry.toggleMask = [];
        entry._liveCount = grid && Array.isArray(grid) ? countLive(grid) : 0;
    }

    function onTeardown(entry, gl) {
        if (!entry) return;
        if (entry.fboRead) {
            gl.deleteFramebuffer(entry.fboRead.fbo);
            gl.deleteTexture(entry.fboRead.texture);
            entry.fboRead = null;
        }
        if (entry.fboWrite) {
            gl.deleteFramebuffer(entry.fboWrite.fbo);
            gl.deleteTexture(entry.fboWrite.texture);
            entry.fboWrite = null;
        }
        if (entry.displayProgram) {
            gl.deleteProgram(entry.displayProgram);
            entry.displayProgram = null;
        }
        if (entry.toggleProgram) {
            gl.deleteProgram(entry.toggleProgram);
            entry.toggleProgram = null;
        }
    }

    function renderGol(patternData, _uniformValues, _signalState) {
        var gl = patternData.gl;
        var program = patternData.program;
        var positionBuffer = patternData.positionBuffer;
        var fboRead = patternData.fboRead;
        var fboWrite = patternData.fboWrite;
        var displayProgram = patternData.displayProgram;
        var toggleProgram = patternData.toggleProgram;
        var canvas = patternData.canvas;
        var w = patternData.golGridSize || GOL_GRID_SIZE;
        var h = w;

        if (!fboRead || !fboWrite || !displayProgram || !canvas) return;

        var now =
            typeof performance !== "undefined" && performance.now
                ? performance.now()
                : Date.now();
        patternData._lastGolStepTime = patternData._lastGolStepTime || 0;
        var timeSinceStep = now - patternData._lastGolStepTime;
        var shouldStep = timeSinceStep >= GOL_STEP_INTERVAL_MS;

        var posLoc = gl.getAttribLocation(program, "position");
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.enableVertexAttribArray(posLoc);
        gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

        gl.activeTexture(gl.TEXTURE0);

        var hadToggles = false;
        var toggles = patternData.toggleMask;
        if (toggles && toggles.length > 0 && toggleProgram) {
            var n = Math.min(toggles.length, MAX_TOGGLES_PER_PASS);
            gl.useProgram(toggleProgram);
            gl.bindTexture(gl.TEXTURE_2D, fboRead.texture);
            gl.bindFramebuffer(gl.FRAMEBUFFER, fboWrite.fbo);
            gl.viewport(0, 0, w, h);
            gl.uniform1i(gl.getUniformLocation(toggleProgram, "u_state"), 0);
            gl.uniform2f(gl.getUniformLocation(toggleProgram, "u_gridSize"), w, h);
            gl.uniform1f(
                gl.getUniformLocation(toggleProgram, "u_brushRadius"),
                TOGGLE_BRUSH_RADIUS
            );
            gl.uniform1i(gl.getUniformLocation(toggleProgram, "u_toggleCount"), n);
            for (var t = 0; t < n; t++) {
                var u = gl.getUniformLocation(toggleProgram, "u_toggles[" + t + "]");
                if (u) gl.uniform2f(u, toggles[t].x, toggles[t].y);
            }
            var posLocT = gl.getAttribLocation(toggleProgram, "position");
            gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
            gl.enableVertexAttribArray(posLocT);
            gl.vertexAttribPointer(posLocT, 2, gl.FLOAT, false, 0, 0);
            gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
            var tmpSwap = fboRead;
            patternData.fboRead = fboWrite;
            patternData.fboWrite = tmpSwap;
            fboRead = patternData.fboRead;
            fboWrite = patternData.fboWrite;
            patternData.toggleMask = [];
            hadToggles = true;
        }

        if (!hadToggles && shouldStep) {
            gl.useProgram(program);
            gl.uniform1i(gl.getUniformLocation(program, "u_state"), 0);
            gl.uniform2f(gl.getUniformLocation(program, "u_texelSize"), 1 / w, 1 / h);
            gl.bindTexture(gl.TEXTURE_2D, fboRead.texture);
            gl.bindFramebuffer(gl.FRAMEBUFFER, fboWrite.fbo);
            gl.viewport(0, 0, w, h);
            gl.clearColor(0, 0, 0, 1);
            gl.clear(gl.COLOR_BUFFER_BIT);
            gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

            var tmp = fboRead;
            patternData.fboRead = fboWrite;
            patternData.fboWrite = tmp;
            patternData._lastGolStepTime = now;
        }

        var didUpdate = hadToggles || (!hadToggles && shouldStep);
        if (didUpdate && patternData.fboRead && patternData.fboRead.fbo) {
            var buf = patternData._readPixelsBuffer;
            if (!buf || buf.length !== w * h * 4) {
                buf = new Uint8Array(w * h * 4);
                patternData._readPixelsBuffer = buf;
            }
            gl.bindFramebuffer(gl.FRAMEBUFFER, patternData.fboRead.fbo);
            gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, buf);
            gl.bindFramebuffer(gl.FRAMEBUFFER, null);
            var count = 0;
            for (var i = 0; i < w * h; i++) {
                if (buf[i * 4] >= 128) count++;
            }
            patternData._liveCount = count;
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

    function preparePatternData(patternData, pattern) {
        if (pattern && pattern.grid !== undefined) {
            patternData.grid = pattern.grid;
        }
        if (patternData.toggleMask == null) {
            patternData.toggleMask = [];
        }
    }

    function onCellInteraction(patternData, x, y, _type) {
        if (!patternData) return;
        if (patternData.toggleMask == null) patternData.toggleMask = [];
        patternData.toggleMask.push({ x: x, y: y });
    }

    function onBeforeRender(_patternData, _context) {}

    function onAfterRender(patternData, _context) {
        if (patternData._liveCount === undefined) return;
        var card = document.querySelector(
            '.pattern-card[data-id="' + String(patternData.patternId) + '"]'
        );
        if (!card) return;
        var meta = card.querySelector(".pattern-meta");
        if (meta) {
            var suffix = buildCaMetaSuffix(
                patternData.grid,
                patternData._liveCount,
                patternData._mostSimilarId,
                patternData._mostSimilarOverlap
            );
            meta.textContent = "Pattern " + patternData.patternId + " | " + suffix;
        }
    }

    /** Base-62 alphabet: 0-9, then aA bB cC ... so a and A are adjacent. */
    var FINGERPRINT_ALPHABET =
        "0123456789aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ";

    /**
     * Deterministic fingerprint: 8×8 downsampled grid as base-62 (0-9, a-z, A-Z).
     * Alphabet orders a,A,b,B,... so small changes flip between nearby chars. 64 bits → 11 chars.
     */
    function gridFingerprint(grid) {
        if (!grid || !Array.isArray(grid) || grid.length === 0) return "0".repeat(11);
        var rows = grid.length;
        var cols = Array.isArray(grid[0]) ? grid[0].length : 0;
        if (cols === 0) return "0".repeat(11);
        var step = Math.max(1, Math.floor(Math.max(rows, cols) / 8));
        var bits = [];
        for (var r = 0; r < 8; r++) {
            var y = Math.min(r * step, rows - 1);
            var row = grid[y];
            if (!Array.isArray(row)) {
                bits.push.apply(bits, [0, 0, 0, 0, 0, 0, 0, 0]);
                continue;
            }
            for (var c = 0; c < 8; c++) {
                var x = Math.min(c * step, cols - 1);
                var v = row[x];
                bits.push(v > 0.5 || v === 1 ? 1 : 0);
            }
        }
        var n = BigInt(0);
        for (var i = 0; i < 64; i++) n = n * BigInt(2) + BigInt(bits[i]);
        var base = BigInt(FINGERPRINT_ALPHABET.length);
        var s = "";
        while (n > 0) {
            var digit = Number(n % base);
            n = n / base;
            s = FINGERPRINT_ALPHABET[digit] + s;
        }
        return s.length >= 11 ? s : FINGERPRINT_ALPHABET[0].repeat(11 - s.length) + s;
    }

    function initialDensity(grid) {
        if (!grid || !Array.isArray(grid) || grid.length === 0) return "0%";
        var rows = grid.length;
        var cols = Array.isArray(grid[0]) ? grid[0].length : 0;
        if (cols === 0) return "0%";
        var total = rows * cols;
        var live = countLive(grid);
        var pct = Math.round((live / total) * 100);
        return pct + "%";
    }

    function gridOverlap(gridA, gridB) {
        if (!gridA || !gridB || !Array.isArray(gridA) || !Array.isArray(gridB))
            return 0;
        var rows = gridA.length;
        if (rows === 0 || gridB.length !== rows) return 0;
        var cols = Array.isArray(gridA[0]) ? gridA[0].length : 0;
        if (cols === 0 || !Array.isArray(gridB[0]) || gridB[0].length !== cols)
            return 0;
        var match = 0;
        var total = rows * cols;
        for (var r = 0; r < rows; r++) {
            for (var c = 0; c < cols; c++) {
                var a = gridA[r][c] > 0.5 || gridA[r][c] === 1 ? 1 : 0;
                var b = gridB[r][c] > 0.5 || gridB[r][c] === 1 ? 1 : 0;
                if (a === b) match++;
            }
        }
        return total > 0 ? match / total : 0;
    }

    function countLive(grid) {
        if (!grid || !Array.isArray(grid)) return 0;
        var n = 0;
        for (var r = 0; r < grid.length; r++) {
            var row = grid[r];
            if (!Array.isArray(row)) continue;
            for (var c = 0; c < row.length; c++) {
                if (row[c] > 0.5 || row[c] === 1) n++;
            }
        }
        return n;
    }

    function buildCaMetaSuffix(grid, liveCount, mostSimilarId, mostSimilarOverlap) {
        var fp = gridFingerprint(grid);
        var density = initialDensity(grid);
        var n = liveCount != null ? liveCount : grid ? countLive(grid) : 0;
        var s = fp + " \u00B7 " + density + " \u00B7 " + n + " alive";
        if (
            mostSimilarId != null &&
            mostSimilarOverlap != null &&
            mostSimilarOverlap >= 0.7 &&
            mostSimilarOverlap < 1
        ) {
            s += " \u00B7 ~ #" + mostSimilarId;
        }
        return s;
    }

    var caAdapter = {
        id: "ca",
        outputType: "grid",
        isGenomeFormat: function (obj) {
            return (
                obj &&
                Array.isArray(obj.grid) &&
                obj.grid.length > 0 &&
                Array.isArray(obj.grid[0])
            );
        },
        hasSignalControls: false,
        capabilities: {
            save: true,
            network: false,
            timeOutput: false,
            adjustWeight: false,
        },
        preparePatternData: preparePatternData,
        render: renderGol,
        getMetaLabel: function (pattern) {
            if (!pattern) return "? \u00B7 0% \u00B7 0 alive";
            return buildCaMetaSuffix(pattern.grid, countLive(pattern.grid));
        },
        gridOverlap: gridOverlap,
        onSetup: onSetup,
        onTeardown: onTeardown,
        onCellInteraction: onCellInteraction,
        onBeforeRender: onBeforeRender,
        onAfterRender: onAfterRender,
    };

    if (window.SubstrateAdapters) {
        window.SubstrateAdapters.register(caAdapter);
    }
})();
