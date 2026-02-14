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
     * @param {Object} signalValues - Signal-id-keyed values from getValues
     * @param {Object} [context] - Optional RenderContext (gridPosition, neighbors, patternId) for context-derived uniforms
     */
    function buildUniformValues(signalValues, context) {
        var state =
            window.PopulationState &&
            window.PopulationState.getState &&
            window.PopulationState.getState();
        var substrateId = state ? state.substrateId : null;
        var SA = window.SubstrateAdapters;
        var resolved =
            SA && SA.safeResolve
                ? SA.safeResolve({ substrateId: substrateId })
                : window.__eyecatcherDefaultResolution || { adapter: null };
        if (resolved.adapter && typeof resolved.adapter.buildUniforms === "function") {
            return resolved.adapter.buildUniforms(signalValues, context);
        }
        return {};
    }

    /**
     * Get signal values from the active source (or fallback), build uniforms, and render one frame.
     * Use this from animation loop, community preview, and genealogy thumbnails to avoid duplicating the pipeline.
     * @param {Object} patternData - From setupPattern
     * @param {Object} patternRenderer - Module with buildUniformValues and renderPattern (usually PatternRenderer)
     * @param {Object} signalState - Flat { signal_id: boolean } for CPPN enable toggles
     * @param {HTMLCanvasElement} [contextCanvas] - Optional canvas for per-pattern signal context (e.g. mouse_dist)
     * @param {Object} [context] - Optional RenderContext (gridPosition, neighbors, patternId) passed to getValues and buildUniformValues
     */
    function renderWithSignals(
        patternData,
        patternRenderer,
        signalState,
        contextCanvas,
        context
    ) {
        const getSource = window.getSignalSource;
        const signalContext = context
            ? { canvas: contextCanvas || (context && context.canvas), ...context }
            : contextCanvas != null
              ? { canvas: contextCanvas }
              : {};
        let signalValues =
            getSource && getSource().getValues && getSource().getValues(signalContext);
        if (!signalValues || !Object.keys(signalValues).length) {
            const ids =
                (window.EvolutionConfig && window.EvolutionConfig.SIGNAL_IDS) || [];
            signalValues = {};
            ids.forEach(function (id) {
                signalValues[id] = id === "raw_time" ? 0.5 : 0;
            });
            if (!Object.keys(signalValues).length) signalValues = { raw_time: 0.5 };
        }
        const uniformValues =
            patternRenderer.buildUniformValues &&
            patternRenderer.buildUniformValues(signalValues, context);
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
     * @param {Object} signalState - Flat { signal_id: boolean } for CPPN enable toggles
     */
    function renderPattern(patternData, uniformValues, signalState) {
        var state =
            window.PopulationState &&
            window.PopulationState.getState &&
            window.PopulationState.getState();
        var substrateId = state ? state.substrateId : null;
        var SA = window.SubstrateAdapters;
        var resolved =
            SA && SA.safeResolve
                ? SA.safeResolve({ substrateId: substrateId, genomes: [] })
                : window.__eyecatcherDefaultResolution || { adapter: null };
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
        var canvas = card.querySelector("canvas");
        var SA = window.SubstrateAdapters;
        var resolved =
            SA && SA.safeResolve
                ? SA.safeResolve({ substrateId: options.substrateId })
                : { adapter: null };
        var adapter = resolved.adapter;
        var hasCellInteraction =
            adapter && typeof adapter.onCellInteraction === "function";

        if (options.onClick) {
            card.addEventListener("click", function (e) {
                if (canvas && e.target === canvas && hasCellInteraction) {
                    _fireCellInteraction(e, canvas, options.substrateId, id, "click");
                    return;
                }
                options.onClick(id, card);
                _fireCellInteraction(e, canvas, options.substrateId, id, "click");
            });
        }
        if (options.onUnclick) {
            card.addEventListener("contextmenu", function (e) {
                e.preventDefault();
                if (canvas && e.target === canvas && hasCellInteraction) {
                    _fireCellInteraction(
                        e,
                        canvas,
                        options.substrateId,
                        id,
                        "contextmenu"
                    );
                    return;
                }
                options.onUnclick(id, card);
                _fireCellInteraction(e, canvas, options.substrateId, id, "contextmenu");
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
     * Fire onCellInteraction on the adapter if it supports it.
     * @param {MouseEvent} event
     * @param {HTMLCanvasElement|null} canvas
     * @param {string|null} substrateId
     * @param {number} patternId
     * @param {string} interactionType - "click" or "contextmenu"
     */
    function _fireCellInteraction(
        event,
        canvas,
        substrateId,
        patternId,
        interactionType
    ) {
        if (!canvas) return;
        var SA = window.SubstrateAdapters;
        var resolved =
            SA && SA.safeResolve
                ? SA.safeResolve({ substrateId: substrateId })
                : { adapter: null };
        var adapter = resolved.adapter;
        if (adapter && typeof adapter.onCellInteraction === "function") {
            var coords = getClickCoordinates(event, canvas);
            var state =
                window.PopulationState &&
                window.PopulationState.getState &&
                window.PopulationState.getState();
            var patternsMap = state ? state.patterns : null;
            var patternData = null;
            if (patternsMap) {
                patternData = patternsMap.get(patternId);
                if (
                    patternData == null &&
                    typeof patternId === "string" &&
                    /^\d+$/.test(patternId)
                ) {
                    patternData = patternsMap.get(parseInt(patternId, 10));
                }
                if (patternData == null && typeof patternId === "number") {
                    patternData = patternsMap.get(String(patternId));
                }
            }
            adapter.onCellInteraction(patternData, coords.x, coords.y, interactionType);
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
        var SA = window.SubstrateAdapters;
        var resolved =
            SA && SA.safeResolve
                ? SA.safeResolve({
                      substrateId: substrateId,
                      genomes: pattern ? [pattern] : [],
                  })
                : window.__eyecatcherDefaultResolution || { adapter: null };
        var adapter = resolved.adapter;
        const id = pattern.id;
        const clicks = pattern.clicks !== undefined ? pattern.clicks : 0;
        const hasCellInteraction =
            adapter && typeof adapter.onCellInteraction === "function";
        const card = document.createElement("div");
        card.className =
            "pattern-card" + (hasCellInteraction ? " pattern-card--interactive" : "");
        card.dataset.id = id;

        const info = document.createElement("div");
        info.className = "pattern-info";
        const meta = document.createElement("div");
        meta.className = "pattern-meta";
        if (adapter && typeof adapter.getMetaLabel === "function") {
            var idPrefix =
                typeof adapter.getMetaIdPrefix === "function"
                    ? adapter.getMetaIdPrefix()
                    : "ID: ";
            meta.textContent = idPrefix + id + " | " + adapter.getMetaLabel(pattern);
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

        if (adapter && typeof adapter.createDisplayElement === "function") {
            var result = adapter.createDisplayElement(pattern, options);
            var displayEl = result && result.element;
            if (displayEl) {
                card.appendChild(displayEl);
            } else {
                card.appendChild(
                    createErrorFallback("Display element creation failed")
                );
            }
            var patternData = result && result.patternData;
            if (
                adapter &&
                typeof adapter.preparePatternData === "function" &&
                patternData
            ) {
                adapter.preparePatternData(patternData, pattern);
            }
            card.appendChild(actions);
            card.appendChild(info);
            attachCardEvents(card, id, options);
            var isCanvas = displayEl && displayEl instanceof HTMLCanvasElement;
            return {
                card: card,
                canvas: isCanvas ? displayEl : null,
                patternData: patternData || null,
            };
        }

        /* BACKWARDS_COMPAT: legacy shader/image branches when adapter does not implement createDisplayElement. Remove once all adapters provide createDisplayElement. */
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

    // -- FBO helpers for stateful substrates (NCA, etc.) --

    /**
     * Create a framebuffer object (FBO) with an attached RGBA float texture.
     * Use for ping-pong rendering in stateful substrates like NCA.
     * @param {WebGL2RenderingContext} gl
     * @param {number} width - Texture width in pixels
     * @param {number} height - Texture height in pixels
     * @returns {{ fbo: WebGLFramebuffer, texture: WebGLTexture, width: number, height: number }}
     */
    function createFBO(gl, width, height) {
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
            null
        );
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

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

    /**
     * Swap two FBO objects (for ping-pong rendering).
     * Returns { read, write } where read was the previous write and vice versa.
     * @param {{ fbo: WebGLFramebuffer, texture: WebGLTexture }} a
     * @param {{ fbo: WebGLFramebuffer, texture: WebGLTexture }} b
     * @returns {{ read: Object, write: Object }}
     */
    function swapFBOs(a, b) {
        return { read: b, write: a };
    }

    /**
     * Destroy an FBO and its attached texture.
     * @param {WebGL2RenderingContext} gl
     * @param {{ fbo: WebGLFramebuffer, texture: WebGLTexture }} fboObj
     */
    function destroyFBO(gl, fboObj) {
        if (fboObj.fbo) gl.deleteFramebuffer(fboObj.fbo);
        if (fboObj.texture) gl.deleteTexture(fboObj.texture);
    }

    /**
     * Read pixels along one edge of an FBO and return average RGB (0-1).
     * Uses the FBO's gl context; call from adapter onBeforeRender when reading a neighbor's edge.
     * @param {WebGL2RenderingContext} gl - Context that owns the FBO
     * @param {{ fbo: WebGLFramebuffer, texture: WebGLTexture, width: number, height: number }} fboObj - From createFBO
     * @param {string} edge - "top" | "bottom" | "left" | "right"
     * @param {number} width - FBO width (use fboObj.width)
     * @param {number} height - FBO height (use fboObj.height)
     * @returns {{ r: number, g: number, b: number }} Average RGB in 0-1 range
     */
    function readEdgePixels(gl, fboObj, edge, width, height) {
        if (!fboObj || !fboObj.fbo) return { r: 0, g: 0, b: 0 };
        var w = width || fboObj.width || 1;
        var h = height || fboObj.height || 1;
        var x = 0,
            y = 0,
            readW = 1,
            readH = 1;
        if (edge === "top") {
            x = 0;
            y = h - 1;
            readW = w;
            readH = 1;
        } else if (edge === "bottom") {
            x = 0;
            y = 0;
            readW = w;
            readH = 1;
        } else if (edge === "left") {
            x = 0;
            y = 0;
            readW = 1;
            readH = h;
        } else if (edge === "right") {
            x = w - 1;
            y = 0;
            readW = 1;
            readH = h;
        } else {
            return { r: 0, g: 0, b: 0 };
        }
        var pixelCount = readW * readH;
        var pixels = new Uint8Array(pixelCount * 4);
        var prevFbo = gl.getParameter(gl.FRAMEBUFFER_BINDING);
        gl.bindFramebuffer(gl.FRAMEBUFFER, fboObj.fbo);
        gl.readPixels(x, y, readW, readH, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
        gl.bindFramebuffer(gl.FRAMEBUFFER, prevFbo);
        var r = 0,
            g = 0,
            b = 0;
        for (var i = 0; i < pixelCount; i++) {
            r += pixels[i * 4] / 255;
            g += pixels[i * 4 + 1] / 255;
            b += pixels[i * 4 + 2] / 255;
        }
        return {
            r: r / pixelCount,
            g: g / pixelCount,
            b: b / pixelCount,
        };
    }

    /**
     * Get patternData for a pattern by id (e.g. a neighbor). Used by adapters in onBeforeRender to read neighbor FBOs.
     * @param {number|string} patternId
     * @returns {Object|null} patternData from PopulationState.patterns, or null
     */
    function getNeighborPatternData(patternId) {
        var state =
            window.PopulationState &&
            window.PopulationState.getState &&
            window.PopulationState.getState();
        var patterns = state ? state.patterns : null;
        return (patterns && patterns.get && patterns.get(patternId)) || null;
    }

    // -- Click coordinate extraction --

    /**
     * Extract normalized (0-1) coordinates from a mouse/click event relative to a canvas.
     * @param {MouseEvent} event
     * @param {HTMLCanvasElement} canvas
     * @returns {{ x: number, y: number }} - Normalized coordinates (0-1 range, origin top-left)
     */
    function getClickCoordinates(event, canvas) {
        var rect = canvas.getBoundingClientRect();
        return {
            x: Math.min(1.0, Math.max(0.0, (event.clientX - rect.left) / rect.width)),
            y: Math.min(1.0, Math.max(0.0, (event.clientY - rect.top) / rect.height)),
        };
    }

    window.PatternRenderer = {
        setupPattern,
        buildUniformValues,
        renderWithSignals,
        renderPattern,
        createPatternCard,
        createFBO,
        swapFBOs,
        destroyFBO,
        readEdgePixels,
        getNeighborPatternData,
        getClickCoordinates,
    };
})();
