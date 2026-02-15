/**
 * Eyecatcher app entry: init and DOM wiring.
 *
 * Core modules (PopulationState, GridRenderer, AnimationLoop, FullscreenModal,
 * RepresentationRegistry) are ES6 class instances on window; wiring is via init(options).
 * Load after: those modules, api_client, webgl_utils, viewer_controls, animation_loop,
 * population_ui, community, network_visualizer, toolbar_ui.
 */
(function () {
    "use strict";

    if (typeof vis === "undefined") {
        console.error(
            "ERROR: vis.js library not loaded! Network visualization will not work."
        );
    }

    var API_URL = window.API_URL || "";
    var IDS = {
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

    var EVENT_BINDINGS = [
        ["fullscreenClose", "closeFullscreen"],
        ["fullscreenBackdrop", "closeFullscreen"],
        ["evolveBtn", "evolveGeneration", true],
        ["loadModalClose", "closeLoadModal"],
        ["communitySubmitDo", "submitCommunityForm"],
        ["communitySubmitCancel", "closeSubmitCommunityModal"],
        ["communityListClose", "closeCommunityListModal"],
        ["communityLoadSelectedBtn", "onCommunityLoadSelected"],
        ["communityLoad12Btn", "onCommunityLoad12"],
        ["communitySelectAllBtn", "onCommunitySelectAll"],
        ["communityDeselectAllBtn", "onCommunityDeselectAll"],
        ["newFromCommunityBtn", "onNewFromCommunityClick", true],
        ["adminKeySubmit", "submitAdminKey"],
        ["adminModalCancel", "closeAdminModal"],
        ["adminListClose", "closeAdminModal"],
        ["saveCurrentBtn", "onSaveCurrentClick"],
        ["importBtn", "onImportClick"],
    ];

    function onRoleButtonKeydownForBindings(e, onClick) {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onClick();
        }
    }

    function applyEventBindings(IDS, handlers) {
        var onIdFn =
            window.Utils && window.Utils.onId
                ? window.Utils.onId
                : function (id, fn) {
                      var el = document.getElementById(id);
                      if (el) fn(el);
                  };
        EVENT_BINDINGS.forEach(function (b) {
            var idKey = b[0];
            var handlerKey = b[1];
            var withRoleKeydown = b[2];
            var id = IDS[idKey];
            var handler = handlers[handlerKey];
            if (!id || !handler) return;
            onIdFn(id, function (el) {
                el.addEventListener("click", handler);
                if (withRoleKeydown) {
                    el.addEventListener("keydown", function (e) {
                        onRoleButtonKeydownForBindings(e, handler);
                    });
                }
            });
        });
    }

    function updateStats() {
        var totalFitness = 0;
        var hasFitness = false;
        window.PopulationState.patterns.forEach(function (p) {
            totalFitness += p.fitness || 0;
            if (p.fitness > 0) hasFitness = true;
        });
        var totalEl = document.getElementById(IDS.totalFitness);
        if (totalEl) totalEl.textContent = totalFitness;
        var evolveEl = document.getElementById(IDS.evolveBtn);
        if (evolveEl) {
            if (hasFitness) {
                evolveEl.classList.remove("disabled");
                evolveEl.setAttribute("aria-disabled", "false");
            } else {
                evolveEl.classList.add("disabled");
                evolveEl.setAttribute("aria-disabled", "true");
            }
        }
    }

    function getGridCallbacks() {
        return {
            onShare: function (id) {
                window.CommunityUI.openSubmitCommunityModal(id);
            },
            onNetwork: function (id, card) {
                window.NetworkVisualizer.toggle(id, card);
            },
            onSave: window.OrganismActions.savePattern,
            onFullscreen: openFullscreen,
            onClick: function (id, card) {
                window.OrganismActions.clickPattern(id, card, updateStats);
            },
            onUnclick: function (id, card) {
                window.OrganismActions.unclickPattern(id, card, updateStats);
            },
            onMouseEnter: function (id) {
                if (typeof window.EyecatcherDebug !== "undefined") {
                    window.EyecatcherDebug.setHoveredPatternId(id);
                }
            },
            onMouseLeave: function (id) {
                if (
                    typeof window.EyecatcherDebug !== "undefined" &&
                    window.EyecatcherDebug.getHoveredPatternId() === id
                ) {
                    window.EyecatcherDebug.setHoveredPatternId(null);
                }
            },
        };
    }

    function openFullscreen(id) {
        window.FullscreenModal.openFullscreen(
            id,
            window.PopulationState.getState().currentPopulation,
            IDS
        );
    }

    function closeFullscreen() {
        window.FullscreenModal.closeFullscreen(IDS);
    }

    function resolveRepresentation(representationId, genomes) {
        var resolved = window.RepresentationRegistry.resolve({
            representationId: representationId,
            genomes: genomes,
        });
        return {
            representation: resolved.representation,
            representationId: resolved.representationId,
        };
    }

    function evolveGeneration() {
        window.EvolutionCoordinator.evolve();
    }

    function getCurrentGenomesForSave() {
        var genomes = window.PopulationState.currentGenomes;
        if (genomes && genomes.length) {
            return {
                genomes: genomes,
                generation: window.PopulationState.generationNum,
                representationId: window.PopulationState.representationId,
            };
        }
        return null;
    }

    function getGenomeForPattern(patternId) {
        var currentGenomes = window.PopulationState.currentGenomes;
        if (!currentGenomes) return Promise.resolve(null);
        var state = window.PopulationState.getState();
        var idx = state.currentPopulation.findIndex(function (p) {
            return p.id === patternId;
        });
        var genome = idx >= 0 && currentGenomes[idx] ? currentGenomes[idx] : null;
        return Promise.resolve(genome);
    }

    function updatePatternShader(individualId, newShader) {
        var pattern = window.PopulationState.patterns.get(individualId);
        if (pattern && window.WebGLUtils) {
            var newRuntime = window.WebGLUtils.setupPattern(pattern.canvas, newShader);
            if (newRuntime && !newRuntime.error) {
                window.PopulationState.dispatch({
                    type: "UPDATE_PATTERN_SHADER",
                    payload: {
                        id: individualId,
                        runtime: {
                            canvas: pattern.canvas,
                            gl: newRuntime.gl,
                            program: newRuntime.program,
                            positionBuffer: newRuntime.positionBuffer,
                            fitness: pattern.fitness || 0,
                        },
                    },
                });
            }
        }
    }

    function getPatterns() {
        var list = Array.from(window.PopulationState.patterns.values());
        var fullscreen = window.FullscreenModal.getFullscreenRuntime();
        if (fullscreen) list.push(fullscreen);
        return list;
    }

    function getCurrentPopulation() {
        return window.PopulationState.getState().currentPopulation;
    }

    function onGenomeUpdated(individualId, idx, genome) {
        window.PopulationState.dispatch({
            type: "UPDATE_GENOME_AT_INDEX",
            payload: { idx: idx, genome: genome },
        });
    }

    function setGenealogyState(populationId, branchName) {
        window.PopulationState.dispatch({
            type: "SET_GENEALOGY",
            payload: {
                populationId: populationId,
                branchName: branchName || "main",
            },
        });
        window.GenealogySync.syncCurrentPopulationIdToStorage(populationId);
    }

    function initGenealogyLoad(setGenealogyStateFn) {
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
        var loadGenomes =
            genealogyLoad && (genealogyLoad.individuals || genealogyLoad.genomes);
        if (loadGenomes && loadGenomes.length) {
            setGenealogyStateFn(
                genealogyLoad.population_id != null
                    ? genealogyLoad.population_id
                    : null,
                genealogyLoad.branch_name || "main"
            );
            var genNum =
                genealogyLoad.generation_num != null ? genealogyLoad.generation_num : 0;
            var resolved = window.RepresentationRegistry.resolve({
                representationId:
                    genealogyLoad.representation_id || genealogyLoad.substrate_id,
                genomes: loadGenomes,
            });
            window.GridRenderer.loadFromStatelessGenomes(
                loadGenomes,
                genNum,
                false,
                resolved.representationId
            );
        } else {
            window.PopulationUI.startNewRandomPopulation();
        }
    }

    function getPatternsMap() {
        return window.PopulationState.patterns;
    }

    window.PopulationState.init();
    window.ApiClient.init(API_URL);

    window.GridRenderer.init({
        IDS: IDS,
        API_URL: API_URL,
        getGridCallbacks: getGridCallbacks,
        resolveRepresentation: resolveRepresentation,
        getColorMode: function () {
            var el = document.querySelector('input[name="colorMode"]:checked');
            return el && el.value === "rgb" ? "rgb" : "hsv";
        },
        showLoading: showLoading,
        updateStats: updateStats,
    });

    window.EvolutionCoordinator.init({
        IDS: IDS,
        showLoading: showLoading,
        updateStats: updateStats,
    });

    window.onRepresentationSwitched = function (config) {
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
        if (window.Toast && window.Toast.show) {
            window.Toast.show(
                "Representation changed",
                "Use Start Fresh to get a population for " +
                    (config.representation_id || "the new substrate") +
                    ".",
                "info"
            );
        }
    };

    window.ApiClient.fetchConfig()
        .then(function (c) {
            window.EvolutionConfig.mergeFromServer(c);
            if (
                window.ToolbarUI &&
                window.ToolbarUI.syncToolbarPopulationSizeFromConfig
            ) {
                window.ToolbarUI.syncToolbarPopulationSizeFromConfig();
            }
        })
        .catch(function () {
            /* keep in-app defaults if server config fetch fails */
        });

    window.AnimationLoop.init({
        getPatterns: getPatterns,
        viewerControls: window.ViewerControls || null,
        signalSource: window.SignalSource,
    });

    window.PopulationUI.init({
        apiUrl: API_URL,
        loadFromStatelessGenomes: window.GridRenderer.loadFromStatelessGenomes.bind(
            window.GridRenderer
        ),
        addToGrid: window.GridRenderer.addToGrid.bind(window.GridRenderer),
        getCurrentGenomesForSave: getCurrentGenomesForSave,
    });

    window.CommunityUI.init({
        apiUrl: API_URL,
        loadFromStatelessGenomes: window.GridRenderer.loadFromStatelessGenomes.bind(
            window.GridRenderer
        ),
        addToGrid: window.GridRenderer.addToGrid.bind(window.GridRenderer),
        getGenomeForPattern: getGenomeForPattern,
        viewerControls: window.ViewerControls || null,
    });

    window.NetworkVisualizer.init({
        apiUrl: API_URL,
        getGenomeForPattern: getGenomeForPattern,
        updatePatternShader: updatePatternShader,
        getCurrentPopulation: getCurrentPopulation,
        onGenomeUpdated: onGenomeUpdated,
    });

    window.ToolbarUI.init();

    document.querySelectorAll('input[name="colorMode"]').forEach(function (radio) {
        radio.addEventListener("change", function () {
            var data = getCurrentGenomesForSave();
            if (!data) return;
            var representation = window.RepresentationRegistry.get(
                data.representationId
            );
            if (
                representation &&
                representation.phenotype &&
                representation.phenotype.substrate === "shader"
            ) {
                window.GridRenderer.loadFromStatelessGenomes(
                    data.genomes,
                    data.generation,
                    false,
                    data.representationId
                );
            }
        });
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") closeFullscreen();
    });

    var closeLoadModal = function () {
        var m = document.getElementById(IDS.loadListModal);
        if (m) m.classList.remove("show");
    };
    var closeCommunityListModal = function () {
        var m = document.getElementById(IDS.communityListModal);
        if (m) m.classList.remove("show");
    };
    applyEventBindings(IDS, {
        closeFullscreen: closeFullscreen,
        evolveGeneration: evolveGeneration,
        closeLoadModal: closeLoadModal,
        closeCommunityListModal: closeCommunityListModal,
        submitCommunityForm: window.CommunityUI.submitCommunityForm,
        closeSubmitCommunityModal: window.CommunityUI.closeSubmitCommunityModal,
        onCommunityLoadSelected: window.CommunityUI.onCommunityLoadSelected,
        onCommunityLoad12: window.CommunityUI.onCommunityLoad12,
        onCommunitySelectAll: window.CommunityUI.onCommunitySelectAll,
        onCommunityDeselectAll: window.CommunityUI.onCommunityDeselectAll,
        onNewFromCommunityClick: window.CommunityUI.onNewFromCommunityClick,
        submitAdminKey: window.CommunityUI.submitAdminKey,
        closeAdminModal: window.CommunityUI.closeAdminModal,
        onSaveCurrentClick: window.PopulationUI.onSaveCurrentClick,
        onImportClick: window.PopulationUI.onImportClick,
    });
    var onId =
        window.Utils && window.Utils.onId
            ? window.Utils.onId
            : function (id, fn) {
                  var el = document.getElementById(id);
                  if (el) fn(el);
              };
    onId(IDS.adminKeyInput, function (el) {
        el.addEventListener("keydown", function (e) {
            if (e.key === "Enter") window.CommunityUI.submitAdminKey();
        });
    });
    onId(IDS.importFile, function (el) {
        el.addEventListener("change", function (e) {
            var file = e.target.files && e.target.files[0];
            e.target.value = "";
            if (file && window.PopulationUI.handleImportFile) {
                window.PopulationUI.handleImportFile(file);
            }
        });
    });

    window.ViewerControls.init();

    if (typeof window.EyecatcherDebug !== "undefined") {
        window.EyecatcherDebug.init({
            apiUrl: API_URL,
            getMouseDistance: window.AnimationLoop.getMouseDistance.bind(
                window.AnimationLoop
            ),
            getPatterns: getPatternsMap,
            getSignalState: function () {
                return window.ViewerControls.signalState;
            },
            getGenomeForPattern: getGenomeForPattern,
            getRepresentation: function () {
                return window.RepresentationRegistry.get(
                    window.PopulationState.representationId
                );
            },
        });
    }

    initGenealogyLoad(setGenealogyState);
    window.AnimationLoop.start();

    console.log("Eyecatcher Interactive Evolution ready!");
})();
