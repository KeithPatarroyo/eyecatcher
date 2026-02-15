/**
 * EvolutionCoordinator: one evolution cycle (parents from state -> API -> load grid).
 * Encapsulates button disable, loading state, dispatch, and grid load. No DOM except via injected IDS/callbacks.
 *
 * Dependencies: window.EvolutionConfig, window.PopulationState, window.GridRenderer, window.ApiClient, window.Toast, window.GenealogySync
 * Init with: { IDS, showLoading, updateStats }
 * Exposes: EvolutionCoordinator.init(options), EvolutionCoordinator.evolve()
 */
(function () {
    "use strict";

    function getPopulationSizeFromConfig() {
        var cfg = window.EvolutionConfig || {};
        return {
            min: cfg.MIN_POPULATION_SIZE !== undefined ? cfg.MIN_POPULATION_SIZE : 2,
            max: cfg.MAX_POPULATION_SIZE !== undefined ? cfg.MAX_POPULATION_SIZE : 50,
            default:
                cfg.DEFAULT_POPULATION_SIZE !== undefined
                    ? cfg.DEFAULT_POPULATION_SIZE
                    : 12,
        };
    }

    class EvolutionCoordinator {
        constructor() {
            this._IDS = null;
            this._showLoading = null;
            this._updateStats = null;
        }

        init(options) {
            options = options || {};
            this._IDS = options.IDS || {};
            this._showLoading = options.showLoading || function () {};
            this._updateStats = options.updateStats || function () {};
        }

        _setEvolveButtonDisabled(disabled) {
            var id = this._IDS && this._IDS.evolveBtn;
            var el = id ? document.getElementById(id) : null;
            if (!el) return;
            if (disabled) {
                el.classList.add("disabled");
                el.setAttribute("aria-disabled", "true");
            } else {
                el.classList.remove("disabled");
                el.setAttribute("aria-disabled", "false");
            }
        }

        _getPopulationSize() {
            var id = this._IDS && this._IDS.populationSizeInput;
            var el = id ? document.getElementById(id) : null;
            return parseInt(el && el.value, 10);
        }

        evolve() {
            var IDS = this._IDS;
            var evolveBtnId = IDS && IDS.evolveBtn;
            var evolveEl = evolveBtnId ? document.getElementById(evolveBtnId) : null;
            if (evolveEl && evolveEl.classList.contains("disabled")) return;

            this._setEvolveButtonDisabled(true);
            this._showLoading(true);
            window.PopulationState.dispatch({
                type: "SET_LOADING",
                payload: true,
            });

            var self = this;
            var organisms = window.PopulationState.organisms;

            if (!organisms || !organisms.length) {
                self._onError(
                    new Error(
                        "No population loaded. Start with New random population or Load population."
                    )
                );
                return;
            }

            var parents = organisms
                .filter(function (o) {
                    return (o.fitness || 0) > 0;
                })
                .map(function (o) {
                    return o.genome
                        ? { genome: o.genome, fitness: o.fitness || 0 }
                        : null;
                })
                .filter(Boolean);

            if (!parents.length) {
                self._onError(
                    new Error(
                        "Select at least one pattern (click on it) before evolving."
                    )
                );
                return;
            }

            var limits = getPopulationSizeFromConfig();
            var rawSize = self._getPopulationSize();
            var populationSize = Math.max(
                limits.min,
                Math.min(
                    limits.max,
                    typeof rawSize === "number" ? rawSize : limits.default
                )
            );

            var newGenerationNum = (window.PopulationState.generationNum || 0) + 1;
            var opts = {
                parentPopulationId: window.PopulationState.populationId,
                generationNum: newGenerationNum,
                branchName: window.PopulationState.branchName || "main",
            };

            window.ApiClient.evolve(parents, populationSize, opts)
                .then(function (data) {
                    if (!data.children) {
                        self._onError(new Error("No children in evolve response"));
                        return;
                    }
                    if (data.population_id != null) {
                        window.PopulationState.dispatch({
                            type: "SET_EVOLVE_RESULT",
                            payload: { populationId: data.population_id },
                        });
                        if (
                            window.GenealogySync &&
                            window.GenealogySync.syncCurrentPopulationIdToStorage
                        ) {
                            window.GenealogySync.syncCurrentPopulationIdToStorage(
                                data.population_id
                            );
                        }
                    }
                    window.PopulationLoader.loadPopulation(
                        data.children,
                        newGenerationNum,
                        data.representation_id,
                        { saveToGenealogy: false }
                    );
                })
                .catch(function (err) {
                    self._onError(err);
                });
        }

        _onError(err) {
            console.error("Error evolving:", err);
            if (window.Toast && window.Toast.error) {
                window.Toast.error("Evolve failed: " + (err.message || String(err)));
            }
            this._showLoading(false);
            window.PopulationState.dispatch({
                type: "SET_LOADING",
                payload: false,
            });
            this._setEvolveButtonDisabled(false);
            this._updateStats();
        }
    }

    window.EvolutionCoordinator = new EvolutionCoordinator();
})();
