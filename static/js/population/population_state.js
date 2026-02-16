/**
 * PopulationState: central in-memory store for organisms + metadata.
 * Small reducer-based state container. No DOM, no side effects.
 *
 * Canonical state (single source of truth):
 * - PopulationState: organisms, generationNum, representationId, genealogy, loading.
 * - Viewer state (zoom, selection): ViewerControls.patternZoom, OrganismActions selection; GridTopology for grid positions (derived from DOM).
 * - Inspection state: NetworkVisualizer (currentId, vis networks); genome/weight UI is driven by currentId.
 * - Caches (performance only, not source of truth): patternsMap in GridRenderer/PopulationLoader (id -> runtime), thumbnailCache in genealogy viewer, pending in network_weight_sliders (debounce).
 */
const initialState = () => ({
    organisms: [], // [{ id, genome, runtime, fitness, ... }]
    generationNum: 0,
    representationId: null,
    genealogy: {
        populationId: null,
        branchName: "main",
    },
    loading: false,
});

let state = initialState();

const clone = (obj) => structuredClone(obj);

const findIndexById = (id) => state.organisms.findIndex((o) => o.id === id);

const reducers = {
    LOAD_POPULATION(payload) {
        const patternsMap = payload.patternsMap ?? null;
        state.organisms = (payload.population || []).map((p, i) => {
            const id = p.id ?? i;
            const runtime = patternsMap?.get(id) ?? p.runtime ?? null;
            return {
                id,
                genome: payload.genomes ? payload.genomes[i] : (p.genome ?? null),
                runtime,
                fitness: p.fitness ?? 0,
                ...p,
            };
        });
        state.generationNum = payload.generationNum ?? 0;
        state.representationId = payload.representationId ?? null;
    },

    ADD_TO_POPULATION(payload) {
        const patternsMap = payload.patternsMap ?? null;
        const items = payload.population || [];
        items.forEach((p) => {
            const id = p.id;
            const runtime = patternsMap?.get(id) ?? p.runtime ?? null;
            state.organisms.push({
                id,
                genome: p.genome ?? null,
                runtime,
                fitness: p.fitness ?? 0,
                ...p,
            });
        });
    },

    SET_ORGANISM_FITNESS(payload) {
        const idx = findIndexById(payload.id);
        if (idx >= 0) state.organisms[idx].fitness = payload.fitness;
    },

    UPDATE_PATTERN_RULE(payload) {
        const idx = findIndexById(payload.id);
        if (idx >= 0) state.organisms[idx].runtime = payload.runtime;
    },

    UPDATE_GENOME_AT_INDEX(payload) {
        if (state.organisms[payload.idx]) {
            state.organisms[payload.idx].genome = payload.genome;
        }
    },

    SET_GENEALOGY(payload) {
        state.genealogy.populationId = payload.populationId ?? null;
        state.genealogy.branchName = payload.branchName ?? "main";
    },

    SET_LOADING(payload) {
        state.loading = Boolean(payload);
    },

    RESET() {
        state = initialState();
    },
};

const dispatch = ({ type, payload }) => {
    const reducer = reducers[type];
    if (!reducer) {
        console.warn("Unknown PopulationState action:", type);
        return;
    }
    reducer(payload || {});
};

const getState = () => state;

const getOrganism = (id) => state.organisms.find((o) => o.id === id) || null;

const getGenomes = () => state.organisms.map((o) => o.genome).filter(Boolean);

const getPhenotypes = () =>
    state.organisms.map((o) => ({
        id: o.id,
        image: o.image,
        rule: o.rule,
        grid: o.grid,
        fitness: o.fitness ?? 0,
        nodes: o.nodes,
        connections: o.connections,
    }));

const getStateSnapshot = () => clone(state);

const init = () => {
    state = initialState();
};

const populationState = {
    init,
    dispatch,
    getState,
    getStateSnapshot,
    getOrganism,
    getGenomes,
    getPhenotypes,
    get organisms() {
        return state.organisms;
    },
    get generationNum() {
        return state.generationNum;
    },
    get representationId() {
        return state.representationId;
    },
};

export default populationState;
window.PopulationState = populationState;
