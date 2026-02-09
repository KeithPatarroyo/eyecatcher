/**
 * Eyecatcher app entry: state, grid/breed/save logic, and module wiring.
 * Load after all module scripts. Depends on: ApiClient, AnimationLoop, PatternRenderer,
 * ZoomSignals, PopulationUI, CommunityUI, NetworkVisualizer, Toast, initToolbarUI.
 */
(function () {
    "use strict";

    if (typeof vis === "undefined") {
        console.error(
            "ERROR: vis.js library not loaded! Network visualization will not work."
        );
    }

    var API_URL =
        window.location.origin && window.location.protocol.indexOf("http") === 0
            ? window.location.origin + "/api"
            : "http://localhost:5001/api";

    var currentPopulation = [];
    var currentGenomes = null;
    var currentGenerationNum = 0;
    var currentPopulationId = null;
    var currentBranchName = "main";
    // Persisted so multiple "Start Fresh" (across tabs) get distinct branches; cleared when user resets genealogy.
    function getGenealogyBranchCounter() {
        try {
            var v =
                typeof localStorage !== "undefined" &&
                localStorage.getItem("genealogy_branch_counter");
            return v != null ? parseInt(v, 10) : 1;
        } catch (_e) {
            return 1;
        }
    }
    function setGenealogyBranchCounter(n) {
        try {
            if (typeof localStorage !== "undefined")
                localStorage.setItem("genealogy_branch_counter", String(n));
        } catch (_e) {
            /* ignore */
        }
    }
    function syncCurrentPopulationIdToStorage() {
        try {
            if (typeof sessionStorage === "undefined") return;
            if (currentPopulationId != null) {
                sessionStorage.setItem(
                    "current_population_id",
                    String(currentPopulationId)
                );
            } else {
                sessionStorage.removeItem("current_population_id");
            }
        } catch (_e) {
            /* ignore */
        }
    }
    function getColorMode() {
        var el = document.querySelector('input[name="colorMode"]:checked');
        return el && el.value === "rgb" ? "rgb" : "hsv";
    }
    var patterns = new Map();
    var fullscreenPatternData = null;

    function openFullscreen(id) {
        var pattern =
            currentPopulation &&
            currentPopulation.find(function (p) {
                return p.id === id;
            });
        if (!pattern || !pattern.shader) return;
        closeFullscreen();
        var modal = document.getElementById("fullscreen-modal");
        var wrap = document.getElementById("fullscreen-canvas-wrap");
        if (!modal || !wrap) return;
        modal.hidden = false;
        wrap.innerHTML = "";
        var patternRef = pattern;
        requestAnimationFrame(function () {
            if (modal.hidden) return;
            var size = Math.min(
                wrap.clientWidth || 800,
                wrap.clientHeight || 800,
                1024
            );
            if (size < 64) size = 800;
            var canvas = document.createElement("canvas");
            canvas.width = size;
            canvas.height = size;
            wrap.appendChild(canvas);
            var patternData = setupPattern(canvas, patternRef.shader);
            if (!patternData) {
                wrap.innerHTML = "";
                modal.hidden = true;
                return;
            }
            fullscreenPatternData = {
                canvas: canvas,
                gl: patternData.gl,
                program: patternData.program,
                positionBuffer: patternData.positionBuffer,
            };
        });
    }

    function closeFullscreen() {
        fullscreenPatternData = null;
        var modal = document.getElementById("fullscreen-modal");
        var wrap = document.getElementById("fullscreen-canvas-wrap");
        if (wrap) wrap.innerHTML = "";
        if (modal) modal.hidden = true;
    }

    function setupPattern(canvas, shaderCode) {
        return (
            window.PatternRenderer &&
            window.PatternRenderer.setupPattern(canvas, shaderCode)
        );
    }

    function renderPattern(patternData, time, mouseSpd, mouseDist, inact) {
        if (window.PatternRenderer && window.ZoomSignals) {
            window.PatternRenderer.renderPattern(
                patternData,
                time,
                mouseSpd,
                mouseDist,
                inact,
                window.ZoomSignals.signalState
            );
        }
    }

    function showGridError(message, showRetry) {
        var grid = document.getElementById("grid");
        grid.innerHTML =
            '<div class="grid-error">' +
            '<div style="color:var(--color-danger);font-weight:600;">Could not load CPPN patterns</div>' +
            '<div style="margin-top:8px;">' +
            message +
            "</div>" +
            '<div style="margin-top:12px;font-size:13px;color:var(--color-text-secondary);">Start the server: <code>python server.py</code><br>Then open <a href="http://localhost:5001" style="color:var(--color-primary);">http://localhost:5001</a></div>' +
            (showRetry
                ? '<button type="button" class="retry-btn" id="grid-retry-btn">New random population</button>'
                : "") +
            "</div>";
        document.getElementById("loading").style.display = "none";
        if (showRetry) {
            document.getElementById("grid-retry-btn").onclick = function () {
                window.PopulationUI.startNewRandomPopulation();
            };
        }
    }

    function renderGridFromPopulation(population) {
        document.getElementById("grid").innerHTML = "";
        patterns.clear();
        var grid = document.getElementById("grid");
        population.forEach(function (pattern) {
            var result = window.PatternRenderer.createPatternCard({
                pattern: pattern,
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
                    if (typeof window.EyecatcherDebug !== "undefined")
                        window.EyecatcherDebug.setHoveredPatternId(id);
                },
                onMouseLeave: function (id) {
                    if (
                        typeof window.EyecatcherDebug !== "undefined" &&
                        window.EyecatcherDebug.getHoveredPatternId() === id
                    ) {
                        window.EyecatcherDebug.setHoveredPatternId(null);
                    }
                },
            });
            grid.appendChild(result.card);
            if (result.patternData) {
                patterns.set(pattern.id, {
                    canvas: result.canvas,
                    gl: result.patternData.gl,
                    program: result.patternData.program,
                    positionBuffer: result.patternData.positionBuffer,
                    clicks: pattern.clicks !== undefined ? pattern.clicks : 0,
                });
            }
        });
        updateStats();
    }

    function loadFromStatelessGenomes(genomes, generationNum, saveToGenealogy) {
        if (!genomes || !genomes.length) return Promise.resolve();
        document.getElementById("loading").style.display = "block";
        document.getElementById("grid").innerHTML = "";
        patterns.clear();
        return window.ApiClient.compile(genomes, getColorMode())
            .then(function (compData) {
                currentGenomes = genomes;
                currentGenerationNum = generationNum;
                currentPopulation = compData.shaders || [];
                document.getElementById("gen-num").textContent = currentGenerationNum;
                renderGridFromPopulation(currentPopulation);
                if (saveToGenealogy) {
                    // New root (Start Fresh): always treat gen 0 as a new branch; clear parent so we don't attach to a loaded node.
                    var branchName = currentBranchName || "main";
                    var parentId = currentPopulationId;
                    if (generationNum === 0) {
                        parentId = null;
                        currentPopulationId = null;
                        syncCurrentPopulationIdToStorage();
                        var counter = getGenealogyBranchCounter();
                        branchName = counter === 1 ? "main" : "branch-" + counter;
                        setGenealogyBranchCounter(counter + 1);
                        currentBranchName = branchName;
                    }
                    var fitnessData = currentPopulation.map(function (p) {
                        var pat = patterns.get(p.id);
                        return pat ? pat.clicks || 0 : 0;
                    });
                    return fetch(API_URL + "/genealogy/save-population", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            genomes: genomes,
                            parent_id: parentId,
                            generation_num: generationNum,
                            branch_name: branchName,
                            description:
                                generationNum === 0
                                    ? "Random initial population"
                                    : "Generation " + generationNum,
                            user_id: "user",
                            fitness_data: fitnessData,
                        }),
                    })
                        .then(function (r) {
                            return r.json();
                        })
                        .then(function (data) {
                            if (data.population_id != null) {
                                currentPopulationId = data.population_id;
                                syncCurrentPopulationIdToStorage();
                            }
                        })
                        .catch(function (e) {
                            console.warn("Genealogy save failed:", e);
                        });
                }
            })
            .catch(function (e) {
                console.error(e);
                showGridError(e.message || "Failed to compile", true);
            })
            .then(function () {
                document.getElementById("loading").style.display = "none";
            });
    }

    function addToGrid(genomes) {
        if (!genomes || !genomes.length) return Promise.resolve();
        var nextKey = 0;
        patterns.forEach(function (_, id) {
            nextKey = Math.max(nextKey, id + 1);
        });
        var payload = genomes.map(function (g) {
            var copy = Object.assign({}, g);
            copy.key = nextKey++;
            copy.clicks = 0;
            return copy;
        });
        document.getElementById("loading").style.display = "block";
        return window.ApiClient.compile(payload, getColorMode())
            .then(function (compData) {
                var newShaders = compData.shaders || [];
                if (!currentGenomes) currentGenomes = [];
                if (!currentPopulation) currentPopulation = [];
                currentGenomes.push.apply(currentGenomes, genomes);
                currentPopulation.push.apply(currentPopulation, newShaders);
                var grid = document.getElementById("grid");
                newShaders.forEach(function (pattern) {
                    var result = window.PatternRenderer.createPatternCard({
                        pattern: pattern,
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
                            if (typeof window.EyecatcherDebug !== "undefined")
                                window.EyecatcherDebug.setHoveredPatternId(id);
                        },
                        onMouseLeave: function (id) {
                            if (
                                typeof window.EyecatcherDebug !== "undefined" &&
                                window.EyecatcherDebug.getHoveredPatternId() === id
                            ) {
                                window.EyecatcherDebug.setHoveredPatternId(null);
                            }
                        },
                    });
                    grid.appendChild(result.card);
                    if (result.patternData) {
                        patterns.set(pattern.id, {
                            canvas: result.canvas,
                            gl: result.patternData.gl,
                            program: result.patternData.program,
                            positionBuffer: result.patternData.positionBuffer,
                            clicks: pattern.clicks !== undefined ? pattern.clicks : 0,
                        });
                    }
                });
                updateStats();
            })
            .catch(function (e) {
                console.error(e);
                if (window.Toast)
                    window.Toast.show(
                        "Add failed",
                        e.message || "Failed to compile",
                        "error"
                    );
            })
            .then(function () {
                document.getElementById("loading").style.display = "none";
            });
    }

    function clickPattern(id, card) {
        var pattern = patterns.get(id);
        if (pattern) {
            pattern.clicks = (pattern.clicks || 0) + 1;
            var clickCount = card.querySelector(".click-count");
            clickCount.textContent = pattern.clicks;
            clickCount.classList.remove("zero");
            card.classList.add("selected");
            updateStats();
        }
    }

    function unclickPattern(id, card) {
        var pattern = patterns.get(id);
        if (pattern && pattern.clicks > 0) {
            pattern.clicks--;
            var clickCount = card.querySelector(".click-count");
            clickCount.textContent = pattern.clicks;
            if (pattern.clicks === 0) {
                clickCount.classList.add("zero");
                card.classList.remove("selected");
            }
            updateStats();
        }
    }

    function setBreedButtonDisabled(disabled) {
        var el = document.getElementById("breed-btn");
        if (disabled) {
            el.classList.add("disabled");
            el.setAttribute("aria-disabled", "true");
        } else {
            el.classList.remove("disabled");
            el.setAttribute("aria-disabled", "false");
        }
    }

    function breedGeneration() {
        if (document.getElementById("breed-btn").classList.contains("disabled")) return;
        setBreedButtonDisabled(true);
        document.getElementById("loading").style.display = "block";

        if (!currentGenomes) {
            if (window.Toast)
                window.Toast.error(
                    "No population loaded. Start with New random population or Load population."
                );
            document.getElementById("loading").style.display = "none";
            setBreedButtonDisabled(false);
            updateStats();
            return;
        }

        var parents = currentPopulation
            .map(function (p, idx) {
                var pat = patterns.get(p.id);
                var clicks = pat ? pat.clicks : 0;
                var genome = currentGenomes[idx];
                return genome ? { genome: genome, clicks: clicks } : null;
            })
            .filter(Boolean)
            .filter(function (p) {
                return p.clicks > 0;
            });

        if (!parents.length) {
            if (window.Toast)
                window.Toast.error(
                    "Select at least one pattern (click on it) before breeding."
                );
            document.getElementById("loading").style.display = "none";
            updateStats();
            setBreedButtonDisabled(false);
            return;
        }

        var sizeInput = document.getElementById("population-size-input");
        var populationSize = Math.max(
            2,
            Math.min(50, parseInt(sizeInput && sizeInput.value, 10) || 12)
        );

        // Breed endpoint auto-saves to genealogy when parent_population_id is sent; do not pass saveToGenealogy.
        window.ApiClient.breed(parents, populationSize, {
            parentPopulationId: currentPopulationId,
            generationNum: currentGenerationNum + 1,
            branchName: currentBranchName || "main",
        })
            .then(function (data) {
                if (data.population_id != null) {
                    currentPopulationId = data.population_id;
                    syncCurrentPopulationIdToStorage();
                }
                return loadFromStatelessGenomes(
                    data.children,
                    currentGenerationNum + 1
                );
            })
            .catch(function (e) {
                console.error("Error breeding:", e);
                if (window.Toast)
                    window.Toast.error("Breed failed: " + (e.message || String(e)));
                document.getElementById("loading").style.display = "none";
                updateStats();
                setBreedButtonDisabled(false);
            });
    }

    function getCurrentGenomesForSave() {
        if (currentGenomes && currentGenomes.length) {
            return { genomes: currentGenomes, generation: currentGenerationNum };
        }
        return null;
    }

    function savePattern(id, buttonEl) {
        if (!currentGenomes || !currentGenomes.length) {
            if (window.Toast)
                window.Toast.show(
                    "Cannot save",
                    "No pattern data. Start with New random population or Load population.",
                    "error"
                );
            return;
        }
        var idx = currentPopulation.findIndex(function (p) {
            return p.id === id;
        });
        var genome = idx >= 0 && currentGenomes[idx] ? currentGenomes[idx] : null;
        if (!genome) {
            if (window.Toast)
                window.Toast.show(
                    "Cannot save",
                    "Could not get pattern data.",
                    "error"
                );
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
                    if (window.Toast)
                        window.Toast.show(
                            "Pattern saved!",
                            "Zip downloaded to your computer.",
                            "success",
                            { duration: 5000 }
                        );
                } else {
                    if (window.Toast)
                        window.Toast.show(
                            "Pattern saved!",
                            "No download in response.",
                            "success"
                        );
                }
            })
            .catch(function (error) {
                console.error("Error saving:", error);
                if (window.Toast)
                    window.Toast.show(
                        "Save failed",
                        error.message || "Network error",
                        "error"
                    );
            })
            .then(function () {
                if (buttonEl) {
                    buttonEl.textContent = originalText;
                    buttonEl.classList.remove("saving");
                }
            });
    }

    function getGenomeForPattern(patternId) {
        if (!currentGenomes) return Promise.resolve(null);
        var idx = currentPopulation.findIndex(function (p) {
            return p.id === patternId;
        });
        var genome = idx >= 0 && currentGenomes[idx] ? currentGenomes[idx] : null;
        return Promise.resolve(genome);
    }

    function updateStats() {
        var totalClicks = 0;
        patterns.forEach(function (p) {
            totalClicks += p.clicks || 0;
        });
        var hasFitness = false;
        patterns.forEach(function (p) {
            if (p.clicks > 0) hasFitness = true;
        });
        document.getElementById("total-clicks").textContent = totalClicks;
        setBreedButtonDisabled(!hasFitness);
    }

    function updatePatternShader(individualId, newShader) {
        var pattern = patterns.get(individualId);
        if (pattern && window.PatternRenderer) {
            var newPatternData = window.PatternRenderer.setupPattern(
                pattern.canvas,
                newShader
            );
            if (newPatternData) {
                var clicks = pattern.clicks || 0;
                patterns.set(individualId, {
                    canvas: pattern.canvas,
                    gl: newPatternData.gl,
                    program: newPatternData.program,
                    positionBuffer: newPatternData.positionBuffer,
                    clicks: clicks,
                });
            }
        }
    }

    function onRoleButtonKeydown(e, onClick) {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onClick();
        }
    }

    // --- Init ---
    window.ApiClient.init(API_URL);

    window.AnimationLoop.init({
        getPatterns: function () {
            var list = Array.from(patterns.values());
            if (fullscreenPatternData) list.push(fullscreenPatternData);
            return list;
        },
        renderPattern: renderPattern,
    });

    window.PopulationUI.init({
        apiUrl: API_URL,
        loadFromStatelessGenomes: loadFromStatelessGenomes,
        addToGrid: addToGrid,
        getCurrentGenomesForSave: getCurrentGenomesForSave,
    });

    window.CommunityUI.init({
        apiUrl: API_URL,
        loadFromStatelessGenomes: loadFromStatelessGenomes,
        addToGrid: addToGrid,
        getGenomeForPattern: getGenomeForPattern,
        setupPattern: setupPattern,
        renderPattern: renderPattern,
    });

    window.NetworkVisualizer.init({
        apiUrl: API_URL,
        getGenomeForPattern: getGenomeForPattern,
        updatePatternShader: updatePatternShader,
        getCurrentPopulation: function () {
            return currentPopulation;
        },
        onGenomeUpdated: function (individualId, idx, genome) {
            if (currentGenomes && idx >= 0) currentGenomes[idx] = genome;
        },
    });

    if (window.initToolbarUI) window.initToolbarUI();

    document.querySelectorAll('input[name="colorMode"]').forEach(function (radio) {
        radio.addEventListener("change", function () {
            if (currentGenomes && currentGenomes.length) {
                loadFromStatelessGenomes(currentGenomes, currentGenerationNum, false);
            }
        });
    });

    var fullscreenCloseBtn = document.getElementById("fullscreen-close");
    var fullscreenBackdrop = document.getElementById("fullscreen-backdrop");
    if (fullscreenCloseBtn)
        fullscreenCloseBtn.addEventListener("click", closeFullscreen);
    if (fullscreenBackdrop)
        fullscreenBackdrop.addEventListener("click", closeFullscreen);
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && fullscreenPatternData) closeFullscreen();
    });

    var breedBtnEl = document.getElementById("breed-btn");
    if (breedBtnEl) {
        breedBtnEl.addEventListener("click", breedGeneration);
        breedBtnEl.addEventListener("keydown", function (e) {
            onRoleButtonKeydown(e, breedGeneration);
        });
    }

    var loadModalClose = document.getElementById("load-modal-close");
    if (loadModalClose)
        loadModalClose.addEventListener("click", function () {
            document.getElementById("load-list-modal").classList.remove("show");
        });
    document
        .getElementById("community-submit-do")
        .addEventListener("click", window.CommunityUI.submitCommunityForm);
    document
        .getElementById("community-submit-cancel")
        .addEventListener("click", window.CommunityUI.closeSubmitCommunityModal);
    document
        .getElementById("community-list-close")
        .addEventListener("click", function () {
            document.getElementById("community-list-modal").classList.remove("show");
        });
    document
        .getElementById("community-load-selected-btn")
        .addEventListener("click", window.CommunityUI.onCommunityLoadSelected);
    document
        .getElementById("community-load-12-btn")
        .addEventListener("click", window.CommunityUI.onCommunityLoad12);
    document
        .getElementById("community-select-all-btn")
        .addEventListener("click", window.CommunityUI.onCommunitySelectAll);
    document
        .getElementById("community-deselect-all-btn")
        .addEventListener("click", window.CommunityUI.onCommunityDeselectAll);
    var newFromCommunityBtn = document.getElementById("new-from-community-btn");
    if (newFromCommunityBtn) {
        newFromCommunityBtn.addEventListener(
            "click",
            window.CommunityUI.onNewFromCommunityClick
        );
        newFromCommunityBtn.addEventListener("keydown", function (e) {
            onRoleButtonKeydown(e, window.CommunityUI.onNewFromCommunityClick);
        });
    }
    document
        .getElementById("admin-key-submit")
        .addEventListener("click", window.CommunityUI.submitAdminKey);
    document
        .getElementById("admin-modal-cancel")
        .addEventListener("click", window.CommunityUI.closeAdminModal);
    document
        .getElementById("admin-list-close")
        .addEventListener("click", window.CommunityUI.closeAdminModal);
    document
        .getElementById("admin-key-input")
        .addEventListener("keydown", function (e) {
            if (e.key === "Enter") window.CommunityUI.submitAdminKey();
        });
    var saveCurrentBtn = document.getElementById("save-current-btn");
    if (saveCurrentBtn)
        saveCurrentBtn.addEventListener(
            "click",
            window.PopulationUI.onSaveCurrentClick
        );
    var importBtn = document.getElementById("import-btn");
    var importFile = document.getElementById("import-file");
    if (importBtn && importFile)
        importBtn.addEventListener("click", window.PopulationUI.onImportClick);
    if (importFile) {
        importFile.addEventListener("change", function (e) {
            var file = e.target.files && e.target.files[0];
            e.target.value = "";
            if (file && typeof window.PopulationUI.handleImportFile === "function") {
                window.PopulationUI.handleImportFile(file);
            }
        });
    }

    window.ZoomSignals.init();

    if (typeof window.EyecatcherDebug !== "undefined") {
        window.EyecatcherDebug.init({
            apiUrl: API_URL,
            getMouseDistance: window.AnimationLoop.getMouseDistance,
            getPatterns: function () {
                return patterns;
            },
            getSignalState: function () {
                return window.ZoomSignals.signalState;
            },
            getGenomeForPattern: getGenomeForPattern,
        });
    }

    // If we arrived from the genealogy viewer ("Load This Population"), restore that population
    // so the generation counter and branch are correct and evolving continues as a child of that node.
    var genealogyLoad = null;
    try {
        var raw =
            typeof localStorage !== "undefined" &&
            localStorage.getItem("genealogy_load");
        if (raw) {
            genealogyLoad = JSON.parse(raw);
            localStorage.removeItem("genealogy_load");
        }
    } catch (e) {
        console.warn("Genealogy load parse failed:", e);
    }
    if (genealogyLoad && genealogyLoad.genomes && genealogyLoad.genomes.length) {
        currentPopulationId =
            genealogyLoad.population_id != null ? genealogyLoad.population_id : null;
        currentBranchName = genealogyLoad.branch_name || "main";
        syncCurrentPopulationIdToStorage();
        var genNum =
            genealogyLoad.generation_num != null ? genealogyLoad.generation_num : 0;
        loadFromStatelessGenomes(genealogyLoad.genomes, genNum, false);
    } else {
        window.PopulationUI.startNewRandomPopulation();
    }
    window.AnimationLoop.start();

    console.log("Eyecatcher Interactive Evolution ready!");
})();
