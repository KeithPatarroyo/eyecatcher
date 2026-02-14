/**
 * CA (Conway's Game of Life) substrate adapter.
 * Stateful 2D grid: FBO ping-pong, initial state from pattern.grid.
 * Canvas click toggles cell (black <-> white); toggle mask applied before each GOL step.
 * Uses createStatefulAdapter for FBO lifecycle and step/display loop.
 */
(function () {
    "use strict";

    const GOL_GRID_SIZE = 64;
    const MAX_TOGGLES_PER_PASS = 64;
    const GOL_STEP_INTERVAL_MS = 180;
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

    function runTogglePass(patternData, gl) {
        var toggles = patternData.toggleMask;
        if (!toggles || toggles.length === 0 || !patternData.toggleProgram) return;
        var n = Math.min(toggles.length, MAX_TOGGLES_PER_PASS);
        var fboRead = patternData.fboRead;
        var fboWrite = patternData.fboWrite;
        var w = patternData.statefulGridSize || GOL_GRID_SIZE;
        var toggleProgram = patternData.toggleProgram;
        var positionBuffer = patternData.positionBuffer;

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
        var posLocT = gl.getAttribLocation(toggleProgram, "position");
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.enableVertexAttribArray(posLocT);
        gl.vertexAttribPointer(posLocT, 2, gl.FLOAT, false, 0, 0);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

        var tmp = patternData.fboRead;
        patternData.fboRead = patternData.fboWrite;
        patternData.fboWrite = tmp;
        patternData.toggleMask = [];
    }

    function updateLiveCount(patternData) {
        var w = patternData.statefulGridSize || GOL_GRID_SIZE;
        var buf = patternData._readPixelsBuffer;
        if (!buf || buf.length !== w * w * 4) {
            buf = new Uint8Array(w * w * 4);
            patternData._readPixelsBuffer = buf;
        }
        patternData.gl.bindFramebuffer(
            patternData.gl.FRAMEBUFFER,
            patternData.fboRead.fbo
        );
        patternData.gl.readPixels(
            0,
            0,
            w,
            w,
            patternData.gl.RGBA,
            patternData.gl.UNSIGNED_BYTE,
            buf
        );
        patternData.gl.bindFramebuffer(patternData.gl.FRAMEBUFFER, null);
        var count = 0;
        for (var i = 0; i < w * w; i++) {
            if (buf[i * 4] >= 128) count++;
        }
        patternData._liveCount = count;
    }

    var FINGERPRINT_ALPHABET =
        "0123456789aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ";

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
        return Math.round((live / total) * 100) + "%";
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

    var caAdapter = window.createStatefulAdapter({
        id: "ca",
        outputType: "grid",
        gridSize: GOL_GRID_SIZE,
        stepIntervalMs: GOL_STEP_INTERVAL_MS,
        texFormat: "RGBA",
        wrap: "REPEAT",

        initState: function (width, height, patternData) {
            var grid = patternData && patternData.grid;
            grid = copyGrid(grid) || grid;
            if (
                grid &&
                Array.isArray(grid) &&
                grid.length === width &&
                Array.isArray(grid[0]) &&
                grid[0].length === height
            ) {
                return gridToRgbaPixelArray(grid);
            }
            return new Uint8Array(width * height * 4);
        },

        stepUniforms: function () {
            return {};
        },

        displayShaderSource: DISPLAY_FRAGMENT_SOURCE,

        beforeStep: function (patternData, gl) {
            if (patternData.toggleMask && patternData.toggleMask.length > 0) {
                runTogglePass(patternData, gl);
            }
        },

        createExtraPrograms: function (gl) {
            var toggleProgram = createProgram(
                gl,
                VERTEX_SHADER_SOURCE,
                TOGGLE_FRAGMENT_SOURCE
            );
            return toggleProgram ? { toggleProgram: toggleProgram } : {};
        },

        teardownExtra: function (entry, gl) {
            if (entry.toggleProgram) {
                gl.deleteProgram(entry.toggleProgram);
                entry.toggleProgram = null;
            }
        },

        onInteraction: function (patternData, x, y) {
            if (patternData.toggleMask == null) patternData.toggleMask = [];
            patternData.toggleMask.push({ x: x, y: y });
        },

        preparePatternData: function (patternData, pattern) {
            if (pattern && pattern.grid !== undefined) {
                patternData.grid = pattern.grid;
            }
            if (patternData.toggleMask == null) patternData.toggleMask = [];
            patternData._liveCount =
                patternData.grid && Array.isArray(patternData.grid)
                    ? countLive(patternData.grid)
                    : 0;
        },

        getMetaLabel: function (pattern) {
            if (!pattern) return "? \u00B7 0% \u00B7 0 alive";
            return buildCaMetaSuffix(pattern.grid, countLive(pattern.grid));
        },

        getMetaIdPrefix: function () {
            return "Pattern ";
        },

        onAfterRender: function (patternData) {
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
        },

        isGenomeFormat: function (obj) {
            return (
                obj &&
                Array.isArray(obj.grid) &&
                obj.grid.length > 0 &&
                Array.isArray(obj.grid[0])
            );
        },

        capabilities: {
            save: true,
            network: false,
            timeOutput: false,
            adjustWeight: false,
        },

        gridOverlap: gridOverlap,
    });

    caAdapter.lifecycle = "frame";
    caAdapter.getDisplayData = function (genomes, options) {
        var SA = window.SubstrateAdapters;
        return SA && SA.fetchViaEvaluate
            ? SA.fetchViaEvaluate(genomes, options)
            : Promise.reject(
                  new Error("SubstrateAdapters.fetchViaEvaluate not available")
              );
    };
    caAdapter.createDisplayElement = function (pattern, _options) {
        var PatternRenderer = window.PatternRenderer;
        if (!PatternRenderer || !pattern) {
            var fallback = document.createElement("div");
            fallback.className = "pattern-canvas-fallback";
            fallback.textContent = "Display not available";
            return { element: fallback, patternData: null };
        }
        var shader = pattern.shader;
        if (!shader) {
            if (pattern.image) {
                var img = document.createElement("img");
                img.className = "pattern-canvas pattern-image";
                img.src = pattern.image;
                img.width = 256;
                img.height = 256;
                img.alt = "Pattern " + (pattern.id != null ? pattern.id : "");
                return { element: img, patternData: null };
            }
            var noShader = document.createElement("div");
            noShader.className = "pattern-canvas-fallback";
            noShader.textContent = "No shader";
            return { element: noShader, patternData: null };
        }
        var canvas = document.createElement("canvas");
        canvas.className = "pattern-canvas";
        canvas.width = 256;
        canvas.height = 256;
        var patternData = PatternRenderer.setupPattern(canvas, shader);
        if (!patternData || patternData.error) {
            var errEl = document.createElement("div");
            errEl.className = "pattern-canvas-fallback";
            errEl.textContent =
                patternData && patternData.error ? patternData.error : "Shader error";
            return { element: errEl, patternData: null };
        }
        return { element: canvas, patternData: patternData };
    };

    caAdapter.onAfterRender = function (patternData) {
        if (patternData.fboRead && patternData.fboRead.fbo) {
            updateLiveCount(patternData);
        }
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
    };

    if (window.SubstrateAdapters) {
        window.SubstrateAdapters.register(caAdapter);
    }
})();
