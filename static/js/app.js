/**
 * Eyecatcher app entry: init and DOM wiring.
 *
 * Core modules (PopulationState, GridRenderer, AnimationLoop, FullscreenModal,
 * RepresentationRegistry) are instances on window; wiring is via init(options).
 *
 * Load after: those modules, api_client, webgl_utils, viewer_controls, animation_loop,
 * population_ui, community, genome_visualizer, toolbar_ui.
 */
(() => {
    "use strict";

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

    const onId =
        window.Utils?.onId ??
        ((id, fn) => {
            const el = getEl(id);
            if (el) fn(el);
        });

    const bindClick = (id, handler) => {
        if (!id || !handler) return;
        onId(id, (el) => el.addEventListener("click", handler));
    };

    const bindRoleButton = (id, handler) => {
        if (!id || !handler) return;
        onId(id, (el) => {
            el.addEventListener("click", handler);
            if (window.Utils?.onRoleButtonKeydown) {
                window.Utils.onRoleButtonKeydown(el, handler);
                return;
            }
            el.addEventListener("keydown", (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handler();
                }
            });
        });
    };

    const getColorMode = () => {
        const el = document.querySelector('input[name="colorMode"]:checked');
        return el?.value === "rgb" ? "rgb" : "hsv";
    };

    const showLoading = (show) => window.PopulationLoader?.showLoading?.(show);

    const closeModalById = (id) => {
        const m = getEl(id);
        if (m) m.classList.remove("show");
    };

    const openFullscreen = (id) => {
        window.FullscreenModal.openFullscreen(
            id,
            window.PopulationState.getPhenotypes(),
            IDS
        );
    };

    const closeFullscreen = () => {
        window.FullscreenModal.closeFullscreen(IDS);
    };

    const resolveRepresentation = (representationId, genomes) => {
        const resolved = window.RepresentationRegistry.resolve({
            representationId,
            genomes,
        });
        return {
            representation: resolved.representation,
            representationId: resolved.representationId,
        };
    };

    const evolveGeneration = () => {
        window.EvolutionCoordinator.evolve();
    };

    const getCurrentGenomesForSave = () => {
        const genomes = window.PopulationState.getGenomes();
        if (genomes && genomes.length) {
            return {
                genomes,
                generation: window.PopulationState.generationNum,
                representationId: window.PopulationState.representationId,
            };
        }
        return null;
    };

    const getGenomeForPattern = (patternId) => {
        const org = window.PopulationState.getOrganism(patternId);
        return Promise.resolve(org ? org.genome : null);
    };

    const updatePatternRule = (individualId, newRule) => {
        const org = window.PopulationState.getOrganism(individualId);
        const runtime = org?.runtime;
        if (!runtime || !window.WebGLUtils) return;

        const newRuntime = window.WebGLUtils.setupPattern(runtime.canvas, newRule);
        if (!newRuntime || newRuntime.error) return;

        window.PopulationState.dispatch({
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
        const list = window.PopulationState.organisms
            .filter((o) => o.runtime != null)
            .map((o) => o.runtime);

        const fullscreen = window.FullscreenModal.getFullscreenRuntime();
        if (fullscreen) list.push(fullscreen);

        return list;
    };

    const getPatternsMap = () => {
        const map = new Map();
        window.PopulationState.organisms.forEach((o) => {
            if (o.runtime != null) map.set(o.id, o.runtime);
        });
        return map;
    };

    const getCurrentPopulation = () => window.PopulationState.getPhenotypes();

    const onGenomeUpdated = (individualId, idx, genome) => {
        window.PopulationState.dispatch({
            type: "UPDATE_GENOME_AT_INDEX",
            payload: { idx, genome },
        });
    };

    const updateStats = () => {
        let totalFitness = 0;
        let hasFitness = false;

        window.PopulationState.organisms.forEach((o) => {
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
        onShare: (id) => window.CommunityUI.openSubmitCommunityModal(id),
        onNetwork: (id, card) => window.NetworkVisualizer.toggle(id, card),
        onSave: window.OrganismActions.savePattern,
        onFullscreen: openFullscreen,
        onClick: (id, card) =>
            window.OrganismActions.clickPattern(id, card, updateStats),
        onUnclick: (id, card) =>
            window.OrganismActions.unclickPattern(id, card, updateStats),
        onMouseEnter: (id) => window.EyecatcherDebug?.setHoveredPatternId?.(id),
        onMouseLeave: (id) => {
            if (window.EyecatcherDebug?.getHoveredPatternId?.() === id) {
                window.EyecatcherDebug.setHoveredPatternId(null);
            }
        },
    });

    const setGenealogyState = (populationId, branchName) => {
        window.PopulationState.dispatch({
            type: "SET_GENEALOGY",
            payload: { populationId, branchName: branchName || "main" },
        });
        window.GenealogySync.syncCurrentPopulationIdToStorage(populationId);
    };

    const initGenealogyLoad = (setGenealogyStateFn) => {
        const raw =
            window.Utils?.safeGetItem?.(localStorage, "genealogy_load", null) ?? null;
        if (!raw) {
            window.PopulationUI.startNewRandomPopulation();
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
            window.PopulationUI.startNewRandomPopulation();
            return;
        }

        const loadGenomes = genealogyLoad?.individuals || genealogyLoad?.genomes;
        if (!Array.isArray(loadGenomes) || loadGenomes.length === 0) {
            window.PopulationUI.startNewRandomPopulation();
            return;
        }

        setGenealogyStateFn(
            genealogyLoad.population_id != null ? genealogyLoad.population_id : null,
            genealogyLoad.branch_name || "main"
        );

        const genNum =
            genealogyLoad.generation_num != null ? genealogyLoad.generation_num : 0;

        const resolved = window.RepresentationRegistry.resolve({
            representationId:
                genealogyLoad.representation_id || genealogyLoad.substrate_id,
            genomes: loadGenomes,
        });

        window.PopulationLoader.loadPopulation(
            loadGenomes,
            genNum,
            resolved.representationId,
            {
                saveToGenealogy: false,
            }
        );
    };

    /** Wrapper for UI that expects (genomes, generationNum, saveToGenealogy, representationId). */
    const loadFromStatelessGenomes = (
        genomes,
        generationNum,
        saveToGenealogy,
        representationId
    ) =>
        window.PopulationLoader.loadPopulation(
            genomes,
            generationNum,
            representationId,
            {
                saveToGenealogy,
            }
        );

    // ---------- Boot sequence ----------
    window.PopulationState.init();
    window.ApiClient.init(API_URL);

    const gridDeps = {
        IDS,
        API_URL,
        getGridCallbacks,
        resolveRepresentation,
        getColorMode,
        showLoading,
        updateStats,
    };

    window.GridRenderer.init(gridDeps);
    window.PopulationLoader.init(gridDeps);

    window.EvolutionCoordinator.init({ IDS, showLoading, updateStats });

    window.onRepresentationSwitched = (config) => {
        window.GridRenderer.clearGrid(IDS);

        window.PopulationState.dispatch({
            type: "LOAD_POPULATION",
            payload: {
                population: [],
                genomes: null,
                generationNum: 0,
                representationId: config.representation_id,
            },
        });

        window.ViewerControls.updateForRepresentation(config.representation_id);
        window.GridTopology.rebuild(null);

        window.Toast?.show?.(
            "Representation changed",
            `Use Start Fresh to get a population for ${config.representation_id || "the new substrate"}.`,
            "info"
        );
    };

    window.ApiClient.fetchConfig()
        .then((c) => {
            window.EvolutionConfig.mergeFromServer(c);

            if (c?.representation_id && window.__eyecatcherDefaultResolution) {
                window.__eyecatcherDefaultResolution.representationId =
                    c.representation_id;
            }

            const needsRep =
                window.PopulationState.representationId == null ||
                window.PopulationState.organisms.length === 0;

            if (needsRep && c?.representation_id) {
                window.PopulationState.dispatch({
                    type: "LOAD_POPULATION",
                    payload: {
                        population: [],
                        genomes: null,
                        generationNum: 0,
                        representationId: c.representation_id,
                    },
                });
            }

            window.ToolbarUI?.syncToolbarPopulationSizeFromConfig?.();
            if (c?.representation_id)
                window.ViewerControls?.updateForRepresentation?.(c.representation_id);
        })
        .catch(() => {
            /* keep in-app defaults if server config fetch fails */
        });

    window.AnimationLoop.init({
        getPatterns,
        viewerControls: window.ViewerControls || null,
        signalSource: window.SignalSource,
    });

    window.PopulationUI.init({
        apiUrl: API_URL,
        loadFromStatelessGenomes,
        addToGrid: window.PopulationLoader.addToPopulation.bind(
            window.PopulationLoader
        ),
        getCurrentGenomesForSave,
    });

    window.CommunityUI.init({
        apiUrl: API_URL,
        loadFromStatelessGenomes,
        addToGrid: window.PopulationLoader.addToPopulation.bind(
            window.PopulationLoader
        ),
        getGenomeForPattern,
        viewerControls: window.ViewerControls || null,
    });

    window.NetworkVisualizer.init({
        apiUrl: API_URL,
        getGenomeForPattern,
        updatePatternRule,
        getCurrentPopulation,
        onGenomeUpdated,
    });

    window.ToolbarUI.init();
    window.ViewerControls.init();

    // Color mode switch reload: only relevant for field substrates (shader).
    document.querySelectorAll('input[name="colorMode"]').forEach((radio) => {
        radio.addEventListener("change", () => {
            const data = getCurrentGenomesForSave();
            if (!data) return;

            const representation = window.RepresentationRegistry.get(
                data.representationId
            );
            const st = representation?.phenotype?.substrate;
            const isField =
                (typeof st === "string" && st === "field") ||
                (st && st.type === "field");

            if (representation?.phenotype && isField) {
                window.PopulationLoader.loadPopulation(
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

    bindClick(IDS.communitySubmitDo, window.CommunityUI.submitCommunityForm);
    bindClick(IDS.communitySubmitCancel, window.CommunityUI.closeSubmitCommunityModal);
    bindClick(IDS.communityListClose, closeCommunityListModal);

    bindClick(IDS.communityLoadSelectedBtn, window.CommunityUI.onCommunityLoadSelected);
    bindClick(IDS.communityLoad12Btn, window.CommunityUI.onCommunityLoad12);
    bindClick(IDS.communitySelectAllBtn, window.CommunityUI.onCommunitySelectAll);
    bindClick(IDS.communityDeselectAllBtn, window.CommunityUI.onCommunityDeselectAll);

    bindRoleButton(IDS.newFromCommunityBtn, window.CommunityUI.onNewFromCommunityClick);

    bindClick(IDS.adminKeySubmit, window.CommunityUI.submitAdminKey);
    bindClick(IDS.adminModalCancel, window.CommunityUI.closeAdminModal);
    bindClick(IDS.adminListClose, window.CommunityUI.closeAdminModal);

    bindClick(IDS.saveCurrentBtn, window.PopulationUI.onSaveCurrentClick);
    bindClick(IDS.importBtn, window.PopulationUI.onImportClick);

    // Admin key input: Enter submits
    onId(IDS.adminKeyInput, (el) => {
        el.addEventListener("keydown", (e) => {
            if (e.key === "Enter") window.CommunityUI.submitAdminKey();
        });
    });

    // Import file input: consume once, then reset
    onId(IDS.importFile, (el) => {
        el.addEventListener("change", (e) => {
            const file = e.target.files && e.target.files[0];
            e.target.value = "";
            if (file) window.PopulationUI.handleImportFile?.(file);
        });
    });

    if (window.EyecatcherDebug) {
        window.EyecatcherDebug.init({
            apiUrl: API_URL,
            getMouseDistance: window.AnimationLoop.getMouseDistance.bind(
                window.AnimationLoop
            ),
            getPatterns: getPatternsMap,
            getSignalState: () => window.ViewerControls.signalState,
            getGenomeForPattern,
            getRepresentation: () =>
                window.RepresentationRegistry.get(
                    window.PopulationState.representationId
                ),
        });
    }

    initGenealogyLoad(setGenealogyState);
    window.AnimationLoop.start();

    console.log("Eyecatcher Interactive Evolution ready!");
})();
