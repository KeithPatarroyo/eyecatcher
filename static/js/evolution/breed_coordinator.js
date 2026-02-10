/**
 * BreedCoordinator: coordinates breed API call and callbacks. No DOM; reads from getState
 * and EvolutionConfig. Researchers change selection or breed params here or in EvolutionConfig.
 *
 * Dependencies: window.EvolutionConfig (MIN/MAX/DEFAULT_POPULATION_SIZE)
 * Exposes: BreedCoordinator.breedGeneration
 */
(function () {
    "use strict";

    function getPopulationSizeFromConfig() {
        var cfg = window.EvolutionConfig || {};
        return {
            min: cfg.MIN_POPULATION_SIZE !== undefined ? cfg.MIN_POPULATION_SIZE : 2,
            max: cfg.MAX_POPULATION_SIZE !== undefined ? cfg.MAX_POPULATION_SIZE : 50,
            default: cfg.DEFAULT_POPULATION_SIZE !== undefined ? cfg.DEFAULT_POPULATION_SIZE : 12,
        };
    }

    /**
     * Run one breed cycle: compute parents from state, call apiBreed, then onSuccess or onError.
     * @param {function()} getState - returns { currentPopulation, currentGenomes, patterns, populationId, branchName, generationNum }
     * @param {function()} getPopulationSize - returns number (from toolbar input or config)
     * @param {function(parents, size, opts)} apiBreed - (parents, populationSize, { parentPopulationId, generationNum, branchName }) => Promise<{ children, population_id? }>
     * @param {function(children, newGenerationNum)} onSuccess
     * @param {function(err)} onError
     */
    function breedGeneration(getState, getPopulationSize, apiBreed, onSuccess, onError) {
        var state = getState();
        var genomes = state.currentGenomes;
        var population = state.currentPopulation;
        var patterns = state.patterns;

        if (!genomes || !genomes.length) {
            onError(new Error("No population loaded. Start with New random population or Load population."));
            return;
        }

        var parents = population
            .map(function (p, idx) {
                var pat = patterns.get(p.id);
                var clicks = pat ? pat.clicks : 0;
                var genome = genomes[idx];
                return genome ? { genome: genome, clicks: clicks } : null;
            })
            .filter(Boolean)
            .filter(function (p) {
                return p.clicks > 0;
            });

        if (!parents.length) {
            onError(new Error("Select at least one pattern (click on it) before breeding."));
            return;
        }

        var limits = getPopulationSizeFromConfig();
        var rawSize = getPopulationSize();
        var populationSize = Math.max(
            limits.min,
            Math.min(limits.max, typeof rawSize === "number" ? rawSize : limits.default)
        );

        var newGenerationNum = state.generationNum + 1;
        var opts = {
            parentPopulationId: state.populationId,
            generationNum: newGenerationNum,
            branchName: state.branchName || "main",
        };

        apiBreed(parents, populationSize, opts)
            .then(function (data) {
                if (data.children) {
                    onSuccess(data.children, newGenerationNum, data.population_id);
                } else {
                    onError(new Error("No children in breed response"));
                }
            })
            .catch(function (err) {
                onError(err);
            });
    }

    window.BreedCoordinator = {
        breedGeneration: breedGeneration,
    };
})();
