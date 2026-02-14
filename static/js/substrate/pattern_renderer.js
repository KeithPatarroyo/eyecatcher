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
        var adapter = window.SubstrateAdapters.currentAdapter();
        if (adapter) return adapter.buildUniforms(signalValues, context);
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
        var adapter = window.SubstrateAdapters.currentAdapter();
        if (adapter) adapter.render(patternData, uniformValues, signalState);
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
        var patterns = window.PopulationState.patterns;
        return (patterns && patterns.get && patterns.get(patternId)) || null;
    }

    /**
     * Delegate to PatternCardBuilder so grid and other callers can use PatternRenderer.createPatternCard.
     * PatternCardBuilder is loaded after this module; the call happens at runtime when population is loaded.
     */
    function createPatternCard(options) {
        try {
            if (
                window.PatternCardBuilder &&
                typeof window.PatternCardBuilder.createCard === "function"
            ) {
                return window.PatternCardBuilder.createCard(options);
            }
        } catch (_e) {
            /* fallback below */
        }
        var card = document.createElement("div");
        card.className = "pattern-card";
        card.textContent = "Card unavailable";
        return { card: card, canvas: null, patternData: null };
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
    };
})();
