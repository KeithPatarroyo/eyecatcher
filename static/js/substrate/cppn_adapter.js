/**
 * Shared CPPN adapter: render logic for dual_cppn and single_cppn (config-driven).
 * No per-substrate render code; uses EvolutionConfig.SIGNAL_TOGGLES for uniforms and enable flags.
 * Exposes: createCppnAdapter(spec) for use by substrate_adapters/index.js
 */
(function () {
    "use strict";

    /**
     * Build uniform-name-keyed values from signal-id-keyed values using EvolutionConfig.SIGNAL_TOGGLES.
     * @param {Object} signalValues - Keys: signal ids (raw_time, mouse_speed, mouse_dist, activity, ...)
     * @param {Object} [_context] - Optional RenderContext (ignored by CPPN adapter)
     * @returns {Object} Keys: uniform names (u_raw_time, u_mouse_speed, ...)
     */
    function buildUniforms(signalValues, _context) {
        const out = {};
        const config = window.EvolutionConfig;
        const toggles = config && config.SIGNAL_TOGGLES;
        if (!toggles || !signalValues) return out;
        (config.NETWORK_TYPES || ["time", "visual"]).forEach(function (networkType) {
            const inputs =
                toggles[networkType] && toggles[networkType].toggleableInputs;
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
     * Draw one frame for a CPPN shader: set uniforms from uniformValues and signalState, then draw.
     * @param {Object} patternData - { gl, program, positionBuffer, canvas? }
     * @param {Object} uniformValues - Keys: uniform names (u_raw_time, u_mouse_speed, ...)
     * @param {Object} signalState - { time: { id: bool }, visual: { id: bool } }
     */
    function renderCppn(patternData, uniformValues, signalState) {
        const { gl, program, positionBuffer } = patternData;
        gl.useProgram(program);

        const sig = signalState || { time: {}, visual: {} };
        const config = window.EvolutionConfig;
        const toggles = config && config.SIGNAL_TOGGLES;
        const values = uniformValues || {};

        const baseUniforms = new Set();
        if (toggles) {
            (window.EvolutionConfig.NETWORK_TYPES || ["time", "visual"]).forEach(
                function (networkType) {
                    const inputs =
                        toggles[networkType] && toggles[networkType].toggleableInputs;
                    if (!inputs) return;
                    inputs.forEach(function (s) {
                        if (s.uniform && !baseUniforms.has(s.uniform)) {
                            const loc = gl.getUniformLocation(program, s.uniform);
                            if (loc !== null) {
                                const val =
                                    values[s.uniform] !== undefined
                                        ? values[s.uniform]
                                        : 0;
                                gl.uniform1f(loc, val);
                            }
                            baseUniforms.add(s.uniform);
                        }
                    });
                }
            );
        }

        (config && config.NETWORK_TYPES
            ? config.NETWORK_TYPES
            : ["time", "visual"]
        ).forEach(function (networkType) {
            const inputs =
                config &&
                config.SIGNAL_TOGGLES &&
                config.SIGNAL_TOGGLES[networkType] &&
                config.SIGNAL_TOGGLES[networkType].toggleableInputs;
            if (!inputs) return;
            const prefix =
                "u" +
                networkType.charAt(0).toUpperCase() +
                networkType.slice(1) +
                "Enable_";
            inputs.forEach(function (s) {
                const uniformName = prefix + s.id;
                const loc = gl.getUniformLocation(program, uniformName);
                if (loc !== null) {
                    gl.uniform1f(
                        loc,
                        sig[networkType] && sig[networkType][s.id] ? 1.0 : 0.0
                    );
                }
            });
        });

        const positionLocation = gl.getAttribLocation(program, "position");
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.enableVertexAttribArray(positionLocation);
        gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);

        gl.clearColor(0, 0, 0, 1);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }

    /**
     * Create a config-driven CPPN adapter (dual_cppn or single_cppn).
     * @param {Object} spec - { id, outputType, isGenomeFormat, hasSignalControls? }
     * @returns {Object} adapter with id, outputType, isGenomeFormat, hasSignalControls, render, getMetaLabel
     */
    function createCppnAdapter(spec) {
        return {
            id: spec.id,
            outputType: spec.outputType || "shader",
            isGenomeFormat: spec.isGenomeFormat,
            hasSignalControls: spec.hasSignalControls !== false,
            render: renderCppn,
            buildUniforms: buildUniforms,
            getMetaLabel: function (pattern) {
                var n = pattern && (pattern.nodes !== undefined ? pattern.nodes : 0);
                var c =
                    pattern &&
                    (pattern.connections !== undefined ? pattern.connections : 0);
                return "Nodes: " + n + " | Connections: " + c;
            },
        };
    }

    window.createCppnAdapter = createCppnAdapter;
})();
