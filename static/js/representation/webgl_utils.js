/**
 * WebGL 2 helpers: context, shader compilation, fullscreen quad setup, and FBOs.
 * Used by shader/grid substrates and by fullscreen/thumbnail render paths.
 */
(() => {
    "use strict";

    const VERTEX_SHADER_SOURCE = `#version 300 es
  in vec2 position;
  out vec2 vUV;
  void main() {
    vUV = position * 0.5 + 0.5;
    gl_Position = vec4(position, 0.0, 1.0);
  }
  `;

    const QUAD_POSITIONS = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);
    const quadBufferByGL = new WeakMap();

    const createWebGLContext = (canvas) => {
        const gl = canvas.getContext("webgl2");
        if (!gl) {
            console.error("WebGL 2 not supported");
            return null;
        }
        return gl;
    };

    const compileShader = (gl, type, source) => {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);

        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            const log = gl.getShaderInfoLog(shader) || "Unknown shader compile error";
            console.error("Shader compilation error:", log);
            gl.deleteShader(shader);
            return { error: log };
        }
        return shader;
    };

    const createProgram = (gl, vertexSource, fragmentSource) => {
        const vs = compileShader(gl, gl.VERTEX_SHADER, vertexSource);
        if (vs?.error) return { error: vs.error };

        const fs = compileShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
        if (fs?.error) return { error: fs.error };

        const program = gl.createProgram();
        gl.attachShader(program, vs);
        gl.attachShader(program, fs);
        gl.linkProgram(program);

        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
            const log = gl.getProgramInfoLog(program) || "Program link failed";
            console.error("Program linking error:", log);
            gl.deleteProgram(program);
            return { error: log };
        }

        // Shaders can be deleted after linking; the program keeps them internally.
        gl.deleteShader(vs);
        gl.deleteShader(fs);

        return program;
    };

    const getOrCreateQuadBuffer = (gl) => {
        const cached = quadBufferByGL.get(gl);
        if (cached) return cached;

        const buffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.bufferData(gl.ARRAY_BUFFER, QUAD_POSITIONS, gl.STATIC_DRAW);

        quadBufferByGL.set(gl, buffer);
        return buffer;
    };

    /**
     * Create WebGL program and buffer for a fullscreen quad (pattern canvas).
     * @param {HTMLCanvasElement} canvas
     * @param {string} shaderCode - Fragment shader source (GLSL)
     * @returns {{ gl, program, positionBuffer, canvas } | { error: string }}
     */
    const setupPattern = (canvas, shaderCode) => {
        const gl = createWebGLContext(canvas);
        if (!gl) return { error: "WebGL 2 not supported" };

        const program = createProgram(gl, VERTEX_SHADER_SOURCE, shaderCode);
        if (program?.error) return { error: program.error };

        const positionBuffer = getOrCreateQuadBuffer(gl);
        return { gl, program, positionBuffer, canvas };
    };

    // ---- Shared grid context (one WebGL context for many 2D canvases) ----
    let sharedGridContext = null;

    /**
     * Single shared WebGL2 context for all grid organism cards. Avoids per-card context limit.
     * Each card uses a 2D canvas; we copy rendered frames from this shared context.
     * @returns {{ gl: WebGL2RenderingContext, canvas: HTMLCanvasElement } | null}
     */
    const getSharedGridContext = () => {
        if (sharedGridContext?.gl) {
            const lost =
                typeof sharedGridContext.gl.isContextLost === "function"
                    ? sharedGridContext.gl.isContextLost()
                    : false;
            if (!lost) return sharedGridContext;
            sharedGridContext = null;
            return null;
        }

        const canvas = document.createElement("canvas");
        canvas.width = 256;
        canvas.height = 256;

        const gl = createWebGLContext(canvas);
        if (!gl) return null;

        sharedGridContext = { gl, canvas };
        return sharedGridContext;
    };

    /**
     * Compile shader in an existing GL context (e.g. shared grid context).
     * @param {WebGL2RenderingContext} gl
     * @param {string} shaderCode - Fragment shader source (GLSL)
     * @returns {{ program, positionBuffer } | { error: string }}
     */
    const setupPatternWithSharedGL = (gl, shaderCode) => {
        const program = createProgram(gl, VERTEX_SHADER_SOURCE, shaderCode);
        if (program?.error) return { error: program.error };

        const positionBuffer = getOrCreateQuadBuffer(gl);
        return { program, positionBuffer };
    };

    /**
     * Create a framebuffer object with an attached RGBA texture.
     * @param {WebGL2RenderingContext} gl
     * @param {number} width
     * @param {number} height
     * @returns {{ fbo: WebGLFramebuffer, texture: WebGLTexture, width: number, height: number }}
     */
    const createFBO = (gl, width, height) => {
        const texture = gl.createTexture();
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

        const fbo = gl.createFramebuffer();
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

        return { fbo, texture, width, height };
    };

    const swapFBOs = (a, b) => ({ read: b, write: a });

    const destroyFBO = (gl, fboObj) => {
        if (!gl || !fboObj) return;
        if (fboObj.fbo) gl.deleteFramebuffer(fboObj.fbo);
        if (fboObj.texture) gl.deleteTexture(fboObj.texture);
    };

    window.WebGLUtils = {
        VERTEX_SHADER_SOURCE,
        createWebGLContext,
        createProgram,
        setupPattern,
        getSharedGridContext,
        setupPatternWithSharedGL,
        createFBO,
        swapFBOs,
        destroyFBO,
    };
})();
