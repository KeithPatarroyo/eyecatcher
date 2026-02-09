/**
 * API client for Eyecatcher backend. Raw fetch calls; no UI.
 * Exposes: ApiClient.init(apiUrl), ApiClient.compile(genomes), ApiClient.breed(parents, populationSize),
 *   ApiClient.save(id, genome), ApiClient.random(size)
 */
(function () {
    "use strict";

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
        const r = await fetch(_apiUrl + "/compile", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const data = await r.json().catch(function () {
            return {};
        });
        if (!r.ok) {
            const err = new Error(data.error || "Compile failed");
            err.status = r.status;
            err.data = data;
            throw err;
        }
        return data;
    }

    /**
     * Breed next generation. Returns { children, population_id? } or throws.
     * When genealogy is provided, the backend auto-saves to the genealogy tree; do not call save-population after breeding.
     * @param {Array} parents - Array of { genome, clicks }
     * @param {number} populationSize - Desired population size
     * @param {Object} [genealogy] - Optional { parentPopulationId, generationNum, branchName } for genealogy tree
     */
    async function breed(parents, populationSize, genealogy) {
        const body = { parents: parents, population_size: populationSize };
        if (genealogy) {
            if (genealogy.parentPopulationId != null)
                body.parent_population_id = genealogy.parentPopulationId;
            if (genealogy.generationNum != null)
                body.generation_num = genealogy.generationNum;
            if (genealogy.branchName) body.branch_name = genealogy.branchName;
        }
        const r = await fetch(_apiUrl + "/breed", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const data = await r.json().catch(function () {
            return {};
        });
        if (!r.ok || data.error) {
            const err = new Error(
                data.error || "Breed failed (status " + r.status + ")"
            );
            err.status = r.status;
            err.data = data;
            throw err;
        }
        if (!Array.isArray(data.children)) {
            throw new Error("Breed failed: no children in response");
        }
        return data;
    }

    /**
     * Save a single pattern (compile + zip). Returns { downloads } or throws.
     * @param {number} id - Pattern id
     * @param {Object} genome - Genome object
     */
    async function save(id, genome) {
        const r = await fetch(_apiUrl + "/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: id, genome: genome }),
        });
        const data = await r.json().catch(function () {
            return {};
        });
        if (data.error) {
            const err = new Error(data.error);
            err.data = data;
            throw err;
        }
        return data;
    }

    /**
     * Get a new random population. Returns { genomes } or throws.
     * @param {number} size - Population size
     */
    async function random(size) {
        const r = await fetch(_apiUrl + "/random", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ size: size }),
        });
        const data = await r.json().catch(function () {
            return {};
        });
        if (!r.ok) {
            const err = new Error(data.error || "Failed to create random population");
            err.status = r.status;
            err.data = data;
            throw err;
        }
        return data;
    }

    window.ApiClient = {
        init: init,
        compile: compile,
        breed: breed,
        save: save,
        random: random,
    };
})();
