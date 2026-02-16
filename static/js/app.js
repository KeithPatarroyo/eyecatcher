/**
 * Eyecatcher app entry: init and DOM wiring.
 * All core modules are imported; wiring is via init(options).
 */
import RepresentationRegistry from "./representation/representation_registry.js";
import GridRenderer from "./viewer/grid_renderer.js";
import { gridTopology } from "./viewer/grid_renderer.js";
import Utils from "./lib/utils.js";
import Toast from "./lib/toast.js";
import apiInstance from "./lib/api_client.js";
import populationState from "./population/population_state.js";
import populationLoader from "./population/population_loader.js";
import populationUI from "./population/population_ui.js";
import fullscreenModal from "./viewer/fullscreen_modal.js";
import evolutionCoordinator from "./evolution/coordinator.js";
import viewerControls from "./evolution/viewer_controls.js";
import { CommunityUI } from "./community/index.js";
import { assertConfig, EvolutionConfig } from "./evolution/experiment_config.js";
import WebGLUtils from "./representation/webgl_utils.js";
import organismActions from "./viewer/organism_actions.js";
import eyecatcherDebug from "./lib/debug.js";
import toolbarUI from "./viewer/toolbar_ui.js";
import { NetworkVisualizer } from "./inspection/genome_visualizer.js";
import GenealogySync from "./genealogy/sync.js";
import animationLoop from "./viewer/animation_loop.js";

if (typeof vis === "undefined") {
    console.error(
        "ERROR: vis.js library not loaded! Network visualization will not work."
    );
}

const API_URL = window.API_URL || "";

const IDS = {
    grid: "grid",
    fullscreenModal: "fullscreen-modal",
    fullscreenCanvasWrap: "fullscreen-canvas-wrap",
    gridErrorTpl: "grid-error-tpl",
    gridRetryBtn: "grid-retry-btn",
    genNum: "gen-num",
    evolveBtn: "evolve-btn",
    populationSizeInput: "population-size-input",
    totalFitness: "total-fitness",
    loadListModal: "load-list-modal",
    communityListModal: "community-list-modal",
    fullscreenClose: "fullscreen-close",
    fullscreenBackdrop: "fullscreen-backdrop",
    loadModalClose: "load-modal-close",
    communitySubmitDo: "community-submit-do",
    communitySubmitCancel: "community-submit-cancel",
    communityListClose: "community-list-close",
    communityLoadSelectedBtn: "community-load-selected-btn",
    communityLoad12Btn: "community-load-12-btn",
    communitySelectAllBtn: "community-select-all-btn",
    communityDeselectAllBtn: "community-deselect-all-btn",
    newFromCommunityBtn: "new-from-community-btn",
    adminKeySubmit: "admin-key-submit",
    adminModalCancel: "admin-modal-cancel",
    adminListClose: "admin-list-close",
    adminKeyInput: "admin-key-input",
    saveCurrentBtn: "save-current-btn",
    importBtn: "import-btn",
    importFile: "import-file",
};

const getEl = (id) => (id ? document.getElementById(id) : null);

const onId = (id, fn) => Utils.onId(id, fn);

const bindClick = (id, handler) => {
    if (!id || !handler) return;
    onId(id, (el) => el.addEventListener("click", handler));
};

const bindRoleButton = (id, handler) => {
    if (!id || !handler) return;
    onId(id, (el) => {
        Utils.onRoleButtonKeydown(el, handler);
    });
};

const getColorMode = () => {
    const el = document.querySelector('input[name="colorMode"]:checked');
    return el?.value === "rgb" ? "rgb" : "hsv";
};

const showLoading = (show) => populationLoader?.showLoading?.(show);

const closeModalById = (id) => {
    const m = getEl(id);
    if (m) m.classList.remove("show");
};

const openFullscreen = (id) => {
    fullscreenModal.openFullscreen(id, populationState.getPhenotypes(), IDS);
};

const closeFullscreen = () => {
    fullscreenModal.closeFullscreen(IDS);
};

