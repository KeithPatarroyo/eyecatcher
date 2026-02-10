/**
 * Pattern Renderer Module for Eyecatcher
 *
 * WebGL 2 setup, shader compilation, and pattern draw for dual-CPPN fragment shaders.
 * Used by the main grid and by community/population previews.
 *
 * Dependencies: none (signal state passed into renderPattern).
 */
(function () {
    "use strict";

    const PATTERN_CANVAS_SIZE = 256;

    const VERTEX_SHADER_SOURCE = `#version 300 es
        in vec2 position;
        out vec2 vUV;

        void main() {
            vUV = position * 0.5 + 0.5;
            gl_Position = vec4(position, 0.0, 1.0);
        }
    `;

    function createWebGLContext(canvas) {
        const gl = canvas.getContext("webgl2");
        if (!gl) {
            console.error("WebGL 2 not supported");
            return null;
        }
        return gl;
    }

    function compileShader(gl, type, source) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);

        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            console.error("Shader compilation error:", gl.getShaderInfoLog(shader));
            gl.deleteShader(shader);
            return null;
        }

        return shader;
    }

    function createProgram(gl, vertexSource, fragmentSource) {
        const vertexShader = compileShader(gl, gl.VERTEX_SHADER, vertexSource);
        const fragmentShader = compileShader(gl, gl.FRAGMENT_SHADER, fragmentSource);

        if (!vertexShader || !fragmentShader) return null;

        const program = gl.createProgram();
        gl.attachShader(program, vertexShader);
        gl.attachShader(program, fragmentShader);
        gl.linkProgram(program);

        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
            console.error("Program linking error:", gl.getProgramInfoLog(program));
            gl.deleteProgram(program);
            return null;
        }

        return program;
    }

    /**
     * Create WebGL program and buffer for a pattern canvas.
     * @param {HTMLCanvasElement} canvas
     * @param {string} shaderCode - Fragment shader source (GLSL)
     * @returns {{ gl: WebGL2RenderingContext, program: WebGLProgram, positionBuffer: WebGLBuffer } | null}
     */
    function setupPattern(canvas, shaderCode) {
        const gl = createWebGLContext(canvas);
        if (!gl) return null;

        const program = createProgram(gl, VERTEX_SHADER_SOURCE, shaderCode);
        if (!program) return null;

        const positions = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);

        const positionBuffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);

        return { gl, program, positionBuffer };
    }

    /**
     * Draw one frame of a pattern with given uniforms.
     * @param {Object} patternData - From setupPattern
     * @param {number} time - Normalized time (0–1 or unbounded for infinite mode)
     * @param {number} mouseSpd - Mouse speed signal
     * @param {number} mouseDist - Mouse distance to canvas (0–1)
     * @param {number} inact - Inactivity/activity level
     * @param {Object} signalState - { time: {...}, visual: {...} } for CPPN signal toggles
     */
    function renderPattern(patternData, time, mouseSpd, mouseDist, inact, signalState) {
        const { gl, program, positionBuffer } = patternData;
        const sig = signalState || { time: {}, visual: {} };

        gl.useProgram(program);

        gl.uniform1f(gl.getUniformLocation(program, "uTime"), time);
        gl.uniform1f(gl.getUniformLocation(program, "uMouseSpeed"), mouseSpd);
        gl.uniform1f(gl.getUniformLocation(program, "uMouseDist"), mouseDist);
        gl.uniform1f(gl.getUniformLocation(program, "uInactivity"), inact);

        gl.uniform1f(
            gl.getUniformLocation(program, "uTimeEnableRawTime"),
            sig.time.rawTime ? 1.0 : 0.0
        );
        gl.uniform1f(
            gl.getUniformLocation(program, "uTimeEnableMouseSpeed"),
            sig.time.mouseSpeed ? 1.0 : 0.0
        );
        gl.uniform1f(
            gl.getUniformLocation(program, "uTimeEnableMouseDist"),
            sig.time.mouseDist ? 1.0 : 0.0
        );
        gl.uniform1f(
            gl.getUniformLocation(program, "uTimeEnableInactivity"),
            sig.time.inactivity ? 1.0 : 0.0
        );

        gl.uniform1f(
            gl.getUniformLocation(program, "uVisualEnableTime"),
            sig.visual.time ? 1.0 : 0.0
        );
        gl.uniform1f(
            gl.getUniformLocation(program, "uVisualEnableMouseSpeed"),
            sig.visual.mouseSpeed ? 1.0 : 0.0
        );
        gl.uniform1f(
            gl.getUniformLocation(program, "uVisualEnableMouseDist"),
            sig.visual.mouseDist ? 1.0 : 0.0
        );
        gl.uniform1f(
            gl.getUniformLocation(program, "uVisualEnableInactivity"),
            sig.visual.inactivity ? 1.0 : 0.0
        );

        const positionLocation = gl.getAttribLocation(program, "position");
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.enableVertexAttribArray(positionLocation);
        gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);

        gl.clearColor(0, 0, 0, 1);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }

    /**
     * Create a pattern card DOM element with canvas, info, action buttons, and event binding.
     * @param {Object} options
     * @param {Object} options.pattern - { id, shader, nodes, connections, clicks }
     * @param {function(number)} options.onShare - (id) => {}
     * @param {function(number, HTMLElement)} options.onNetwork - (id, card) => {}
     * @param {function(number, HTMLButtonElement)} options.onSave - (id, buttonEl) => {}
     * @param {function(number, HTMLElement)} options.onClick - (id, card) => {}
     * @param {function(number, HTMLElement)} options.onUnclick - (id, card) => {}
     * @param {function(number)} [options.onMouseEnter] - (id) => {}
     * @param {function(number)} [options.onMouseLeave] - (id) => {}
     * @param {function(number)} [options.onFullscreen] - (id) => {} open pattern in fullscreen modal
     * @returns {{ card: HTMLElement, canvas: HTMLCanvasElement|null, patternData: Object|null }}
     */
    function createPatternCard(options) {
        const pattern = options.pattern;
        const id = pattern.id;
        const clicks = pattern.clicks !== undefined ? pattern.clicks : 0;
        const card = document.createElement("div");
        card.className = "pattern-card";
        card.dataset.id = id;

        const canvas = document.createElement("canvas");
        canvas.className = "pattern-canvas";
        canvas.width = PATTERN_CANVAS_SIZE;
        canvas.height = PATTERN_CANVAS_SIZE;

        const info = document.createElement("div");
        info.className = "pattern-info";
        info.innerHTML =
            '<div class="pattern-meta">ID: ' +
            id +
            " | Nodes: " +
            pattern.nodes +
            " | Connections: " +
            pattern.connections +
            "</div>" +
            '<div class="click-count' +
            (clicks === 0 ? " zero" : "") +
            '">' +
            clicks +
            "</div>";

        const actions = document.createElement("div");
        actions.className = "pattern-actions";

        const fullscreenBtn = document.createElement("button");
        fullscreenBtn.className = "fullscreen-btn";
        fullscreenBtn.textContent = "\u26F6";
        fullscreenBtn.setAttribute("title", "Expand to fullscreen");
        fullscreenBtn.setAttribute("aria-label", "Expand to fullscreen");
        fullscreenBtn.onclick = function (e) {
            e.stopPropagation();
            if (options.onFullscreen) options.onFullscreen(id);
        };

        const submitCommunityBtn = document.createElement("button");
        submitCommunityBtn.className = "submit-community-btn";
        submitCommunityBtn.setAttribute("title", "Share to Community");
        submitCommunityBtn.setAttribute("aria-label", "Share to Community");
        submitCommunityBtn.textContent = "\u2197";
        submitCommunityBtn.onclick = function (e) {
            e.stopPropagation();
            if (options.onShare) options.onShare(id);
        };

        const networkBtn = document.createElement("button");
        networkBtn.className = "network-btn";
        networkBtn.textContent = "\uD83E\uDDE0";
        networkBtn.setAttribute("title", "View network visualization");
        networkBtn.setAttribute("aria-label", "View network visualization");
        networkBtn.onclick = function (e) {
            e.stopPropagation();
            if (options.onNetwork) options.onNetwork(id, card);
        };

        const saveBtn = document.createElement("button");
        saveBtn.className = "save-btn";
        saveBtn.textContent = "\u2193";
        saveBtn.setAttribute("title", "Download pattern (compiling may take a moment)");
        saveBtn.setAttribute(
            "aria-label",
            "Download pattern; compiling may take a moment"
        );
        saveBtn.onclick = function (e) {
            e.stopPropagation();
            if (options.onSave) options.onSave(id, saveBtn);
        };

        actions.appendChild(fullscreenBtn);
        actions.appendChild(submitCommunityBtn);
        actions.appendChild(networkBtn);
        actions.appendChild(saveBtn);
        card.appendChild(canvas);
        card.appendChild(actions);
        card.appendChild(info);

        let patternData = setupPattern(canvas, pattern.shader);
        if (!patternData) {
            const fallback = document.createElement("div");
            fallback.className = "pattern-canvas-fallback";
            fallback.textContent = "WebGL not available";
            card.replaceChild(fallback, canvas);
            return { card: card, canvas: null, patternData: null };
        }

        if (options.onClick) {
            card.addEventListener("click", function () {
                options.onClick(id, card);
            });
        }
        if (options.onUnclick) {
            card.addEventListener("contextmenu", function (e) {
                e.preventDefault();
                options.onUnclick(id, card);
            });
        }
        if (options.onMouseEnter) {
            card.addEventListener("mouseenter", function () {
                options.onMouseEnter(id);
            });
        }
        if (options.onMouseLeave) {
            card.addEventListener("mouseleave", function () {
                options.onMouseLeave(id);
            });
        }

        return { card: card, canvas: canvas, patternData: patternData };
    }

    window.PatternRenderer = {
        setupPattern,
        renderPattern,
        createPatternCard,
    };
})();
