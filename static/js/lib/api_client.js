/**
 * API client for Eyecatcher backend. Raw fetch calls; no UI.
 * Sets window.API_URL and window.DEFAULT_DEV_PORT. Exposes: ApiClient.init(apiUrl),
 * ApiClient.compile(individuals), ApiClient.evolve(parents, populationSize),
 * ApiClient.save(id, individual), ApiClient.randomPopulation(size)
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

    /** Base URL for API (so pages that never call init, e.g. genealogy, still hit /api/...). */
    function getBase() {
        return _apiUrl || getApiBaseUrl();
    }

    /**
     * Compile individuals to shaders. Returns { shaders } or throws.
     * @param {Array} individuals - Array of individual objects (with optional clicks; normalized to 0 for compile)
     * @param {string} [colorMode] - 'hsv' (Picbreeder-style) or 'rgb'; omitted = server default
     */
    async function compile(individuals, colorMode) {
        const payload = individuals.map(function (g) {
            const copy = Object.assign({}, g);
            copy.clicks = 0;
            return copy;
        });
        const body = { individuals: payload };
        if (colorMode === "hsv" || colorMode === "rgb") body.color_mode = colorMode;
        return apiFetch(
            getBase() + "/compile",
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
     * @param {Array} parents - Array of { genome, clicks } (genome sent as 'individual' to API)
     * @param {number} populationSize - Desired population size
     * @param {Object} [genealogy] - Optional { parentPopulationId, generationNum, branchName } for genealogy tree
     */
    async function evolve(parents, populationSize, genealogy) {
        const parentsPayload = (parents || []).map(function (p) {
            return {
                individual: p.genome || p,
                fitness: p.fitness != null ? p.fitness : p.clicks || 0,
            };
        });
        const body = { parents: parentsPayload, population_size: populationSize };
        if (genealogy) {
            if (genealogy.parentPopulationId != null)
                body.parent_population_id = genealogy.parentPopulationId;
            if (genealogy.generationNum != null)
                body.generation_num = genealogy.generationNum;
            if (genealogy.branchName) body.branch_name = genealogy.branchName;
        }
        const data = await apiFetch(
            getBase() + "/evolve",
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
     * @param {Object} individual - Individual object (genome + metadata)
     */
    async function save(id, individual) {
        return apiFetch(
            getBase() + "/save",
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: id, individual: individual }),
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
     * Fetch server config (substrate_id, output_type, population_size, max_population_size, crossover_probability).
     * Caches result on window.ServerConfig. Use for bootstrapping EvolutionConfig.
     * @returns {Promise<Object>} Config object or rejects on failure
     */
    async function fetchConfig() {
        var data = await apiFetch(
            getBase() + "/config",
            { method: "GET" },
            "Config failed"
        );
        if (typeof window !== "undefined") {
            window.ServerConfig = data;
        }
        return data;
    }

    /**
     * Update experiment parameters at runtime (PATCH /api/config). No server restart.
     * @param {Object} updates - { population_size?, max_population_size?, crossover_probability? }
     * @returns {Promise<Object>} Current config (same shape as fetchConfig)
     */
    async function patchConfig(updates) {
        var data = await apiFetch(
            getBase() + "/config",
            {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(updates || {}),
            },
            "Update config failed"
        );
        if (typeof window !== "undefined") {
            window.ServerConfig = data;
        }
        return data;
    }

    /**
     * Get a new random population. Returns { individuals, output_type, representation_id } or throws.
     * @param {number} size - Population size
     */
    async function randomPopulation(size) {
        return apiFetch(
            getBase() + "/random",
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ size: size }),
            },
            "Failed to create random population"
        );
    }

    /**
     * Evaluate individuals with the current representation. Returns displayable output for the grid.
     * Returns { results: [ { id, output_type, image?|shader? } ], output_type } or throws.
     * Use when output_type is "grid" (e.g. CA) to get images; or "shader" to get shader strings.
     * @param {Array} individuals - Array of individual objects
     */
    async function evaluate(individuals) {
        return apiFetch(
            getBase() + "/evaluate",
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ individuals: individuals }),
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
        patchConfig: patchConfig,
        apiFetch: apiFetch,
    };
})();
