// coordinator.js (replace whole file)
(() => {
    "use strict";

    const clampInt = (value, min, max, fallback) => {
        const n = Number.parseInt(value, 10);
        const v = Number.isFinite(n) ? n : fallback;
        return Math.max(min, Math.min(max, v));
    };

    const getPopLimits = () => {
        const cfg = window.getConfig?.() ?? window.EvolutionConfig ?? {};
        return {
            min: cfg.MIN_POPULATION_SIZE ?? 2,
            max: cfg.MAX_POPULATION_SIZE ?? 50,
            def: cfg.DEFAULT_POPULATION_SIZE ?? 12,
        };
    };

    class EvolutionCoordinator {
        _ctx = null;

        init(ctx = {}) {
            this._ctx = ctx;
        }

        _populationSize() {
            const { min, max, def } = getPopLimits();
            const id = this._ctx?.ids?.populationSizeInput;
            const el = id ? document.getElementById(id) : null;
            return clampInt(el?.value, min, max, def);
        }

        async evolve() {
            const evolveEl = this._ctx?.ids?.evolveBtn
                ? document.getElementById(this._ctx.ids.evolveBtn)
                : null;

            if (evolveEl?.classList.contains("disabled")) return;

            await window.Utils?.runTask?.({
                button: evolveEl,
                setLoading: this._ctx?.showLoading,
                task: async () => {
                    this._ctx?.state?.dispatch?.({
                        type: "SET_LOADING",
                        payload: true,
                    });
                    const organisms = this._ctx?.state?.organisms ?? [];
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
                    const newGenerationNum = (this._ctx?.state?.generationNum ?? 0) + 1;

                    const genealogy = this._ctx?.state?.getState?.()?.genealogy;
                    const opts = {
                        parentPopulationId: genealogy?.populationId ?? null,
                        generationNum: newGenerationNum,
                        branchName: genealogy?.branchName || "main",
                    };

                    const data = await this._ctx?.api?.evolve?.(
                        parents,
                        populationSize,
                        opts
                    );
                    if (!data?.children)
                        throw new Error("No children in evolve response");

                    if (data.population_id != null) {
                        this._ctx?.state?.dispatch?.({
                            type: "SET_GENEALOGY",
                            payload: {
                                populationId: data.population_id,
                                branchName: genealogy?.branchName || "main",
                            },
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
                },
                onError: (err) => {
                    console.error("Error evolving:", err);
                    this._ctx?.toast?.show?.(
                        "Evolve failed",
                        err?.message ?? String(err),
                        "error"
                    );
                },
                onFinally: () => {
                    this._ctx?.state?.dispatch?.({
                        type: "SET_LOADING",
                        payload: false,
                    });
                    this._ctx?.updateStats?.();
                },
            });
        }
    }

    window.EvolutionCoordinator = new EvolutionCoordinator();
})();