const resolveRepresentation = (representationId, genomes) => {
    const resolved = RepresentationRegistry.resolve({
        representationId,
        genomes,
    });
    return {
        representation: resolved.representation,
        representationId: resolved.representationId,
    };
};

const evolveGeneration = () => {
    evolutionCoordinator.evolve();
};

const getCurrentGenomesForSave = () => {
    const genomes = populationState.getGenomes();
    if (genomes && genomes.length) {
        return {
            genomes,
            generation: populationState.generationNum,
            representationId: populationState.representationId,
        };
    }
    return null;
};

const getGenomeForPattern = (patternId) => {
    const org = populationState.getOrganism(patternId);
    return Promise.resolve(org ? org.genome : null);
};

const updatePatternRule = (individualId, newRule) => {
    const org = populationState.getOrganism(individualId);
    const runtime = org?.runtime;
    if (!runtime || !WebGLUtils) return;

    const newRuntime = WebGLUtils.setupPattern(runtime.canvas, newRule);
    if (!newRuntime || newRuntime.error) return;

    populationState.dispatch({
        type: "UPDATE_PATTERN_RULE",
        payload: {
            id: individualId,
            runtime: {
                canvas: runtime.canvas,
                gl: newRuntime.gl,
                program: newRuntime.program,
                positionBuffer: newRuntime.positionBuffer,
                fitness: runtime.fitness || 0,
            },
        },
    });
};

const getPatterns = () => {
    const list = populationState.organisms
        .filter((o) => o.runtime != null)
        .map((o) => o.runtime);

    const fullscreen = fullscreenModal.getFullscreenRuntime();
    if (fullscreen) list.push(fullscreen);

    return list;
};

const getPatternsMap = () => {
    const map = new Map();
    populationState.organisms.forEach((o) => {
        if (o.runtime != null) map.set(o.id, o.runtime);
    });
    return map;
};

const getCurrentPopulation = () => populationState.getPhenotypes();

const onGenomeUpdated = (individualId, idx, genome) => {
    populationState.dispatch({
        type: "UPDATE_GENOME_AT_INDEX",
        payload: { idx, genome },
    });
};

const updateStats = () => {
    let totalFitness = 0;
    let hasFitness = false;

    populationState.organisms.forEach((o) => {
        const f = o.fitness || 0;
        totalFitness += f;
        if (f > 0) hasFitness = true;
    });

    const totalEl = getEl(IDS.totalFitness);
    if (totalEl) totalEl.textContent = String(totalFitness);

    const evolveEl = getEl(IDS.evolveBtn);
    if (!evolveEl) return;

    evolveEl.classList.toggle("disabled", !hasFitness);
    evolveEl.setAttribute("aria-disabled", hasFitness ? "false" : "true");
};

const getGridCallbacks = () => ({
    onShare: (id) => CommunityUI.openSubmitCommunityModal(id),
    onNetwork: (id, card) => NetworkVisualizer.toggle(id, card),
    onSave: organismActions.savePattern,
    onFullscreen: openFullscreen,
    onClick: (id, card) => organismActions.clickPattern(id, card, updateStats),
    onUnclick: (id, card) => organismActions.unclickPattern(id, card, updateStats),
    onMouseEnter: (id) => eyecatcherDebug?.setHoveredPatternId?.(id),
    onMouseLeave: (id) => {
        if (eyecatcherDebug?.getHoveredPatternId?.() === id) {
            eyecatcherDebug.setHoveredPatternId(null);
        }
    },
});

const setGenealogyState = (populationId, branchName) => {
    populationState.dispatch({
        type: "SET_GENEALOGY",
        payload: { populationId, branchName: branchName || "main" },
    });
    GenealogySync.syncCurrentPopulationIdToStorage(populationId);
};

