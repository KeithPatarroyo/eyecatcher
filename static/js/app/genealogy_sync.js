/**
 * GenealogySync: branch counter (localStorage), population id (sessionStorage), and
 * save-current-population-to-genealogy API call. Researchers can add custom metadata
 * to the save payload if the API supports it.
 *
 * Dependencies: Utils.safeGetItem, Utils.safeSetItem
 * Exposes: GenealogySync.getGenealogyBranchCounter, GenealogySync.setGenealogyBranchCounter,
 *   GenealogySync.syncCurrentPopulationIdToStorage, GenealogySync.getStoredPopulationId,
 *   GenealogySync.saveCurrentPopulationToGenealogy
 */
(function () {
    "use strict";

    var BRANCH_COUNTER_KEY = "genealogy_branch_counter";
    var POPULATION_ID_KEY = "current_population_id";

    function getStorage() {
        return typeof localStorage !== "undefined" ? localStorage : null;
    }

    function getSessionStorage() {
        return typeof sessionStorage !== "undefined" ? sessionStorage : null;
    }

    function getGenealogyBranchCounter() {
        var v = Utils.safeGetItem(getStorage(), BRANCH_COUNTER_KEY, "1");
        return parseInt(v, 10) || 1;
    }

    function setGenealogyBranchCounter(n) {
        Utils.safeSetItem(getStorage(), BRANCH_COUNTER_KEY, String(n));
    }

    function syncCurrentPopulationIdToStorage(populationId) {
        var session = getSessionStorage();
        if (!session) return;
        if (populationId != null) {
            Utils.safeSetItem(session, POPULATION_ID_KEY, String(populationId));
        } else {
            try {
                session.removeItem(POPULATION_ID_KEY);
            } catch (_e) {
                /* ignore */
            }
        }
    }

    function getStoredPopulationId() {
        var session = getSessionStorage();
        if (!session) return null;
        var v = Utils.safeGetItem(session, POPULATION_ID_KEY, null);
        if (v === null || v === "") return null;
        var n = parseInt(v, 10);
        return isNaN(n) ? null : n;
    }

    /**
     * Save current population to genealogy API. Returns Promise that resolves with
     * { population_id } or rejects on error.
     * @param {string} apiUrl - base API URL
     * @param {Array} genomes - genome JSONs
     * @param {number} generationNum
     * @param {string} branchName
     * @param {number|null} parentId - parent population id (null for gen 0)
     * @param {Array<number>} fitnessData - parallel to genomes
     * @param {function} apiFetch - (url, options, errorMsg) => Promise
     * @param {string} [substrateId] - current substrate id for metadata
     */
    function saveCurrentPopulationToGenealogy(
        apiUrl,
        genomes,
        generationNum,
        branchName,
        parentId,
        fitnessData,
        apiFetch,
        substrateId
    ) {
        var url = apiUrl + "/genealogy/save-population";
        var body = {
            genomes: genomes,
            parent_id: parentId,
            generation_num: generationNum,
            branch_name: branchName,
            description:
                generationNum === 0
                    ? "Random initial population"
                    : "Generation " + generationNum,
            user_id: "user",
            fitness_data: fitnessData || [],
        };
        if (substrateId != null) body.substrate_id = substrateId;
        return apiFetch(
            url,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            },
            "Save failed"
        );
    }

    window.GenealogySync = {
        getGenealogyBranchCounter: getGenealogyBranchCounter,
        setGenealogyBranchCounter: setGenealogyBranchCounter,
        syncCurrentPopulationIdToStorage: syncCurrentPopulationIdToStorage,
        getStoredPopulationId: getStoredPopulationId,
        saveCurrentPopulationToGenealogy: saveCurrentPopulationToGenealogy,
    };
})();
