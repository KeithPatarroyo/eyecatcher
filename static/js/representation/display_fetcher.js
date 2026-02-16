/**
 * Display data fetching: develop (rule) and express (image/grid) via ApiClient.
 * No state, no DOM. Used by grid load/append, community preview, genealogy thumbnails.
 * Depends on window.ApiClient.
 */
const getApi = () => {
    const api = window.ApiClient;
    if (!api) throw new Error("ApiClient not available");
    return api;
};

const normalizeResult = (r) => ({
    id: r.id,
    image: r.image,
    rule: r.rule,
    grid: r.grid,
    nodes: r.nodes ?? 0,
    connections: r.connections ?? 0,
    fitness: r.fitness ?? 0,
});

const normalizePopulation = (results) => (results || []).map(normalizeResult);

const developGenomes = async (genomes, options = {}) => {
    const api = getApi();
    const compData = await api.develop(genomes, options.colorMode);
    return { population: compData.rules || [] };
};

const expressGenomes = async (genomes, options = {}) => {
    const api = getApi();
    const inputs = options.inputs || {};
    const expressOptions = options.expressOptions || null;

    const evalData = await api.express(genomes, inputs, expressOptions);
    if (typeof performance !== "undefined")
        window.CA_ANIMATION_START_TIME = performance.now();

    return { population: normalizePopulation(evalData.results) };
};

const applyNcaDefaults = (representation, options) => {
    if (representation?.id !== "nca") return options;

    const out = { ...options };
    out.expressOptions = out.expressOptions ? { ...out.expressOptions } : {};

    if (out.expressOptions.nca_steps === undefined) out.expressOptions.nca_steps = 8;
    if (out.expressOptions.nca_preview_grid_size === undefined)
        out.expressOptions.nca_preview_grid_size = 32;

    return out;
};

/**
 * Start polling /api/express on an interval for image substrates with capabilities.animate.
 * @param {Object} representation - must have capabilities.animate and phenotype.substrate.type === "image"
 * @param {Array} genomes
 * @param {function(): Object} getSignalValues - returns { raw_time, ... }
 * @param {number} intervalMs
 * @param {function(Array)} onUpdate - called with population array
 * @returns {function()} stop
 */
const startImageAnimate = (
    representation,
    genomes,
    getSignalValues,
    intervalMs,
    onUpdate
) => {
    const api = getApi();
    let intervalId = null;
    let stopped = false;

    const tick = async () => {
        if (stopped) return;
        const inputs = typeof getSignalValues === "function" ? getSignalValues() : {};
        try {
            const evalData = await api.express(genomes, inputs);
            onUpdate(normalizePopulation(evalData.results));
        } catch (_e) {
            // Intentionally quiet: animation polling should not spam console by default.
        }
    };

    tick();
    intervalId = setInterval(tick, intervalMs);

    return () => {
        stopped = true;
        if (intervalId != null) clearInterval(intervalId);
        intervalId = null;
    };
};

/**
 * Fetch display data for the given representation and genomes.
 * Routes to develop (field) or express (image/grid) based on phenotype.substrate.type.
 * @returns {Promise<{ population: Array }>}
 */
const fetchDisplayData = async (representation, genomes, options = {}) => {
    const substrate = representation?.phenotype?.substrate ?? "image";
    const substrateType =
        typeof substrate === "string" ? substrate : substrate.type || "image";

    if (substrateType === "field") return developGenomes(genomes, options);

    const expressOpts = applyNcaDefaults(representation, {
        inputs: options.inputs,
        expressOptions: options.expressOptions,
    });

    return expressGenomes(genomes, expressOpts);
};

window.DisplayFetcher = {
    developGenomes,
    expressGenomes,
    fetchDisplayData,
    startImageAnimate,
};