const initGenealogyLoad = (setGenealogyStateFn) => {
    const raw = Utils?.safeGetItem?.(localStorage, "genealogy_load", null) ?? null;
    if (!raw) {
        populationUI.startNewRandomPopulation();
        return;
    }

    let genealogyLoad = null;
    try {
        genealogyLoad = JSON.parse(raw);
        try {
            localStorage.removeItem("genealogy_load");
        } catch (_e) {
            /* ignore */
        }
    } catch (e) {
        console.warn("Genealogy load parse failed:", e);
        populationUI.startNewRandomPopulation();
        return;
    }

    const loadGenomes = genealogyLoad?.individuals || genealogyLoad?.genomes;
    if (!Array.isArray(loadGenomes) || loadGenomes.length === 0) {
        populationUI.startNewRandomPopulation();
        return;
    }

    setGenealogyStateFn(
        genealogyLoad.population_id != null ? genealogyLoad.population_id : null,
        genealogyLoad.branch_name || "main"
    );

    const genNum =
        genealogyLoad.generation_num != null ? genealogyLoad.generation_num : 0;

    const resolved = RepresentationRegistry.resolve({
        representationId: genealogyLoad.representation_id || genealogyLoad.substrate_id,
        genomes: loadGenomes,
    });

    populationLoader.loadPopulation(loadGenomes, genNum, resolved.representationId, {
        saveToGenealogy: false,
    });
};

/** Wrapper for UI that expects (genomes, generationNum, saveToGenealogy, representationId). */
const loadFromStatelessGenomes = (
    genomes,
    generationNum,
    saveToGenealogy,
    representationId
) =>
    populationLoader.loadPopulation(genomes, generationNum, representationId, {
        saveToGenealogy,
    });

// ---------- Boot sequence ----------
Utils.setPopulationRefs(populationLoader, populationState);
populationState.init();
apiInstance.init(API_URL);
if (typeof assertConfig === "function") assertConfig();

/** Frontend context: one object passed into inits so modules use ctx.api / ctx.state instead of window.* */
const ctx = {
    api: apiInstance,
    state: populationState,
    toast: Toast,
    ids: IDS,
    apiUrl: API_URL,
    getGridCallbacks,
    resolveRepresentation,
    getColorMode,
    showLoading,
    updateStats,
};

const gridDeps = {
    ...ctx,
    IDS: ctx.ids,
    API_URL: ctx.apiUrl,
};

GridRenderer.init(gridDeps);
populationLoader.init(gridDeps);

evolutionCoordinator.init(ctx);

window.onRepresentationSwitched = (config) => {
    GridRenderer.clearGrid(IDS);

    populationState.dispatch({
        type: "LOAD_POPULATION",
        payload: {
            population: [],
            genomes: null,
            generationNum: 0,
            representationId: config.representation_id,
        },
    });

    viewerControls.updateForRepresentation(config.representation_id);
    gridTopology.rebuild(null);

    Toast?.show?.(
        "Representation changed",
        `Use Start Fresh to get a population for ${config.representation_id || "the new substrate"}.`,
        "info"
    );
};

apiInstance
    .fetchConfig()
    .then((c) => {
        EvolutionConfig.mergeFromServer(c);

        if (c?.representation_id && window.__eyecatcherDefaultResolution) {
            window.__eyecatcherDefaultResolution.representationId = c.representation_id;
        }

        const needsRep =
            populationState.representationId == null ||
            populationState.organisms.length === 0;

        if (needsRep && c?.representation_id) {
            populationState.dispatch({
                type: "LOAD_POPULATION",
                payload: {
                    population: [],
                    genomes: null,
                    generationNum: 0,
                    representationId: c.representation_id,
                },
            });
        }

        toolbarUI?.syncToolbarPopulationSizeFromConfig?.();
        if (c?.representation_id)
            viewerControls?.updateForRepresentation?.(c.representation_id);
    })
    .catch(() => {
        /* keep in-app defaults if server config fetch fails */
    });

animationLoop.init({
    getPatterns,
    viewerControls: viewerControls || null,
    signalSource: window.SignalSource,
});

