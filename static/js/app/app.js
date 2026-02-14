/**
 * Eyecatcher app entry: init and DOM wiring.
 *
 * Core modules (PopulationState, GridRenderer, AnimationLoop, FullscreenModal,
 * SubstrateAdapters) are ES6 class instances on window; wiring is via init(options).
 * Load after: those modules, api_client, pattern_renderer, viewer_controls, animation_loop,
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
        totalClicks: "total-clicks",
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

    function onId(id, fn) {
        var el = document.getElementById(id);
        if (el) fn(el);
    }

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

    function applyEventBindings(IDS, handlers, onIdFn) {
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

    function getColorMode() {
        var el = document.querySelector('input[name="colorMode"]:checked');
        return el && el.value === "rgb" ? "rgb" : "hsv";
    }

    function setEvolveButtonDisabled(disabled) {
        var el = document.getElementById(IDS.evolveBtn);
        if (el) {
            if (disabled) {
                el.classList.add("disabled");
                el.setAttribute("aria-disabled", "true");
            } else {
                el.classList.remove("disabled");
                el.setAttribute("aria-disabled", "false");
            }
        }
    }

    function updateStats() {
        var totalClicks = 0;
        var hasFitness = false;
        window.PopulationState.patterns.forEach(function (p) {
            totalClicks += p.clicks || 0;
            if (p.clicks > 0) hasFitness = true;
        });
        var totalEl = document.getElementById(IDS.totalClicks);
        if (totalEl) totalEl.textContent = totalClicks;
        setEvolveButtonDisabled(!hasFitness);
    }

    function showGridError(message, showRetry) {
        var grid = document.getElementById(IDS.grid);
        var tpl = document.getElementById(IDS.gridErrorTpl);
        window.GridRenderer.clearGrid(IDS);
        grid = document.getElementById(IDS.grid);
        if (!tpl || !tpl.content) {
            if (grid) {
                var wrap = document.createElement("div");
                wrap.className = "grid-error";
                var msg = document.createElement("div");
                msg.className = "grid-error__message";
                msg.textContent = message;
                wrap.appendChild(msg);
                grid.appendChild(wrap);
            }
            showLoading(false);
            return;
        }
        var devPort = window.DEFAULT_DEV_PORT || 5001;
        var localUrl = "http://localhost:" + devPort;
        var fragment = tpl.content.cloneNode(true);
        var root = fragment.querySelector(".grid-error");
        fragment.querySelector(".grid-error__message").textContent = message;
        var link = fragment.querySelector("#grid-error-link");
        if (link) {
            link.href = localUrl;
            link.textContent = localUrl;
        }
        if (showRetry) {
            var retryBtn = document.createElement("button");
            retryBtn.type = "button";
            retryBtn.className = "retry-btn";
            retryBtn.id = "grid-retry-btn";
            retryBtn.textContent = "New random population";
            root.appendChild(retryBtn);
        }
        window.GridRenderer.clearGrid(IDS);
        grid = document.getElementById(IDS.grid);
        if (grid) grid.appendChild(fragment);
        showLoading(false);
        if (showRetry) {
            var retryEl = document.getElementById(IDS.gridRetryBtn);
            if (retryEl) {
                retryEl.onclick = function () {
                    window.PopulationUI.startNewRandomPopulation();
                };
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
            onSave: window.PatternActions.savePattern,
            onFullscreen: openFullscreen,
            onClick: function (id, card) {
                window.PatternActions.clickPattern(id, card, updateStats);
            },
            onUnclick: function (id, card) {
                window.PatternActions.unclickPattern(id, card, updateStats);
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

    function resolveAdapterAndOutput(outputType, substrateId, genomes) {
        var resolved = window.SubstrateAdapters.safeResolve({
            outputType: outputType,
            substrateId: substrateId,
            genomes: genomes,
        });
        return {
            adapter: resolved.adapter,
            outputType: outputType || resolved.outputType,
            substrateId: substrateId || resolved.substrateId,
        };
    }

    function evolveGeneration() {
        var evolveEl = document.getElementById(IDS.evolveBtn);
        if (evolveEl && evolveEl.classList.contains("disabled")) return;
        setEvolveButtonDisabled(true);
        showLoading(true);
        window.PopulationState.dispatch({ type: "SET_LOADING", payload: true });

        function getPopulationSize() {
            var el = document.getElementById(IDS.populationSizeInput);
            return parseInt(el && el.value, 10);
        }

        window.EvolutionCoordinator.evolveGeneration(
            window.PopulationState.getState,
            getPopulationSize,
            window.ApiClient.evolve.bind(window.ApiClient),
            function (
                children,
                newGenerationNum,
                populationId,
                outputType,
                substrateId
            ) {
                if (populationId != null) {
                    window.PopulationState.dispatch({
                        type: "SET_EVOLVE_RESULT",
                        payload: { populationId: populationId },
                    });
                    window.GenealogySync.syncCurrentPopulationIdToStorage(populationId);
                }
                window.GridRenderer.loadFromStatelessGenomes(
                    children,
                    newGenerationNum,
                    false,
                    outputType,
                    substrateId
                );
            },
            function (err) {
                console.error("Error evolving:", err);
                window.Toast.error("Evolve failed: " + (err.message || String(err)));
                showLoading(false);
                window.PopulationState.dispatch({
                    type: "SET_LOADING",
                    payload: false,
                });
                setEvolveButtonDisabled(false);
                updateStats();
            }
        );
    }

    function getCurrentGenomesForSave() {
        var genomes = window.PopulationState.currentGenomes;
        if (genomes && genomes.length) {
            return {
                genomes: genomes,
                generation: window.PopulationState.generationNum,
                substrateId: window.PopulationState.substrateId,
                outputType: window.PopulationState.outputType,
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
        if (pattern && window.PatternRenderer) {
            var newPatternData = window.PatternRenderer.setupPattern(
                pattern.canvas,
                newShader
            );
            if (newPatternData && !newPatternData.error) {
                window.PopulationState.dispatch({
                    type: "UPDATE_PATTERN_SHADER",
                    payload: {
                        id: individualId,
                        patternData: {
                            canvas: pattern.canvas,
                            gl: newPatternData.gl,
                            program: newPatternData.program,
                            positionBuffer: newPatternData.positionBuffer,
                            clicks: pattern.clicks || 0,
                        },
                    },
                });
            }
        }
    }

    function getPatterns() {
        var list = Array.from(window.PopulationState.patterns.values());
        var fullscreen = window.FullscreenModal.getFullscreenPatternData();
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
            var resolved = window.SubstrateAdapters.safeResolve({
                substrateId:
                    genealogyLoad.representation_id || genealogyLoad.substrate_id,
                genomes: loadGenomes,
            });
            window.GridRenderer.loadFromStatelessGenomes(
                loadGenomes,
                genNum,
                false,
                resolved.outputType,
                resolved.substrateId
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
        resolveAdapterAndOutput: resolveAdapterAndOutput,
        getColorMode: getColorMode,
        showLoading: showLoading,
        showGridError: showGridError,
        updateStats: updateStats,
    });

    window.onSubstrateSwitched = function (config) {
        window.GridRenderer.clearGrid(IDS);
        window.PopulationState.dispatch({
            type: "LOAD_POPULATION",
            payload: {
                population: [],
                genomes: null,
                generationNum: 0,
                substrateId: config.representation_id,
                outputType: config.output_type || "shader",
            },
        });
        window.ViewerControls.updateForSubstrate(config.representation_id);
        window.GridTopology.rebuild(null);
        if (window.Toast && window.Toast.show) {
            window.Toast.show(
                "Substrate changed",
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
            /* fallback to hardcoded EvolutionConfig */
        });

    window.AnimationLoop.init({
        getPatterns: getPatterns,
        patternRenderer: window.PatternRenderer || null,
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
        patternRenderer: window.PatternRenderer || null,
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
            if (data && data.outputType === "shader") {
                window.GridRenderer.loadFromStatelessGenomes(
                    data.genomes,
                    data.generation,
                    false,
                    data.outputType,
                    data.substrateId
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
    applyEventBindings(
        IDS,
        {
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
        },
        onId
    );
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
            getAdapter: function () {
                return window.SubstrateAdapters.getAdapter(
                    window.PopulationState.substrateId
                );
            },
        });
    }

    initGenealogyLoad(setGenealogyState);
    window.AnimationLoop.start();

    console.log("Eyecatcher Interactive Evolution ready!");
})();
