/**
 * Display data fetching: develop (shader) and express (image/grid) via ApiClient.
 * No state, no DOM. Use from grid load, append, community preview, genealogy thumbnails.
 * Depends on window.ApiClient.
 */
(function () {
    "use strict";

    async function developGenomes(genomes, options) {
        var ApiClient = window.ApiClient;
        if (!ApiClient) throw new Error("ApiClient not available");
        var compData = await ApiClient.develop(genomes, options && options.colorMode);
        return { population: compData.shaders || [] };
    }

    async function expressGenomes(genomes, _options) {
        var ApiClient = window.ApiClient;
        if (!ApiClient) throw new Error("ApiClient not available");
        var evalData = await ApiClient.express(genomes);
        var results = evalData.results || [];
        if (typeof performance !== "undefined") {
            window.CA_ANIMATION_START_TIME = performance.now();
        }
        return {
            population: results.map(function (r) {
                return {
                    id: r.id,
                    image: r.image,
                    shader: r.shader,
                    grid: r.grid,
                    nodes: r.nodes !== undefined ? r.nodes : 0,
                    connections: r.connections !== undefined ? r.connections : 0,
                    fitness: r.fitness !== undefined ? r.fitness : 0,
                };
            }),
        };
    }

    /**
     * Fetch display data for the given representation and genomes.
     * Routes to develop (shader) or express (image/grid) based on representation.phenotype.substrate.
     * @param {Object} representation - { phenotype: { substrate }, ... }
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
        if (substrate === "shader") {
            return developGenomes(genomes, options);
        }
        return expressGenomes(genomes, options);
    }

    window.DisplayFetcher = {
        developGenomes: developGenomes,
        expressGenomes: expressGenomes,
        fetchDisplayData: fetchDisplayData,
    };
})();