populationUI.init({
    ...ctx,
    loadFromStatelessGenomes,
    addToGrid: populationLoader.addToPopulation.bind(populationLoader),
    getCurrentGenomesForSave,
});

CommunityUI.init({
    ...ctx,
    loadFromStatelessGenomes,
    addToGrid: populationLoader.addToPopulation.bind(populationLoader),
    getGenomeForPattern,
    viewerControls: viewerControls || null,
});

NetworkVisualizer.init({
    ...ctx,
    getGenomeForPattern,
    updatePatternRule,
    getCurrentPopulation,
    onGenomeUpdated,
});

toolbarUI.init();
viewerControls.init();

// Color mode switch reload: only relevant for field substrates (shader).
document.querySelectorAll('input[name="colorMode"]').forEach((radio) => {
    radio.addEventListener("change", () => {
        const data = getCurrentGenomesForSave();
        if (!data) return;

        const representation = RepresentationRegistry.get(data.representationId);
        const st = representation?.phenotype?.substrate;
        const isField =
            (typeof st === "string" && st === "field") || (st && st.type === "field");

        if (representation?.phenotype && isField) {
            populationLoader.loadPopulation(
                data.genomes,
                data.generation,
                data.representationId,
                {
                    saveToGenealogy: false,
                }
            );
        }
    });
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeFullscreen();
});

// Modal closers (kept as tiny helpers so applyEventBindings can stay simple).
const closeLoadModal = () => closeModalById(IDS.loadListModal);
const closeCommunityListModal = () => closeModalById(IDS.communityListModal);

// Centralised button wiring
bindClick(IDS.fullscreenClose, closeFullscreen);
bindClick(IDS.fullscreenBackdrop, closeFullscreen);

bindRoleButton(IDS.evolveBtn, evolveGeneration);
bindClick(IDS.loadModalClose, closeLoadModal);

bindClick(IDS.communitySubmitDo, CommunityUI.submitCommunityForm);
bindClick(IDS.communitySubmitCancel, CommunityUI.closeSubmitCommunityModal);
bindClick(IDS.communityListClose, closeCommunityListModal);

bindClick(IDS.communityLoadSelectedBtn, CommunityUI.onCommunityLoadSelected);
bindClick(IDS.communityLoad12Btn, CommunityUI.onCommunityLoad12);
bindClick(IDS.communitySelectAllBtn, CommunityUI.onCommunitySelectAll);
bindClick(IDS.communityDeselectAllBtn, CommunityUI.onCommunityDeselectAll);

bindRoleButton(IDS.newFromCommunityBtn, CommunityUI.onNewFromCommunityClick);

bindClick(IDS.adminKeySubmit, CommunityUI.submitAdminKey);
bindClick(IDS.adminModalCancel, CommunityUI.closeAdminModal);
bindClick(IDS.adminListClose, CommunityUI.closeAdminModal);

bindClick(IDS.saveCurrentBtn, populationUI.onSaveCurrentClick);
bindClick(IDS.importBtn, populationUI.onImportClick);

// Admin key input: Enter submits
onId(IDS.adminKeyInput, (el) => {
    el.addEventListener("keydown", (e) => {
        if (e.key === "Enter") CommunityUI.submitAdminKey();
    });
});

// Import file input: consume once, then reset
onId(IDS.importFile, (el) => {
    el.addEventListener("change", (e) => {
        const file = e.target.files && e.target.files[0];
        e.target.value = "";
        if (file) populationUI.handleImportFile?.(file);
    });
});

if (eyecatcherDebug) {
    eyecatcherDebug.init({
        apiUrl: API_URL,
        getMouseDistance: animationLoop.getMouseDistance.bind(animationLoop),
        getPatterns: getPatternsMap,
        getSignalState: () => viewerControls.signalState,
        getGenomeForPattern,
        getRepresentation: () =>
            RepresentationRegistry.get(populationState.representationId),
    });
}

initGenealogyLoad(setGenealogyState);
animationLoop.start();

console.log("Eyecatcher Interactive Evolution ready!");
