/**
 * Pattern Renderer Module for Eyecatcher
 *
 * WebGL 2 setup, shader compilation, and pattern draw for fragment shaders.
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
            const log = gl.getShaderInfoLog(shader);
            console.error("Shader compilation error:", log);
            gl.deleteShader(shader);
            return { error: log };
        }

        return shader;
    }

    function createProgram(gl, vertexSource, fragmentSource) {
        const vertexShader = compileShader(gl, gl.VERTEX_SHADER, vertexSource);
        if (vertexShader && vertexShader.error) return { error: vertexShader.error };
        const fragmentShader = compileShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
        if (fragmentShader && fragmentShader.error)
            return { error: fragmentShader.error };

        if (!vertexShader || !fragmentShader) return { error: "Shader compile failed" };

        const program = gl.createProgram();
        gl.attachShader(program, vertexShader);
        gl.attachShader(program, fragmentShader);
        gl.linkProgram(program);

        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
            const log = gl.getProgramInfoLog(program);
            console.error("Program linking error:", log);
            gl.deleteProgram(program);
            return { error: log || "Program link failed" };
        }

        return program;
    }

    /**
     * Create WebGL program and buffer for a pattern canvas.
     * @param {HTMLCanvasElement} canvas
     * @param {string} shaderCode - Fragment shader source (GLSL)
     * @returns {{ gl, program, positionBuffer } | { error: string } | null}
     */
    function setupPattern(canvas, shaderCode) {
        const gl = createWebGLContext(canvas);
        if (!gl) return { error: "WebGL 2 not supported" };

        const program = createProgram(gl, VERTEX_SHADER_SOURCE, shaderCode);
        if (program && program.error) return { error: program.error };
        if (!program) return { error: "Shader compile failed" };

        const positions = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);

        const positionBuffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);

        return { gl, program, positionBuffer };
    }

    /**
     * Build uniform values from signal values. Delegates to adapter.buildUniforms when present (CPPN);
     * otherwise returns empty object (e.g. grid adapters do not use uniforms).
     */
    function buildUniformValues(signalValues) {
        var state =
            window.PopulationState &&
            window.PopulationState.getState &&
            window.PopulationState.getState();
        var substrateId = state ? state.substrateId : null;
        var resolved =
            window.SubstrateAdapters && window.SubstrateAdapters.resolve
                ? window.SubstrateAdapters.resolve({ substrateId: substrateId })
                : { adapter: null };
        if (resolved.adapter && typeof resolved.adapter.buildUniforms === "function") {
            return resolved.adapter.buildUniforms(signalValues);
        }
        return {};
    }

    /**
     * Get signal values from the active source (or fallback), build uniforms, and render one frame.
     * Use this from animation loop, community preview, and genealogy thumbnails to avoid duplicating the pipeline.
     * @param {Object} patternData - From setupPattern
     * @param {Object} patternRenderer - Module with buildUniformValues and renderPattern (usually PatternRenderer)
     * @param {Object} signalState - { time: {...}, visual: {...} } for CPPN signal toggles
     * @param {HTMLCanvasElement} [contextCanvas] - Optional canvas for per-pattern signal context (e.g. mouse_dist)
     */
    function renderWithSignals(
        patternData,
        patternRenderer,
        signalState,
        contextCanvas
    ) {
        const getSource = window.getSignalSource;
        const signalValues = (getSource &&
            getSource().getValues &&
            getSource().getValues(
                contextCanvas != null ? { canvas: contextCanvas } : {}
            )) || { raw_time: 0.5 };
        const uniformValues =
            patternRenderer.buildUniformValues &&
            patternRenderer.buildUniformValues(signalValues);
        const u = uniformValues || signalValues;
        if (patternRenderer.renderPattern) {
            patternRenderer.renderPattern(patternData, u, signalState);
        }
    }

    /**
     * Draw one frame of a pattern with given uniforms.
     * Uses SubstrateAdapters (substrateId then findAdapterByGenome from patternData).
     * @param {Object} patternData - From setupPattern
     * @param {Object} uniformValues - Keys match uniform names (u_raw_time, u_mouse_speed, ...); use buildUniformValues(signalValues) to build from signal ids
     * @param {Object} signalState - { time: {...}, visual: {...} } for CPPN signal toggles
     */
    function renderPattern(patternData, uniformValues, signalState) {
        var state =
            window.PopulationState &&
            window.PopulationState.getState &&
            window.PopulationState.getState();
        var substrateId = state ? state.substrateId : null;
        var SubstrateAdapters = window.SubstrateAdapters;
        var genomes =
            patternData && patternData.caRule != null
                ? [{ rule: patternData.caRule }]
                : [];
        var resolved =
            SubstrateAdapters && SubstrateAdapters.resolve
                ? SubstrateAdapters.resolve({
                      substrateId: substrateId,
                      genomes: genomes,
                  })
                : {
                      adapter:
                          SubstrateAdapters && SubstrateAdapters.getAdapter
                              ? SubstrateAdapters.getAdapter(substrateId)
                              : null,
                  };
        var adapter = resolved.adapter;
        if (adapter && typeof adapter.render === "function") {
            adapter.render(patternData, uniformValues, signalState);
        }
    }

    function createErrorFallback(errorMsg) {
        var fallback = document.createElement("div");
        fallback.className = "pattern-canvas-fallback";
        fallback.textContent = errorMsg || "WebGL not available";
        if (errorMsg && errorMsg.length > 80) {
            fallback.setAttribute("title", errorMsg);
            fallback.textContent = "Shader error (hover for details)";
        }
        return fallback;
    }

    function attachCardEvents(card, id, options) {
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
     * @param {string} [options.substrateId] - current substrate id for adapter.preparePatternData
     * @returns {{ card: HTMLElement, canvas: HTMLCanvasElement|null, patternData: Object|null }}
     */
    function createPatternCard(options) {
        const pattern = options.pattern;
        const substrateId = options.substrateId || null;
        const SubstrateAdapters = window.SubstrateAdapters;
        var resolved =
            SubstrateAdapters && SubstrateAdapters.resolve
                ? SubstrateAdapters.resolve({
                      substrateId: substrateId,
                      genomes: pattern ? [pattern] : [],
                  })
                : {
                      adapter: SubstrateAdapters
                          ? SubstrateAdapters.getAdapter(substrateId)
                          : null,
                  };
        var adapter = resolved.adapter;
        const id = pattern.id;
        const clicks = pattern.clicks !== undefined ? pattern.clicks : 0;
        const card = document.createElement("div");
        card.className = "pattern-card";
        card.dataset.id = id;

        const info = document.createElement("div");
        info.className = "pattern-info";
        const meta = document.createElement("div");
        meta.className = "pattern-meta";
        if (adapter && typeof adapter.getMetaLabel === "function") {
            meta.textContent = "ID: " + id + " | " + adapter.getMetaLabel(pattern);
        } else {
            meta.textContent =
                pattern.image != null
                    ? "ID: " + id
                    : "ID: " +
                      id +
                      " | Nodes: " +
                      (pattern.nodes ?? 0) +
                      " | Connections: " +
                      (pattern.connections ?? 0);
        }
        const clickCount = document.createElement("div");
        clickCount.className = "click-count" + (clicks === 0 ? " zero" : "");
        clickCount.textContent = String(clicks);
        info.appendChild(meta);
        info.appendChild(clickCount);

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

        var caps = adapter && adapter.capabilities;
        var showNetwork = !caps || caps.network !== false;
        var showSave = !caps || caps.save !== false;

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
        if (showNetwork) actions.appendChild(networkBtn);
        if (showSave) actions.appendChild(saveBtn);

        if (pattern.shader) {
            const canvas = document.createElement("canvas");
            canvas.className = "pattern-canvas";
            canvas.width = PATTERN_CANVAS_SIZE;
            canvas.height = PATTERN_CANVAS_SIZE;
            let patternData = setupPattern(canvas, pattern.shader);
            if (!patternData || patternData.error) {
                var fallback = createErrorFallback(
                    patternData && patternData.error ? patternData.error : null
                );
                card.appendChild(fallback);
                card.appendChild(actions);
                card.appendChild(info);
                attachCardEvents(card, id, options);
                return { card: card, canvas: null, patternData: null };
            }
            if (adapter && typeof adapter.preparePatternData === "function") {
                adapter.preparePatternData(patternData, pattern);
            }
            card.appendChild(canvas);
            card.appendChild(actions);
            card.appendChild(info);
            attachCardEvents(card, id, options);
            return { card: card, canvas: canvas, patternData: patternData };
        }

        if (pattern.image != null) {
            const img = document.createElement("img");
            img.className = "pattern-canvas pattern-image";
            img.src = pattern.image;
            img.width = PATTERN_CANVAS_SIZE;
            img.height = PATTERN_CANVAS_SIZE;
            img.alt = "Pattern " + id;
            card.appendChild(img);
            card.appendChild(actions);
            card.appendChild(info);
            attachCardEvents(card, id, options);
            return { card: card, canvas: null, patternData: null };
        }

        var fallbackEl = createErrorFallback(null);
        card.appendChild(fallbackEl);
        card.appendChild(actions);
        card.appendChild(info);
        attachCardEvents(card, id, options);
        return { card: card, canvas: null, patternData: null };
    }

    window.PatternRenderer = {
        setupPattern,
        buildUniformValues,
        renderWithSignals,
        renderPattern,
        createPatternCard,
    };
})();
