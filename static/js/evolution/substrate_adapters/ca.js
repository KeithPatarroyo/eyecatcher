/**
 * CA (elementary cellular automaton) substrate adapter.
 * Tunables at top for researcher experiments (animation speed, grid size).
 */
(function () {
    "use strict";

    const RENDER_PARAMS = {
        rowIntervalMs: 500,
        gridSize: 36,
    };

    function renderCa(patternData, _uniformValues, _signalState) {
        const { gl, program, positionBuffer } = patternData;
        gl.useProgram(program);

        if (patternData.caRule == null) return;

        const start = window.CA_ANIMATION_START_TIME || 0;
        const timeMs =
            typeof performance !== "undefined" ? performance.now() - start : 0;
        const step = Math.floor(timeMs / RENDER_PARAMS.rowIntervalMs);
        const uGeneration = Math.min(1.0, step / RENDER_PARAMS.gridSize);

        const locRule = gl.getUniformLocation(program, "uRule");
        const locGen = gl.getUniformLocation(program, "uGeneration");
        const locRes = gl.getUniformLocation(program, "uResolution");
        const locGrid = gl.getUniformLocation(program, "uGridSize");
        if (locRule !== null) gl.uniform1i(locRule, patternData.caRule);
        if (locGen !== null) gl.uniform1f(locGen, uGeneration);
        if (locRes !== null && patternData.canvas) {
            gl.uniform2f(locRes, patternData.canvas.width, patternData.canvas.height);
        }
        if (locGrid !== null) gl.uniform1i(locGrid, RENDER_PARAMS.gridSize);

        const positionLocation = gl.getAttribLocation(program, "position");
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.enableVertexAttribArray(positionLocation);
        gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);
        gl.clearColor(0, 0, 0, 1);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }

    function preparePatternData(patternData, pattern) {
        if (pattern.rule !== undefined && pattern.rule !== null) {
            patternData.caRule = pattern.rule;
        }
    }

    const caAdapter = {
        id: "ca",
        outputType: "grid",
        isGenomeFormat: function (obj) {
            return obj && typeof obj.rule === "number";
        },
        hasSignalControls: false,
        capabilities: {
            save: true,
            network: false,
            timeOutput: false,
            adjustWeight: false,
        },
        preparePatternData: preparePatternData,
        render: renderCa,
    };

    if (window.SubstrateAdapters) {
        window.SubstrateAdapters.register(caAdapter);
    }
})();
