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
     * Build uniform-name-keyed values from signal-id-keyed values using EvolutionConfig.SIGNAL_TOGGLES.
     * Call this in the animation loop or before renderPattern so adding signals only requires config change.
     * @param {Object} signalValues - Keys: signal ids (raw_time, mouse_speed, mouse_dist, activity)
     * @returns {Object} Keys: uniform names (u_raw_time, u_mouse_speed, ...)
     */
    function buildUniformValues(signalValues) {
        const out = {};
        const config = window.EvolutionConfig;
        const toggles = config && config.SIGNAL_TOGGLES;
        if (!toggles || !signalValues) return out;
        ["time", "visual"].forEach(function (cppnType) {
            const inputs = toggles[cppnType] && toggles[cppnType].toggleableInputs;
            if (!inputs) return;
            inputs.forEach(function (s) {
                if (s.uniform && !s.derived) {
                    out[s.uniform] =
                        signalValues[s.id] !== undefined ? signalValues[s.id] : 0;
                }
            });
        });
        return out;
    }

    /**
     * Draw one frame of a pattern with given uniforms.
     * Uses SubstrateAdapters.getAdapter(substrateId).render when available; else infers adapter from patternData (caRule -> ca, else dual_cppn).
     * @param {Object} patternData - From setupPattern
     * @param {Object} uniformValues - Keys match uniform names (u_raw_time, u_mouse_speed, ...); use buildUniformValues(signalValues) to build from signal ids
     * @param {Object} signalState - { time: {...}, visual: {...} } for CPPN signal toggles
     */
    function renderPattern(patternData, uniformValues, signalState) {
        var substrateId =
            typeof window !== "undefined" &&
            window.PopulationState &&
            window.PopulationState.getState
                ? window.PopulationState.getState().substrateId
                : null;
        var SubstrateAdapters =
            typeof window !== "undefined" && window.SubstrateAdapters;
        var adapter =
            SubstrateAdapters && SubstrateAdapters.getAdapter
                ? SubstrateAdapters.getAdapter(substrateId)
                : null;
        if (!adapter && SubstrateAdapters && SubstrateAdapters.getAdapter) {
            var inferredId = patternData.caRule != null ? "ca" : "dual_cppn";
            adapter = SubstrateAdapters.getAdapter(inferredId);
        }
        if (adapter && typeof adapter.render === "function") {
            adapter.render(patternData, uniformValues, signalState);
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
        const SubstrateAdapters =
            typeof window !== "undefined" && window.SubstrateAdapters;
        var adapter =
            SubstrateAdapters && SubstrateAdapters.getAdapter
                ? SubstrateAdapters.getAdapter(substrateId)
                : null;
        if (!adapter && SubstrateAdapters && SubstrateAdapters.findAdapterByGenome) {
            adapter = SubstrateAdapters.findAdapterByGenome(pattern);
        }
        const id = pattern.id;
        const clicks = pattern.clicks !== undefined ? pattern.clicks : 0;
        const card = document.createElement("div");
        card.className = "pattern-card";
        card.dataset.id = id;

        const info = document.createElement("div");
        info.className = "pattern-info";
        const meta = document.createElement("div");
        meta.className = "pattern-meta";
        meta.textContent =
            pattern.image != null
                ? "ID: " + id
                : "ID: " +
                  id +
                  " | Nodes: " +
                  pattern.nodes +
                  " | Connections: " +
                  pattern.connections;
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
            card.appendChild(canvas);
            card.appendChild(actions);
            card.appendChild(info);
            let patternData = setupPattern(canvas, pattern.shader);
            if (!patternData || patternData.error) {
                const fallback = document.createElement("div");
                fallback.className = "pattern-canvas-fallback";
                fallback.textContent =
                    patternData && patternData.error
                        ? patternData.error
                        : "WebGL not available";
                if (patternData && patternData.error && patternData.error.length > 80) {
                    fallback.setAttribute("title", patternData.error);
                    fallback.textContent = "Shader error (hover for details)";
                }
                card.replaceChild(fallback, canvas);
                return { card: card, canvas: null, patternData: null };
            }
            if (adapter && typeof adapter.preparePatternData === "function") {
                adapter.preparePatternData(patternData, pattern);
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
            return { card: card, canvas: null, patternData: null };
        }

        const canvas = document.createElement("canvas");
        canvas.className = "pattern-canvas";
        canvas.width = PATTERN_CANVAS_SIZE;
        canvas.height = PATTERN_CANVAS_SIZE;
        card.appendChild(canvas);
        card.appendChild(actions);
        card.appendChild(info);

        let patternData = setupPattern(canvas, pattern.shader);
        if (!patternData || patternData.error) {
            const fallback = document.createElement("div");
            fallback.className = "pattern-canvas-fallback";
            fallback.textContent =
                patternData && patternData.error
                    ? patternData.error
                    : "WebGL not available";
            if (patternData && patternData.error && patternData.error.length > 80) {
                fallback.setAttribute("title", patternData.error);
                fallback.textContent = "Shader error (hover for details)";
            }
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
        buildUniformValues,
        renderPattern,
        createPatternCard,
    };
})();
