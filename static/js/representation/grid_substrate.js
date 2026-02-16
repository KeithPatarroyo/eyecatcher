/**
 * GridSubstrate: phenotype expressed on a 2D grid with FBO ping-pong.
 * Step shader, display shader, and toggle shader come from phenotype.
 * Built-in interaction "toggle": click to flip cells.
 */
const Substrate = window.Substrate;

const MAX_TOGGLES_PER_PASS = 64;
const TOGGLE_BRUSH_RADIUS = 1;

const nowMs = () =>
    typeof performance !== "undefined" && performance.now
        ? performance.now()
        : Date.now();

const clampInt = (v, min, max, fallback) => {
    const n = parseInt(v, 10);
    if (!Number.isFinite(n)) return fallback;
    return Math.max(min, Math.min(max, n));
};

// ---- Grid -> initial texture pixels ----

const gridToRgbaPixelArray = (grid) => {
    const rows = Array.isArray(grid) ? grid.length : 0;
    if (!rows) return new Uint8Array(0);
    const cols = Array.isArray(grid[0]) ? grid[0].length : 0;
    const out = new Uint8Array(rows * cols * 4);

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const alive = grid[r][c] > 0.5 || grid[r][c] === 1;
            const v = alive ? 255 : 0;
            const i = (r * cols + c) * 4;
            out[i] = v;
            out[i + 1] = v;
            out[i + 2] = v;
            out[i + 3] = 255;
        }
    }
    return out;
};

const float32ToFloat16 = (f) => {
    const f32 = new Float32Array(1);
    const u32 = new Uint32Array(f32.buffer);
    f32[0] = f;
    const x = u32[0];
    const sign = (x >> 31) & 1;
    let exp = (x >> 23) & 0xff;
    const frac = x & 0x7fffff;

    if (exp === 0xff) return (sign << 15) | 0x7c00 | (frac ? 0x200 : 0);
    if (exp === 0 && frac === 0) return sign << 15;

    exp -= 127;
    if (exp < -14) return sign << 15;

    return (sign << 15) | ((exp + 15) << 10) | (frac >> 13);
};

const gridToRgba16FPixelArray = (grid, rows, cols) => {
    const n = rows * cols * 4;
    const f32 = new Float32Array(n);

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const alive = grid[r][c] > 0.5 || grid[r][c] === 1 ? 1.0 : 0.0;
            const i = (r * cols + c) * 4;
            f32[i] = 0;
            f32[i + 1] = 0;
            f32[i + 2] = 0;
            f32[i + 3] = alive;
        }
    }

    const u16 = new Uint16Array(n);
    for (let j = 0; j < n; j++) u16[j] = float32ToFloat16(f32[j]);
    return u16;
};

// ---- WebGL helpers ----

const bindFullscreenQuad = (gl, program, positionBuffer) => {
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    const loc = gl.getAttribLocation(program, "position");
    if (loc < 0) return;
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
};

const cacheUniforms = (gl, program, names) => {
    const out = Object.create(null);
    for (const n of names) out[n] = gl.getUniformLocation(program, n);
    return out;
};

const setUniformAuto = (gl, loc, value) => {
    if (!loc) return;
    if (typeof value === "number") {
        // Default to float; callers can pass { int: x } if needed.
        gl.uniform1f(loc, value);
        return;
    }
    if (!value || typeof value !== "object") return;

    if (typeof value.int === "number") {
        gl.uniform1i(loc, value.int);
        return;
    }
    if (Array.isArray(value.vec2) && value.vec2.length === 2) {
        gl.uniform2f(loc, value.vec2[0], value.vec2[1]);
        return;
    }
    if (Array.isArray(value.vec3) && value.vec3.length === 3) {
        gl.uniform3f(loc, value.vec3[0], value.vec3[1], value.vec3[2]);
        return;
    }
    if (Array.isArray(value.vec4) && value.vec4.length === 4) {
        gl.uniform4f(loc, value.vec4[0], value.vec4[1], value.vec4[2], value.vec4[3]);
        return;
    }
    if (typeof value.bool === "boolean") {
        gl.uniform1i(loc, value.bool ? 1 : 0);
    }
};

const createFBOWithOptions = (gl, width, height, options = {}) => {
    const useFloat = options.format === "RGBA16F" && gl.RGBA16F;
    const wrap = options.wrap === "REPEAT" ? gl.REPEAT : gl.CLAMP_TO_EDGE;
    const initialPixels = options.initialPixels ?? null;

    const texture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, texture);

    if (useFloat) {
        gl.texImage2D(
            gl.TEXTURE_2D,
            0,
            gl.RGBA16F,
            width,
            height,
            0,
            gl.RGBA,
            gl.HALF_FLOAT,
            initialPixels
        );
    } else {
        gl.texImage2D(
            gl.TEXTURE_2D,
            0,
            gl.RGBA,
            width,
            height,
            0,
            gl.RGBA,
            gl.UNSIGNED_BYTE,
            initialPixels
        );
    }

    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, wrap);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, wrap);

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

