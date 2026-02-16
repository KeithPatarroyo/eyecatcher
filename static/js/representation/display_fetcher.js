/**
 * Display data fetching: develop (rule) and express (image/grid) via ApiClient.
 * No state, no DOM. Use from grid load, append, community preview, genealogy thumbnails.
 * Depends on window.ApiClient.
 */
(function () {
    "use strict";

    async function developGenomes(genomes, options) {
        var ApiClient = window.ApiClient;
        if (!ApiClient) throw new Error("ApiClient not available");
        var compData = await ApiClient.develop(genomes, options && options.colorMode);
        return { population: compData.rules || [] };
    }

    async function expressGenomes(genomes, options) {
        var ApiClient = window.ApiClient;
        if (!ApiClient) throw new Error("ApiClient not available");
        var inputs = (options && options.inputs) || {};
        var expressOptions = (options && options.expressOptions) || null;
        var evalData = await ApiClient.express(genomes, inputs, expressOptions);
        var results = evalData.results || [];
        if (typeof performance !== "undefined") {
            window.CA_ANIMATION_START_TIME = performance.now();
        }
        return {
            population: results.map(function (r) {
                return {
                    id: r.id,
                    image: r.image,
                    rule: r.rule,
                    grid: r.grid,
                    nodes: r.nodes !== undefined ? r.nodes : 0,
                    connections: r.connections !== undefined ? r.connections : 0,
                    fitness: r.fitness !== undefined ? r.fitness : 0,
                };
            }),
        };
    }

    function mapExpressResultsToPopulation(results) {
        return (results || []).map(function (r) {
            return {
                id: r.id,
                image: r.image,
                rule: r.rule,
                grid: r.grid,
                nodes: r.nodes !== undefined ? r.nodes : 0,
                connections: r.connections !== undefined ? r.connections : 0,
                fitness: r.fitness !== undefined ? r.fitness : 0,
            };
        });
    }

    /**
     * Start polling /api/express on an interval for image substrates with capabilities.animate.
     * Use this to show a live view of Python express() output (e.g. prototyping).
     * @param {Object} representation - must have capabilities.animate and phenotype.substrate.type === "image"
     * @param {Array} genomes - same format as for express
     * @param {function(): Object} getSignalValues - returns current signal values { raw_time, ... }
     * @param {number} intervalMs - e.g. 200
     * @param {function(Array)} onUpdate - called with { population }-shaped array each tick
     * @returns {function()} stop - call to clear the interval
     */
    function startImageAnimate(
        representation,
        genomes,
        getSignalValues,
        intervalMs,
        onUpdate
    ) {
        var ApiClient = window.ApiClient;
        if (!ApiClient) throw new Error("ApiClient not available");
        var intervalId = null;
        function tick() {
            var inputs = typeof getSignalValues === "function" ? getSignalValues() : {};
            ApiClient.express(genomes, inputs)
                .then(function (evalData) {
                    var results = evalData.results || [];
                    onUpdate(mapExpressResultsToPopulation(results));
                })
                .catch(function () {});
        }
        tick();
        intervalId = setInterval(tick, intervalMs);
        return function stop() {
            if (intervalId !== null) {
                clearInterval(intervalId);
                intervalId = null;
            }
        };
    }

    /**
     * Fetch display data for the given representation and genomes.
     * Routes to develop (rule) or express (image/grid) based on representation.phenotype.substrate.type.
     * @param {Object} representation - { phenotype: { substrate: { type } }, ... }
     * @param {Array} genomes
     * @param {Object} [options] - e.g. { colorMode }
     * @returns {Promise<{ population: Array }>}
     */
    async function fetchDisplayData(representation, genomes, options) {
        var substrate =
            (representation &&
                representation.phenotype &&
                representation.phenotype.substrate) ||
            "image";
        var substrateType =
            typeof substrate === "string"
                ? substrate
                : (substrate && substrate.type) || "image";
        if (substrateType === "field") {
            return developGenomes(genomes, options);
        }
        var opts = options
            ? { inputs: options.inputs, expressOptions: options.expressOptions }
            : {};
        if (representation && representation.id === "nca") {
            opts.expressOptions = opts.expressOptions || {};
            if (opts.expressOptions.nca_steps === undefined) {
                opts.expressOptions.nca_steps = 8;
            }
            if (opts.expressOptions.nca_preview_grid_size === undefined) {
                opts.expressOptions.nca_preview_grid_size = 32;
            }
        }
        return expressGenomes(genomes, opts);
    }

    window.DisplayFetcher = {
        developGenomes: developGenomes,
        expressGenomes: expressGenomes,
        fetchDisplayData: fetchDisplayData,
        startImageAnimate: startImageAnimate,
    };
})();
