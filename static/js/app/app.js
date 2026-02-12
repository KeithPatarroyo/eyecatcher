/**
 * Eyecatcher app entry: init and DOM wiring. State and coordinators live in
 * population_state, grid_renderer, fullscreen_modal, evolution_coordinator, genealogy_sync.
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

    function onRoleButtonKeydown(e, onClick) {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onClick();
        }
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
        var state = window.PopulationState.getState();
        var totalClicks = 0;
        var hasFitness = false;
        state.patterns.forEach(function (p) {
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
            if (typeof showLoading !== "undefined") showLoading(false);
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
        if (typeof showLoading !== "undefined") showLoading(false);
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
            onSave: savePattern,
            onFullscreen: openFullscreen,
            onClick: clickPattern,
            onUnclick: unclickPattern,
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

    function savePattern(id, buttonEl) {
        var state = window.PopulationState.getState();
        if (!state.currentGenomes || !state.currentGenomes.length) {
            if (window.Toast) {
                window.Toast.show(
                    "Cannot save",
                    "No pattern data. Start with New random population or Load population.",
                    "error"
                );
            }
            return;
        }
        var idx = state.currentPopulation.findIndex(function (p) {
            return p.id === id;
        });
        var genome =
            idx >= 0 && state.currentGenomes[idx] ? state.currentGenomes[idx] : null;
        if (!genome) {
            if (window.Toast) {
                window.Toast.show(
                    "Cannot save",
                    "Could not get pattern data.",
                    "error"
                );
            }
            return;
        }
        var originalText = buttonEl ? buttonEl.textContent : null;
        if (buttonEl) {
            buttonEl.textContent = "Compiling...";
            buttonEl.classList.add("saving");
        }
        window.ApiClient.save(id, genome)
            .then(function (data) {
                if (Array.isArray(data.downloads) && data.downloads.length) {
                    var file = data.downloads[0];
                    var blob = file.content_base64
                        ? window.Toast.base64ToBlob(file.content_base64, file.mime)
                        : new Blob([file.content], { type: file.mime });
                    window.Toast.triggerDownload(blob, file.filename);
                    if (window.Toast) {
                        window.Toast.show(
                            "Pattern saved!",
                            "Zip downloaded to your computer.",
                            "success",
                            { duration: 5000 }
                        );
                    }
                } else if (window.Toast) {
                    window.Toast.show(
                        "Pattern saved!",
                        "No download in response.",
                        "success"
                    );
                }
            })
            .catch(function (error) {
                console.error("Error saving:", error);
                if (window.Toast) {
                    window.Toast.show(
                        "Save failed",
                        error.message || "Network error",
                        "error"
                    );
                }
            })
            .then(function () {
                if (buttonEl) {
                    buttonEl.textContent = originalText;
                    buttonEl.classList.remove("saving");
                }
            });
    }

    function openFullscreen(id) {
        var state = window.PopulationState.getState();
        window.FullscreenModal.openFullscreen(id, state.currentPopulation, IDS);
    }

    function closeFullscreen() {
        window.FullscreenModal.closeFullscreen(IDS);
    }

    function clickPattern(id, card) {
        var state = window.PopulationState.getState();
        var pattern = state.patterns.get(id);
        if (pattern) {
            var clicks = (pattern.clicks || 0) + 1;
            window.PopulationState.dispatch({
                type: "SET_PATTERN_CLICKS",
                payload: { id: id, clicks: clicks },
            });
            var clickCount = card.querySelector(".click-count");
            if (clickCount) {
                clickCount.textContent = clicks;
                clickCount.classList.remove("zero");
            }
            card.classList.add("selected");
            updateStats();
        }
    }

    function unclickPattern(id, card) {
        var state = window.PopulationState.getState();
        var pattern = state.patterns.get(id);
        if (pattern && (pattern.clicks || 0) > 0) {
            var clicks = pattern.clicks - 1;
            window.PopulationState.dispatch({
                type: "SET_PATTERN_CLICKS",
                payload: { id: id, clicks: clicks },
            });
            var clickCount = card.querySelector(".click-count");
            if (clickCount) {
                clickCount.textContent = clicks;
                if (clicks === 0) {
                    clickCount.classList.add("zero");
                    card.classList.remove("selected");
                }
            }
            updateStats();
        }
    }

    function resolveAdapterAndOutput(outputType, substrateId, genomes) {
        var SubstrateAdapters = window.SubstrateAdapters;
        var adapter = null;
        if (substrateId && SubstrateAdapters && SubstrateAdapters.getAdapter) {
            adapter = SubstrateAdapters.getAdapter(substrateId);
        }
        if (
            !adapter &&
            genomes &&
            genomes.length &&
            SubstrateAdapters &&
            SubstrateAdapters.resolveFromGenomes
        ) {
            var resolved = SubstrateAdapters.resolveFromGenomes(genomes);
            adapter = SubstrateAdapters.getAdapter(resolved.substrateId);
        }
        if (!adapter && SubstrateAdapters && SubstrateAdapters.getAdapter) {
            adapter = SubstrateAdapters.getAdapter("dual_cppn");
        }
        var resolvedOutputType =
            (adapter && adapter.outputType) || outputType || "shader";
        var resolvedSubstrateId = (adapter && adapter.id) || substrateId || "dual_cppn";
        return {
            adapter: adapter,
            outputType: resolvedOutputType,
            substrateId: resolvedSubstrateId,
        };
    }

    function evolveGeneration() {
        var evolveEl = document.getElementById(IDS.evolveBtn);
        if (evolveEl && evolveEl.classList.contains("disabled")) return;
        setEvolveButtonDisabled(true);
        if (typeof showLoading !== "undefined") showLoading(true);
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
                if (window.Toast) {
                    window.Toast.error(
                        "Evolve failed: " + (err.message || String(err))
                    );
                }
                if (typeof showLoading !== "undefined") showLoading(false);
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
        var state = window.PopulationState.getState();
        if (state.currentGenomes && state.currentGenomes.length) {
            return {
                genomes: state.currentGenomes,
                generation: state.generationNum,
                substrateId: state.substrateId,
                outputType: state.outputType,
            };
        }
        return null;
    }

    function getGenomeForPattern(patternId) {
        var state = window.PopulationState.getState();
        if (!state.currentGenomes) return Promise.resolve(null);
        var idx = state.currentPopulation.findIndex(function (p) {
            return p.id === patternId;
        });
        var genome =
            idx >= 0 && state.currentGenomes[idx] ? state.currentGenomes[idx] : null;
        return Promise.resolve(genome);
    }

    function updatePatternShader(individualId, newShader) {
        var state = window.PopulationState.getState();
        var pattern = state.patterns.get(individualId);
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
        var state = window.PopulationState.getState();
        var list = Array.from(state.patterns.values());
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

    function getPatternsMap() {
        return window.PopulationState.getState().patterns;
    }

    window.PopulationState.init();
    window.ApiClient.init(API_URL);

    if (window.GridRenderer && window.GridRenderer.init) {
        window.GridRenderer.init({
            IDS: IDS,
            API_URL: API_URL,
            getGridCallbacks: getGridCallbacks,
            resolveAdapterAndOutput: resolveAdapterAndOutput,
            getColorMode: getColorMode,
            showLoading: function (show) {
                if (typeof showLoading !== "undefined") showLoading(show);
            },
            showGridError: showGridError,
            updateStats: updateStats,
        });
    }

    window.ApiClient.fetchConfig()
        .then(function (c) {
            if (window.EvolutionConfig && window.EvolutionConfig.mergeFromServer) {
                window.EvolutionConfig.mergeFromServer(c);
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
        loadFromStatelessGenomes: window.GridRenderer.loadFromStatelessGenomes,
        addToGrid: window.GridRenderer.addToGrid,
        getCurrentGenomesForSave: getCurrentGenomesForSave,
    });

    window.CommunityUI.init({
        apiUrl: API_URL,
        loadFromStatelessGenomes: window.GridRenderer.loadFromStatelessGenomes,
        addToGrid: window.GridRenderer.addToGrid,
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

    if (window.initToolbarUI) window.initToolbarUI();

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

    onId(IDS.fullscreenClose, function (el) {
        el.addEventListener("click", closeFullscreen);
    });
    onId(IDS.fullscreenBackdrop, function (el) {
        el.addEventListener("click", closeFullscreen);
    });
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") closeFullscreen();
    });

    onId(IDS.evolveBtn, function (el) {
        el.addEventListener("click", evolveGeneration);
        el.addEventListener("keydown", function (e) {
            onRoleButtonKeydown(e, evolveGeneration);
        });
    });

    onId(IDS.loadModalClose, function (el) {
        el.addEventListener("click", function () {
            var modal = document.getElementById(IDS.loadListModal);
            if (modal) modal.classList.remove("show");
        });
    });
    onId(IDS.communitySubmitDo, function (el) {
        el.addEventListener("click", window.CommunityUI.submitCommunityForm);
    });
    onId(IDS.communitySubmitCancel, function (el) {
        el.addEventListener("click", window.CommunityUI.closeSubmitCommunityModal);
    });
    onId(IDS.communityListClose, function (el) {
        el.addEventListener("click", function () {
            var modal = document.getElementById(IDS.communityListModal);
            if (modal) modal.classList.remove("show");
        });
    });
    onId(IDS.communityLoadSelectedBtn, function (el) {
        el.addEventListener("click", window.CommunityUI.onCommunityLoadSelected);
    });
    onId(IDS.communityLoad12Btn, function (el) {
        el.addEventListener("click", window.CommunityUI.onCommunityLoad12);
    });
    onId(IDS.communitySelectAllBtn, function (el) {
        el.addEventListener("click", window.CommunityUI.onCommunitySelectAll);
    });
    onId(IDS.communityDeselectAllBtn, function (el) {
        el.addEventListener("click", window.CommunityUI.onCommunityDeselectAll);
    });
    onId(IDS.newFromCommunityBtn, function (el) {
        el.addEventListener("click", window.CommunityUI.onNewFromCommunityClick);
        el.addEventListener("keydown", function (e) {
            onRoleButtonKeydown(e, window.CommunityUI.onNewFromCommunityClick);
        });
    });
    onId(IDS.adminKeySubmit, function (el) {
        el.addEventListener("click", window.CommunityUI.submitAdminKey);
    });
    onId(IDS.adminModalCancel, function (el) {
        el.addEventListener("click", window.CommunityUI.closeAdminModal);
    });
    onId(IDS.adminListClose, function (el) {
        el.addEventListener("click", window.CommunityUI.closeAdminModal);
    });
    onId(IDS.adminKeyInput, function (el) {
        el.addEventListener("keydown", function (e) {
            if (e.key === "Enter") window.CommunityUI.submitAdminKey();
        });
    });
    onId(IDS.saveCurrentBtn, function (el) {
        el.addEventListener("click", window.PopulationUI.onSaveCurrentClick);
    });
    onId(IDS.importBtn, function (el) {
        el.addEventListener("click", window.PopulationUI.onImportClick);
    });
    onId(IDS.importFile, function (el) {
        el.addEventListener("change", function (e) {
            var file = e.target.files && e.target.files[0];
            e.target.value = "";
            if (file && typeof window.PopulationUI.handleImportFile === "function") {
                window.PopulationUI.handleImportFile(file);
            }
        });
    });

    window.ViewerControls.init();

    if (typeof window.EyecatcherDebug !== "undefined") {
        window.EyecatcherDebug.init({
            apiUrl: API_URL,
            getMouseDistance: window.AnimationLoop.getMouseDistance,
            getPatterns: getPatternsMap,
            getSignalState: function () {
                return window.ViewerControls.signalState;
            },
            getGenomeForPattern: getGenomeForPattern,
        });
    }

    var genealogyLoad = null;
    var raw = Utils.safeGetItem(
        typeof localStorage !== "undefined" ? localStorage : null,
        "genealogy_load",
        null
    );
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
    if (genealogyLoad && genealogyLoad.genomes && genealogyLoad.genomes.length) {
        setGenealogyState(
            genealogyLoad.population_id != null ? genealogyLoad.population_id : null,
            genealogyLoad.branch_name || "main"
        );
        var genNum =
            genealogyLoad.generation_num != null ? genealogyLoad.generation_num : 0;
        var subId = genealogyLoad.substrate_id;
        var outType;
        if (subId != null) {
            outType = subId === "ca" ? "grid" : "shader";
        } else if (
            window.SubstrateAdapters &&
            window.SubstrateAdapters.resolveFromGenomes
        ) {
            var r = window.SubstrateAdapters.resolveFromGenomes(genealogyLoad.genomes);
            outType = r.outputType;
            subId = r.substrateId;
        } else {
            outType = "shader";
        }
        window.GridRenderer.loadFromStatelessGenomes(
            genealogyLoad.genomes,
            genNum,
            false,
            outType,
            subId
        );
    } else {
        window.PopulationUI.startNewRandomPopulation();
    }
    window.AnimationLoop.start();

    console.log("Eyecatcher Interactive Evolution ready!");
})();
