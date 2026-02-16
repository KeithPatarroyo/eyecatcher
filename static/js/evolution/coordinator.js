import Utils from "../lib/utils.js";
import GenealogySync from "../genealogy/sync.js";
import { getConfig } from "./experiment_config.js";
import populationLoader from "../population/population_loader.js";

const clampInt = (value, min, max, fallback) => {
    const n = Number.parseInt(value, 10);
    const v = Number.isFinite(n) ? n : fallback;
    return Math.max(min, Math.min(max, v));
};

const getPopLimits = () => {
    const cfg = getConfig?.() ?? getConfig() ?? {};
    return {
        min: cfg.MIN_POPULATION_SIZE ?? 2,
        max: cfg.MAX_POPULATION_SIZE ?? 50,
        def: cfg.DEFAULT_POPULATION_SIZE ?? 12,
    };
};

class EvolutionCoordinator {
    #ctx = null;

    init(ctx = {}) {
        this.#ctx = ctx;
    }

    _populationSize() {
        const { min, max, def } = getPopLimits();
        const id = this.#ctx?.ids?.populationSizeInput;
        const el = id ? document.getElementById(id) : null;
        return clampInt(el?.value, min, max, def);
    }

    async evolve() {
        const evolveEl = this.#ctx?.ids?.evolveBtn
            ? document.getElementById(this.#ctx.ids.evolveBtn)
            : null;

        if (evolveEl?.classList.contains("disabled")) return;

        await Utils?.runTask?.({
            button: evolveEl,
            setLoading: this.#ctx?.showLoading,
            task: async () => {
                this.#ctx?.state?.dispatch?.({
                    type: "SET_LOADING",
                    payload: true,
                });
                const organisms = this.#ctx?.state?.organisms ?? [];
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
                const newGenerationNum = (this.#ctx?.state?.generationNum ?? 0) + 1;

                const genealogy = this.#ctx?.state?.getState?.()?.genealogy;
                const opts = {
                    parentPopulationId: genealogy?.populationId ?? null,
                    generationNum: newGenerationNum,
                    branchName: genealogy?.branchName || "main",
                };

                const data = await this.#ctx?.api?.evolve?.(
                    parents,
                    populationSize,
                    opts
                );
                if (!data?.children) throw new Error("No children in evolve response");

                if (data.population_id != null) {
                    this.#ctx?.state?.dispatch?.({
                        type: "SET_GENEALOGY",
                        payload: {
                            populationId: data.population_id,
                            branchName: genealogy?.branchName || "main",
                        },
                    });
                    GenealogySync?.syncCurrentPopulationIdToStorage?.(
                        data.population_id
                    );
                }

                populationLoader.loadPopulation(
                    data.children,
                    newGenerationNum,
                    data.representation_id,
                    { saveToGenealogy: false }
                );
            },
            onError: (err) => {
                console.error("Error evolving:", err);
                this.#ctx?.toast?.show?.(
                    "Evolve failed",
                    err?.message ?? String(err),
                    "error"
                );
            },
            onFinally: () => {
                this.#ctx?.state?.dispatch?.({
                    type: "SET_LOADING",
                    payload: false,
                });
                this.#ctx?.updateStats?.();
            },
        });
    }
}

const evolutionCoordinator = new EvolutionCoordinator();
export default evolutionCoordinator;