const swapReadWrite = (state) => {
    const tmp = state.fboRead;
    state.fboRead = state.fboWrite;
    state.fboWrite = tmp;
};

const copySharedFramebufferTo2D = (gl, canvas2d, width, height) => {
    const pixels = new Uint8Array(width * height * 4);
    gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);

    // Flip Y for canvas2d
    const flipped = new Uint8Array(pixels.length);
    const rowBytes = width * 4;
    for (let y = 0; y < height; y++) {
        const src = (height - 1 - y) * rowBytes;
        const dst = y * rowBytes;
        flipped.set(pixels.subarray(src, src + rowBytes), dst);
    }

    const imageData = canvas2d.createImageData(width, height);
    imageData.data.set(flipped);
    canvas2d.putImageData(imageData, 0, 0);
};

const runTogglePass = (state) => {
    const toggles = state.toggleMask;
    if (!state.toggleProgram || !toggles || toggles.length === 0) return;

    const gl = state.gl;
    const n = Math.min(toggles.length, MAX_TOGGLES_PER_PASS);
    const w = state.gridSize;

    gl.useProgram(state.toggleProgram);
    bindFullscreenQuad(gl, state.toggleProgram, state.positionBuffer);

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, state.fboRead.texture);

    gl.bindFramebuffer(gl.FRAMEBUFFER, state.fboWrite.fbo);
    gl.viewport(0, 0, w, w);

    gl.uniform1i(state.toggleUniforms.u_state, 0);
    gl.uniform2f(state.toggleUniforms.u_gridSize, w, w);
    gl.uniform1f(state.toggleUniforms.u_brushRadius, TOGGLE_BRUSH_RADIUS);

    // Pack toggles as vec2 array (x,y in [0,1])
    const packed = new Float32Array(n * 2);
    for (let i = 0; i < n; i++) {
        packed[i * 2] = toggles[i].x;
        packed[i * 2 + 1] = toggles[i].y;
    }
    gl.uniform1i(state.toggleUniforms.u_toggleCount, n);
    gl.uniform2fv(state.toggleUniforms.u_toggles, packed);

    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

    swapReadWrite(state);
    toggles.splice(0, n);
};

// ---- GridSubstrate ----

class GridSubstrate extends Substrate {
    createDisplayElement(phenotype, patternPayload, _options) {
        const stepShader =
            phenotype?.behaviour?.updateRule ||
            patternPayload?.rule ||
            phenotype?.stepShader;

        if (!stepShader)
            return { element: this._createFallback("No step shader"), state: null };

        const canvas = this._createCanvas(256, 256);
        const wu = window.WebGLUtils;

        if (!wu?.setupPattern) {
            return {
                element: this._createFallback("WebGLUtils not available"),
                state: null,
            };
        }

        const shared = wu.getSharedGridContext?.();
        let state;

        if (shared && wu.setupPatternWithSharedGL) {
            const compiled = wu.setupPatternWithSharedGL(shared.gl, stepShader);
            if (compiled?.error) {
                return {
                    element: this._createFallback(compiled.error || "Shader error"),
                    state: null,
                };
            }
            state = {
                gl: shared.gl,
                program: compiled.program,
                positionBuffer: compiled.positionBuffer,
                canvas,
                useSharedContext: true,
                sharedCanvas: shared.canvas,
            };
        } else {
            state = wu.setupPattern(canvas, stepShader);
            if (state?.error) {
                return {
                    element: this._createFallback(state.error || "Shader error"),
                    state: null,
                };
            }
        }

        state.canvas = canvas;
        state.patternPayload = patternPayload || {};
        state.phenotype = phenotype || {};
        state.toggleMask = [];
        return { element: canvas, state };
    }

