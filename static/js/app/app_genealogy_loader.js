/**
 * Genealogy load from localStorage and population restore.
 * Reads genealogy_load key, then either restores from genomes or starts new random population.
 * Depends: Utils.safeGetItem, SubstrateAdapters.safeResolve,
 * GridRenderer.loadFromStatelessGenomes, PopulationUI.startNewRandomPopulation.
 */
(function () {
    "use strict";

    /**
     * Run once at app init. If genealogy_load in localStorage, restore that population;
     * otherwise start new random population.
     * @param {function(number|null, string)} setGenealogyState - (populationId, branchName)
     */
    function initGenealogyLoad(setGenealogyState) {
        var genealogyLoad = null;
        var raw = window.Utils.safeGetItem(localStorage, "genealogy_load", null);
        if (raw) {
            try {
                genealogyLoad = JSON.parse(raw);
                try {
                    localStorage.removeItem("genealogy_load");
                } catch (_e) {
                    /* ignore */
                }
            } catch (e) {
                console.warn("Genealogy load parse failed:", e);
            }
        }
        if (genealogyLoad && genealogyLoad.genomes && genealogyLoad.genomes.length) {
            setGenealogyState(
                genealogyLoad.population_id != null
                    ? genealogyLoad.population_id
                    : null,
                genealogyLoad.branch_name || "main"
            );
            var genNum =
                genealogyLoad.generation_num != null ? genealogyLoad.generation_num : 0;
            var SA = window.SubstrateAdapters;
            var resolved =
                SA && SA.safeResolve
                    ? SA.safeResolve({
                          substrateId: genealogyLoad.substrate_id,
                          genomes: genealogyLoad.genomes,
                      })
                    : window.__eyecatcherDefaultResolution || {
                          outputType: "shader",
                          substrateId: "dual_cppn",
                      };
            window.GridRenderer.loadFromStatelessGenomes(
                genealogyLoad.genomes,
                genNum,
                false,
                resolved.outputType,
                resolved.substrateId
            );
        } else {
            window.PopulationUI.startNewRandomPopulation();
        }
    }

    window.AppGenealogyLoader = {
        initGenealogyLoad: initGenealogyLoad,
    };
})();
