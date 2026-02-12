/**
 * API client for Eyecatcher backend. Raw fetch calls; no UI.
 * Sets window.API_URL and window.DEFAULT_DEV_PORT. Exposes: ApiClient.init(apiUrl),
 * ApiClient.compile(genomes), ApiClient.evolve(parents, populationSize),
 * ApiClient.save(id, genome), ApiClient.randomPopulation(size)
 */
(function () {
    "use strict";

    // Fallback must match EvolutionConfig.DEFAULT_DEV_PORT
    var DEFAULT_DEV_PORT =
        (typeof window !== "undefined" &&
            window.EvolutionConfig &&
            window.EvolutionConfig.DEFAULT_DEV_PORT) ||
        5001;

    function getApiBaseUrl() {
        if (
            typeof window !== "undefined" &&
            window.location &&
            window.location.origin &&
            window.location.protocol &&
            window.location.protocol.indexOf("http") === 0
        ) {
            return window.location.origin + "/api";
        }
        return "http://localhost:" + DEFAULT_DEV_PORT + "/api";
    }

    window.DEFAULT_DEV_PORT = DEFAULT_DEV_PORT;
    window.API_URL = getApiBaseUrl();

    let _apiUrl = "";

    function init(apiUrl) {
        _apiUrl = apiUrl || "";
    }

    /**
     * Compile genomes to shaders. Returns { shaders } or throws.
     * @param {Array} genomes - Array of genome objects (with optional clicks; will be normalized to 0 for compile)
     * @param {string} [colorMode] - 'hsv' (Picbreeder-style) or 'rgb'; omitted = server default
     */
    async function compile(genomes, colorMode) {
        const payload = genomes.map(function (g) {
            const copy = Object.assign({}, g);
            copy.clicks = 0;
            return copy;
        });
        const body = { genomes: payload };
        if (colorMode === "hsv" || colorMode === "rgb") body.color_mode = colorMode;
        return apiFetch(
            _apiUrl + "/compile",
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            },
            "Compile failed"
        );
    }

    /**
     * Evolve next generation (selection, crossover, mutation). Returns { children, population_id? } or throws.
     * When genealogy is provided, the backend auto-saves to the genealogy tree; do not call save-population after evolve.
     * @param {Array} parents - Array of { genome, clicks }
     * @param {number} populationSize - Desired population size
     * @param {Object} [genealogy] - Optional { parentPopulationId, generationNum, branchName } for genealogy tree
     */
    async function evolve(parents, populationSize, genealogy) {
        const body = { parents: parents, population_size: populationSize };
        if (genealogy) {
            if (genealogy.parentPopulationId != null)
                body.parent_population_id = genealogy.parentPopulationId;
            if (genealogy.generationNum != null)
                body.generation_num = genealogy.generationNum;
            if (genealogy.branchName) body.branch_name = genealogy.branchName;
        }
        const data = await apiFetch(
            _apiUrl + "/evolve",
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            },
            "Evolve failed"
        );
        if (!Array.isArray(data.children)) {
            throw new Error("Evolve failed: no children in response");
        }
        return data;
    }

    /**
     * Save a single pattern (compile + zip). Returns { downloads } or throws.
     * @param {number} id - Pattern id
     * @param {Object} genome - Genome object
     */
    async function save(id, genome) {
        return apiFetch(
            _apiUrl + "/save",
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: id, genome: genome }),
            },
            "Save failed"
        );
    }

    /**
     * Generic fetch that parses JSON and throws on !r.ok with data.error or defaultMessage.
     * Use for any API URL (e.g. genealogy endpoints). Returns parsed JSON.
     * @param {string} url - Full URL
     * @param {RequestInit} [options] - fetch options (method, headers, body, etc.)
     * @param {string} [defaultMessage] - Error message when response has no data.error
     */
    async function apiFetch(url, options, defaultMessage) {
        const r = await fetch(url, options || {});
        const data = await r.json().catch(function () {
            return {};
        });
        if (!r.ok) {
            const err = new Error(
                data.error || defaultMessage || "Request failed (" + r.status + ")"
            );
            err.status = r.status;
            err.data = data;
            throw err;
        }
        return data;
    }

    /**
     * Fetch server config (substrate_id, output_type, population_size, max_population_size).
     * Caches result on window.ServerConfig. Use for bootstrapping EvolutionConfig.
     * @returns {Promise<Object>} Config object or rejects on failure
     */
    async function fetchConfig() {
        var base = _apiUrl || getApiBaseUrl();
        var data = await apiFetch(base + "/config", { method: "GET" }, "Config failed");
        if (typeof window !== "undefined") {
            window.ServerConfig = data;
        }
        return data;
    }

    /**
     * Get a new random population. Returns { genomes, output_type } or throws.
     * @param {number} size - Population size
     */
    async function randomPopulation(size) {
        return apiFetch(
            _apiUrl + "/random",
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ size: size }),
            },
            "Failed to create random population"
        );
    }

    /**
     * Evaluate genomes with the current substrate. Returns displayable output for the grid.
     * Returns { results: [ { id, output_type, image?|shader? } ], output_type } or throws.
     * Use when output_type is "grid" (e.g. CA) to get images; or "shader" to get shader strings.
     * @param {Array} genomes - Array of genome objects
     */
    async function evaluate(genomes) {
        return apiFetch(
            _apiUrl + "/evaluate",
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ genomes: genomes }),
            },
            "Evaluate failed"
        );
    }

    window.ApiClient = {
        init: init,
        compile: compile,
        evolve: evolve,
        save: save,
        randomPopulation: randomPopulation,
        evaluate: evaluate,
        fetchConfig: fetchConfig,
        apiFetch: apiFetch,
    };
})();
