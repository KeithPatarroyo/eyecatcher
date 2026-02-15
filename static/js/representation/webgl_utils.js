/**
 * WebGL 2 helpers: context, shader compilation, fullscreen quad setup, and FBOs.
 * Used by shader/grid substrates and by fullscreen/thumbnail render paths.
 */
(function () {
    "use strict";

    var VERTEX_SHADER_SOURCE =
        "#version 300 es\n" +
        "in vec2 position;\n" +
        "out vec2 vUV;\n" +
        "void main() {\n" +
        "    vUV = position * 0.5 + 0.5;\n" +
        "    gl_Position = vec4(position, 0.0, 1.0);\n" +
        "}\n";

    function createWebGLContext(canvas) {
        var gl = canvas.getContext("webgl2");
        if (!gl) {
            console.error("WebGL 2 not supported");
            return null;
        }
        return gl;
    }

    function compileShader(gl, type, source) {
        var shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            var log = gl.getShaderInfoLog(shader);
            console.error("Shader compilation error:", log);
            gl.deleteShader(shader);
            return { error: log };
        }
        return shader;
    }

    function createProgram(gl, vertexSource, fragmentSource) {
        var vertexShader = compileShader(gl, gl.VERTEX_SHADER, vertexSource);
        if (vertexShader && vertexShader.error) return { error: vertexShader.error };
        var fragmentShader = compileShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
        if (fragmentShader && fragmentShader.error)
            return { error: fragmentShader.error };
        if (!vertexShader || !fragmentShader) return { error: "Shader compile failed" };
        var program = gl.createProgram();
        gl.attachShader(program, vertexShader);
        gl.attachShader(program, fragmentShader);
        gl.linkProgram(program);
        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
            var log = gl.getProgramInfoLog(program);
            console.error("Program linking error:", log);
            gl.deleteProgram(program);
            return { error: log || "Program link failed" };
        }
        return program;
    }

    /**
     * Create WebGL program and buffer for a fullscreen quad (pattern canvas).
     * @param {HTMLCanvasElement} canvas
     * @param {string} shaderCode - Fragment shader source (GLSL)
     * @returns {{ gl, program, positionBuffer, canvas } | { error: string } | null}
     */
    function setupPattern(canvas, shaderCode) {
        var gl = createWebGLContext(canvas);
        if (!gl) return { error: "WebGL 2 not supported" };
        var program = createProgram(gl, VERTEX_SHADER_SOURCE, shaderCode);
        if (program && program.error) return { error: program.error };
        if (!program) return { error: "Shader compile failed" };
        var positions = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);
        var positionBuffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);
        return {
            gl: gl,
            program: program,
            positionBuffer: positionBuffer,
            canvas: canvas,
        };
    }

    /**
     * Create a framebuffer object with an attached RGBA texture.
     * @param {WebGL2RenderingContext} gl
     * @param {number} width
     * @param {number} height
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

    function swapFBOs(a, b) {
        return { read: b, write: a };
    }

    function destroyFBO(gl, fboObj) {
        if (fboObj.fbo) gl.deleteFramebuffer(fboObj.fbo);
        if (fboObj.texture) gl.deleteTexture(fboObj.texture);
    }

    window.WebGLUtils = {
        VERTEX_SHADER_SOURCE: VERTEX_SHADER_SOURCE,
        createWebGLContext: createWebGLContext,
        createProgram: createProgram,
        setupPattern: setupPattern,
        createFBO: createFBO,
        swapFBOs: swapFBOs,
        destroyFBO: destroyFBO,
    };
})();
