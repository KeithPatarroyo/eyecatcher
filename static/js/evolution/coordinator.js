// coordinator.js (replace whole file)
(() => {
    "use strict";

    const clampInt = (value, min, max, fallback) => {
        const n = Number.parseInt(value, 10);
        const v = Number.isFinite(n) ? n : fallback;
        return Math.max(min, Math.min(max, v));
    };

    const getPopLimits = () => {
        const cfg = window.EvolutionConfig ?? {};
        return {
            min: cfg.MIN_POPULATION_SIZE ?? 2,
            max: cfg.MAX_POPULATION_SIZE ?? 50,
            def: cfg.DEFAULT_POPULATION_SIZE ?? 12,
        };
    };

    class EvolutionCoordinator {
        _IDS = {};
        _showLoading = () => {};
        _updateStats = () => {};

        init({ IDS = {}, showLoading = () => {}, updateStats = () => {} } = {}) {
            this._IDS = IDS;
            this._showLoading = showLoading;
            this._updateStats = updateStats;
        }

        _btn(disabled) {
            const id = this._IDS?.evolveBtn;
            const el = id ? document.getElementById(id) : null;
            if (!el) return;

            el.classList.toggle("disabled", disabled);
            el.setAttribute("aria-disabled", disabled ? "true" : "false");
        }

        _populationSize() {
            const { min, max, def } = getPopLimits();
            const id = this._IDS?.populationSizeInput;
            const el = id ? document.getElementById(id) : null;
            return clampInt(el?.value, min, max, def);
        }

        _fail(err) {
            console.error("Error evolving:", err);
            window.Toast?.error?.(`Evolve failed: ${err?.message ?? String(err)}`);

            this._showLoading(false);
            window.PopulationState?.dispatch?.({ type: "SET_LOADING", payload: false });
            this._btn(false);
            this._updateStats();
        }

        async evolve() {
            const evolveEl = this._IDS?.evolveBtn
                ? document.getElementById(this._IDS.evolveBtn)
                : null;

            if (evolveEl?.classList.contains("disabled")) return;

            this._btn(true);
            this._showLoading(true);
            window.PopulationState?.dispatch?.({ type: "SET_LOADING", payload: true });

            try {
                const organisms = window.PopulationState?.organisms ?? [];
                if (!organisms.length) {
                    throw new Error(
                        "No population loaded. Start with New random population or Load population."
                    );
                }

                const parents = organisms
                    .filter((o) => (o?.fitness ?? 0) > 0 && o?.genome)
                    .map((o) => ({ genome: o.genome, fitness: o.fitness ?? 0 }));

                if (!parents.length) {
                    throw new Error(
                        "Select at least one pattern (click on it) before evolving."
                    );
                }

                const populationSize = this._populationSize();
                const newGenerationNum =
                    (window.PopulationState?.generationNum ?? 0) + 1;

                const opts = {
                    parentPopulationId: window.PopulationState?.populationId,
                    generationNum: newGenerationNum,
                    branchName: window.PopulationState?.branchName || "main",
                };

                const data = await window.ApiClient.evolve(
                    parents,
                    populationSize,
                    opts
                );
                if (!data?.children) throw new Error("No children in evolve response");

                if (data.population_id != null) {
                    window.PopulationState?.dispatch?.({
                        type: "SET_EVOLVE_RESULT",
                        payload: { populationId: data.population_id },
                    });
                    window.GenealogySync?.syncCurrentPopulationIdToStorage?.(
                        data.population_id
                    );
                }

                window.PopulationLoader.loadPopulation(
                    data.children,
                    newGenerationNum,
                    data.representation_id,
                    { saveToGenealogy: false }
                );
            } catch (err) {
                this._fail(err);
            }
        }
    }

    window.EvolutionCoordinator = new EvolutionCoordinator();
})();
