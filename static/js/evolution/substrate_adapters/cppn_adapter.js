/**
 * Shared CPPN adapter: render logic for dual_cppn and single_cppn (config-driven).
 * No per-substrate render code; uses EvolutionConfig.SIGNAL_TOGGLES for uniforms and enable flags.
 * Exposes: createCppnAdapter(spec) for use by substrate_adapters/index.js
 */
(function () {
    "use strict";

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
            ["time", "visual"].forEach(function (cppnType) {
                const inputs = toggles[cppnType] && toggles[cppnType].toggleableInputs;
                if (!inputs) return;
                inputs.forEach(function (s) {
                    if (s.uniform && !baseUniforms.has(s.uniform)) {
                        const loc = gl.getUniformLocation(program, s.uniform);
                        if (loc !== null) {
                            const val =
                                values[s.uniform] !== undefined ? values[s.uniform] : 0;
                            gl.uniform1f(loc, val);
                        }
                        baseUniforms.add(s.uniform);
                    }
                });
            });
        }

        ["time", "visual"].forEach(function (cppnType) {
            const inputs =
                config &&
                config.SIGNAL_TOGGLES &&
                config.SIGNAL_TOGGLES[cppnType] &&
                config.SIGNAL_TOGGLES[cppnType].toggleableInputs;
            if (!inputs) return;
            const prefix =
                "u" + cppnType.charAt(0).toUpperCase() + cppnType.slice(1) + "Enable_";
            inputs.forEach(function (s) {
                const uniformName = prefix + s.id;
                const loc = gl.getUniformLocation(program, uniformName);
                if (loc !== null) {
                    gl.uniform1f(loc, sig[cppnType] && sig[cppnType][s.id] ? 1.0 : 0.0);
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
     * @returns {Object} adapter with id, outputType, isGenomeFormat, hasSignalControls, render
     */
    function createCppnAdapter(spec) {
        return {
            id: spec.id,
            outputType: spec.outputType || "shader",
            isGenomeFormat: spec.isGenomeFormat,
            hasSignalControls: spec.hasSignalControls !== false,
            render: renderCppn,
        };
    }

    window.createCppnAdapter = createCppnAdapter;
})();
