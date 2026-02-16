/**
 * Pattern Renderer Module for Eyecatcher
 *
 * WebGL 2 setup, shader compilation, and pattern draw for dual-CPPN fragment shaders.
 * Used by the main grid and by community/population previews.
 *
 * Dependencies: none (signal state passed into renderPattern).
 */
(function () {
    'use strict';

    const VERTEX_SHADER_SOURCE = `#version 300 es
        in vec2 position;
        out vec2 vUV;

        void main() {
            vUV = position * 0.5 + 0.5;
            gl_Position = vec4(position, 0.0, 1.0);
        }
    `;

    function createWebGLContext(canvas) {
        const gl = canvas.getContext('webgl2');
        if (!gl) {
            console.error('WebGL 2 not supported');
            return null;
        }
        return gl;
    }

    function compileShader(gl, type, source) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);

        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            console.error('Shader compilation error:', gl.getShaderInfoLog(shader));
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
            console.error('Program linking error:', gl.getProgramInfoLog(program));
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

        const positions = new Float32Array([
            -1, -1,
            1, -1,
            -1, 1,
            1, 1,
        ]);

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
     * @param {Object} signalState - { time: {...}, visual: {...}, effects: {...} } for CPPN signal toggles
     * @param {Object} mousePos - { x, y } mouse position on canvas (0–1 each)
     */
    function renderPattern(patternData, time, mouseSpd, mouseDist, inact, signalState, mousePos) {
        const { gl, program, positionBuffer } = patternData;
        const sig = signalState || { time: {}, visual: {}, effects: {} };
        const mPos = mousePos || { x: 0.5, y: 0.5 };

        gl.useProgram(program);

        gl.uniform1f(gl.getUniformLocation(program, 'uTime'), time);
        gl.uniform1f(gl.getUniformLocation(program, 'uMouseSpeed'), mouseSpd);
        gl.uniform1f(gl.getUniformLocation(program, 'uMouseDist'), mouseDist);
        gl.uniform1f(gl.getUniformLocation(program, 'uInactivity'), inact);

        // Mouse position and perturbation strength for ripple effect
        gl.uniform1f(gl.getUniformLocation(program, 'uMouseX'), mPos.x);
        gl.uniform1f(gl.getUniformLocation(program, 'uMouseY'), mPos.y);
        gl.uniform1f(gl.getUniformLocation(program, 'uPerturbStrength'),
            sig.effects && sig.effects.mouseRipple ? 1.0 : 0.0);

        gl.uniform1f(gl.getUniformLocation(program, 'uTimeEnableRawTime'),
            sig.time.rawTime ? 1.0 : 0.0);
        gl.uniform1f(gl.getUniformLocation(program, 'uTimeEnableMouseSpeed'),
            sig.time.mouseSpeed ? 1.0 : 0.0);
        gl.uniform1f(gl.getUniformLocation(program, 'uTimeEnableMouseDist'),
            sig.time.mouseDist ? 1.0 : 0.0);
        gl.uniform1f(gl.getUniformLocation(program, 'uTimeEnableInactivity'),
            sig.time.inactivity ? 1.0 : 0.0);

        gl.uniform1f(gl.getUniformLocation(program, 'uVisualEnableTime'),
            sig.visual.time ? 1.0 : 0.0);
        gl.uniform1f(gl.getUniformLocation(program, 'uVisualEnableMouseSpeed'),
            sig.visual.mouseSpeed ? 1.0 : 0.0);
        gl.uniform1f(gl.getUniformLocation(program, 'uVisualEnableMouseDist'),
            sig.visual.mouseDist ? 1.0 : 0.0);
        gl.uniform1f(gl.getUniformLocation(program, 'uVisualEnableInactivity'),
            sig.visual.inactivity ? 1.0 : 0.0);

        const positionLocation = gl.getAttribLocation(program, 'position');
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.enableVertexAttribArray(positionLocation);
        gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);

        gl.clearColor(0, 0, 0, 1);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }

    window.PatternRenderer = {
        setupPattern,
        renderPattern,
    };
})();
