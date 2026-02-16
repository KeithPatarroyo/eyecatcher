/**
 * FieldSubstrate: phenotype expressed on a continuous field (fullscreen quad).
 * Uses WebGLUtils for WebGL setup. Toggleable signals come from EvolutionConfig.
 */
import WebGLUtils from "./webgl_utils.js";

const Substrate = window.Substrate;

const getToggleableSignals = () => {
    const cfg = window.getConfig?.() ?? window.EvolutionConfig;
    return (
        (cfg &&
            cfg.getToggleableSignalsForCurrentRep &&
            cfg.getToggleableSignalsForCurrentRep()) ??
        null
    );
};

const bindFullscreenQuad = (gl, program, positionBuffer, cachedAttrLoc) => {
    const loc =
        typeof cachedAttrLoc === "number"
            ? cachedAttrLoc
            : gl.getAttribLocation(program, "position");

    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    return loc;
};

const computeToggleCacheKey = (list) => {
    if (!Array.isArray(list) || list.length === 0) return "";
    // Key includes id + uniform so changes in either invalidate the cache.
    return list.map((s) => `${s.id}:${s.uniform || ""}`).join("|");
};

const ensureUniformCache = (state, list) => {
    const key = computeToggleCacheKey(list);
    if (state._toggleCacheKey === key) return;

    const gl = state.gl;
    const program = state.program;

    // Cache uniform locations once; render() becomes simple.
    const base = Object.create(null); // uniformName -> location
    const enables = Object.create(null); // signalId -> location (uEnable_<id>)

    if (Array.isArray(list)) {
        for (const s of list) {
            if (s?.uniform && base[s.uniform] === undefined) {
                base[s.uniform] = gl.getUniformLocation(program, s.uniform);
            }
        }
        for (const s of list) {
            const name = `uEnable_${s.id}`;
            enables[s.id] = gl.getUniformLocation(program, name);
        }
    }

    state._toggleCacheKey = key;
    state._baseUniformLocs = base;
    state._enableUniformLocs = enables;
};

class FieldSubstrate extends Substrate {
    createDisplayElement(_phenotype, patternPayload) {
        const rule = patternPayload?.rule;
        if (!rule) return { element: this._createFallback("No rule"), state: null };

        const canvas = this._createCanvas(256, 256);
        const wu = WebGLUtils;

        if (!wu?.setupPattern) {
            return {
                element: this._createFallback("WebGLUtils not available"),
                state: null,
            };
        }

        const state = wu.setupPattern(canvas, rule);
        if (state?.error) {
            return {
                element: this._createFallback(state.error || "Rule error"),
                state: null,
            };
        }

        // Small render-time caches
        state._toggleCacheKey = null;
        state._baseUniformLocs = Object.create(null);
        state._enableUniformLocs = Object.create(null);
        state._positionAttrLoc = null;

        return { element: canvas, state };
    }

    render(state, params, signalState) {
        if (!state?.gl || !state.program) return;

        const gl = state.gl;
        const program = state.program;
        // params is keyed by signal id (raw_time, mouse_x, ...); uniforms use names (u_time, u_mouse_x).
        const valuesById = params || {};
        const toggles = signalState || {};

        gl.useProgram(program);

        const list = getToggleableSignals();
        ensureUniformCache(state, list);

        // Build uniform name -> value from signal list (each signal has id + uniform).
        const valueByUniform = Object.create(null);
        if (Array.isArray(list)) {
            for (const s of list) {
                if (s?.uniform) valueByUniform[s.uniform] = valuesById[s.id] ?? 0;
            }
        }

        // Set base uniforms (values for each configured uniform).
        const baseLocs = state._baseUniformLocs;
        for (const uniformName in baseLocs) {
            const loc = baseLocs[uniformName];
            if (loc !== null) {
                const v = valueByUniform[uniformName] ?? valuesById[uniformName] ?? 0;
                gl.uniform1f(loc, v);
            }
        }

        // Set enable flags (uEnable_<id>) from signalState.
        const enableLocs = state._enableUniformLocs;
        for (const signalId in enableLocs) {
            const loc = enableLocs[signalId];
            if (loc !== null) gl.uniform1f(loc, toggles[signalId] ? 1.0 : 0.0);
        }

        state._positionAttrLoc = bindFullscreenQuad(
            gl,
            program,
            state.positionBuffer,
            state._positionAttrLoc
        );

        gl.clearColor(0, 0, 0, 1);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }
}

window.FieldSubstrate = FieldSubstrate;