    setup(state, phenotype) {
        if (!state?.gl) return;

        const gl = state.gl;
        const wu = window.WebGLUtils;
        if (!wu?.createProgram) return;

        const w = clampInt(phenotype?.gridSize, 2, 4096, 64);
        const stepIntervalMs = clampInt(phenotype?.stepIntervalMs, 0, 60_000, 180);
        const texFormat = phenotype?.stateFormat || "RGBA";
        const wrap = phenotype?.wrap || "REPEAT";

        let initialPixels = null;
        const grid = state.patternPayload?.grid;

        if (
            Array.isArray(grid) &&
            grid.length === w &&
            Array.isArray(grid[0]) &&
            grid[0].length === w
        ) {
            const is2D = typeof grid[0][0] === "number";
            initialPixels =
                texFormat === "RGBA16F" && is2D
                    ? gridToRgba16FPixelArray(grid, w, w)
                    : gridToRgbaPixelArray(grid);
        }

        const fboRead = createFBOWithOptions(gl, w, w, {
            format: texFormat,
            wrap,
            initialPixels,
        });
        const fboWrite = createFBOWithOptions(gl, w, w, {
            format: texFormat,
            wrap,
        });

        const displayShaderSource =
            phenotype?.displayShader ||
            `#version 300 es
  precision highp float;
  uniform sampler2D u_state;
  in vec2 vUV;
  out vec4 fragColor;
  void main() { fragColor = vec4(texture(u_state, vUV).rgb, 1.0); }`;

        const displayProgram = wu.createProgram(
            gl,
            wu.VERTEX_SHADER_SOURCE,
            displayShaderSource
        );
        if (displayProgram?.error) {
            wu.destroyFBO?.(gl, fboRead);
            wu.destroyFBO?.(gl, fboWrite);
            return;
        }

        state.fboRead = fboRead;
        state.fboWrite = fboWrite;
        state.displayProgram = displayProgram;
        state.gridSize = w;
        state.stepIntervalMs = stepIntervalMs;
        state._lastStepTime = 0;

        // Cache uniforms once
        state.stepUniforms = cacheUniforms(gl, state.program, [
            "u_state",
            "u_texelSize",
        ]);
        state.displayUniforms = cacheUniforms(gl, state.displayProgram, ["u_state"]);

        if (state.useSharedContext && state.canvas)
            state.canvas2d = state.canvas.getContext("2d");

        const toggleShaderSource =
            phenotype?.behaviour?.interactionRule || phenotype?.toggleShader;

        if (toggleShaderSource) {
            const toggleProgram = wu.createProgram(
                gl,
                wu.VERTEX_SHADER_SOURCE,
                toggleShaderSource
            );
            if (toggleProgram && !toggleProgram.error) {
                state.toggleProgram = toggleProgram;
                state.toggleUniforms = cacheUniforms(gl, toggleProgram, [
                    "u_state",
                    "u_gridSize",
                    "u_brushRadius",
                    "u_toggleCount",
                    "u_toggles",
                ]);
            }
        }
    }

    teardown(state) {
        if (!state) return;
        const wu = window.WebGLUtils;

        if (wu && state.gl) {
            if (state.fboRead) wu.destroyFBO(state.gl, state.fboRead);
            if (state.fboWrite) wu.destroyFBO(state.gl, state.fboWrite);
        }

        if (state.program && state.gl) state.gl.deleteProgram(state.program);
        if (state.displayProgram && state.gl)
            state.gl.deleteProgram(state.displayProgram);
        if (state.toggleProgram && state.gl)
            state.gl.deleteProgram(state.toggleProgram);

        state.fboRead = null;
        state.fboWrite = null;
        state.program = null;
        state.displayProgram = null;
        state.toggleProgram = null;
    }

    render(state, params, _signalState) {
        if (!state?.gl || !state.fboRead || !state.fboWrite || !state.displayProgram)
            return;
        if (typeof state.gl.isContextLost === "function" && state.gl.isContextLost())
            return;

        const gl = state.gl;
        const w = state.gridSize;
        const stepIntervalMs = state.stepIntervalMs || 180;

        if (state.toggleMask?.length) runTogglePass(state);

        const t = nowMs();
        const shouldStep = t - (state._lastStepTime || 0) >= stepIntervalMs;

        // ---- Step pass (ping-pong) ----
        if (shouldStep && state.program) {
            gl.useProgram(state.program);
            bindFullscreenQuad(gl, state.program, state.positionBuffer);

            gl.activeTexture(gl.TEXTURE0);
            gl.bindTexture(gl.TEXTURE_2D, state.fboRead.texture);

            gl.bindFramebuffer(gl.FRAMEBUFFER, state.fboWrite.fbo);
            gl.viewport(0, 0, w, w);

            gl.uniform1i(state.stepUniforms.u_state, 0);
            gl.uniform2f(state.stepUniforms.u_texelSize, 1 / w, 1 / w);

            if (params && typeof params === "object") {
                for (const key of Object.keys(params)) {
                    if (key === "u_state" || key === "u_texelSize") continue;
                    const loc = gl.getUniformLocation(state.program, key);
                    setUniformAuto(gl, loc, params[key]);
                }
            }

            gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

            swapReadWrite(state);
            state._lastStepTime = t;
        }

        // ---- Display pass ----
        gl.useProgram(state.displayProgram);
        bindFullscreenQuad(gl, state.displayProgram, state.positionBuffer);

        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, state.fboRead.texture);

        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        gl.viewport(0, 0, state.canvas.width, state.canvas.height);

        gl.uniform1i(state.displayUniforms.u_state, 0);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

        // Shared context rendering writes into shared canvas; copy pixels to the card’s 2D canvas.
        if (state.useSharedContext && state.canvas2d) {
            copySharedFramebufferTo2D(
                gl,
                state.canvas2d,
                state.canvas.width,
                state.canvas.height
            );
        }
    }

    handleInteraction(state, x, y, _interactionType) {
        if (!state) return;
        if (!state.toggleMask) state.toggleMask = [];
        state.toggleMask.push({ x, y });
    }
}

window.GridSubstrate = GridSubstrate;
