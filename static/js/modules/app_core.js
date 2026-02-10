/**
 * Eyecatcher app core: state, grid/breed/save logic. No DOM wiring.
 * Load after: utils, api_client, pattern_renderer, toast, zoom_signals (optional).
 * Call AppCore.init(apiUrl, ids) before using; then app.js wires DOM and passes AppCore to PopulationUI, CommunityUI, NetworkVisualizer, AnimationLoop.
 */
(function () {
    "use strict";

    var API_URL;
    var IDS;
    var FULLSCREEN_CANVAS_MAX = 1024;
    var FULLSCREEN_CANVAS_DEFAULT = 800;
    var FULLSCREEN_CANVAS_MIN = 64;

    var currentPopulation = [];
    var currentGenomes = null;
    var currentGenerationNum = 0;
    var currentPopulationId = null;
    var currentBranchName = "main";
    var patterns = new Map();
    var fullscreenPatternData = null;

    function getGenealogyBranchCounter() {
        var v = Utils.safeGetItem(
            typeof localStorage !== "undefined" ? localStorage : null,
            "genealogy_branch_counter",
            "1"
        );
        return parseInt(v, 10) || 1;
    }
    function setGenealogyBranchCounter(n) {
        Utils.safeSetItem(
            typeof localStorage !== "undefined" ? localStorage : null,
            "genealogy_branch_counter",
            String(n)
        );
    }
    function syncCurrentPopulationIdToStorage() {
        if (typeof sessionStorage === "undefined") return;
        if (currentPopulationId != null) {
            Utils.safeSetItem(
                sessionStorage,
                "current_population_id",
                String(currentPopulationId)
            );
        } else {
            try {
                sessionStorage.removeItem("current_population_id");
            } catch (_e) {
                /* ignore */
            }
        }
    }
    function getColorMode() {
        var el = document.querySelector('input[name="colorMode"]:checked');
        return el && el.value === "rgb" ? "rgb" : "hsv";
    }

    function getGrid() {
        return document.getElementById(IDS.grid);
    }
    function clearGrid() {
        var g = getGrid();
        if (g) g.innerHTML = "";
    }

    function openFullscreen(id) {
        var pattern =
            currentPopulation &&
            currentPopulation.find(function (p) {
                return p.id === id;
            });
        if (!pattern || !pattern.shader) return;
        closeFullscreen();
        var modal = document.getElementById(IDS.fullscreenModal);
        var wrap = document.getElementById(IDS.fullscreenCanvasWrap);
        if (!modal || !wrap) return;
        modal.hidden = false;
        wrap.innerHTML = "";
        var patternRef = pattern;
        requestAnimationFrame(function () {
            if (modal.hidden) return;
            var size = Math.min(
                wrap.clientWidth || FULLSCREEN_CANVAS_DEFAULT,
                wrap.clientHeight || FULLSCREEN_CANVAS_DEFAULT,
                FULLSCREEN_CANVAS_MAX
            );
            if (size < FULLSCREEN_CANVAS_MIN) size = FULLSCREEN_CANVAS_DEFAULT;
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
        var modal = document.getElementById(IDS.fullscreenModal);
        var wrap = document.getElementById(IDS.fullscreenCanvasWrap);
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
        var grid = getGrid();
        var tpl = document.getElementById(IDS.gridErrorTpl);
        if (!tpl || !tpl.content) {
            clearGrid();
            grid = getGrid();
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
        clearGrid();
        grid = getGrid();
        if (grid) grid.appendChild(fragment);
        showLoading(false);
        if (showRetry) {
            var retryEl = document.getElementById(IDS.gridRetryBtn);
            if (retryEl)
                retryEl.onclick = function () {
                    window.PopulationUI.startNewRandomPopulation();
                };
        }
    }

    function patternCardCallbacks(pattern) {
        return {
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
        };
    }

    function renderGridFromPopulation(population) {
        clearGrid();
        patterns.clear();
        var grid = getGrid();
        population.forEach(function (pattern) {
            var result = window.PatternRenderer.createPatternCard(
                patternCardCallbacks(pattern)
            );
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

    async function loadFromStatelessGenomes(genomes, generationNum, saveToGenealogy) {
        if (!genomes || !genomes.length) return;
        showLoading(true);
        clearGrid();
        patterns.clear();
        try {
            var compData = await window.ApiClient.compile(genomes, getColorMode());
            currentGenomes = genomes;
            currentGenerationNum = generationNum;
            currentPopulation = compData.shaders || [];
            var genEl = document.getElementById(IDS.genNum);
            if (genEl) genEl.textContent = currentGenerationNum;
            renderGridFromPopulation(currentPopulation);
            if (saveToGenealogy) {
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
                try {
                    var data = await window.ApiClient.apiFetch(
                        API_URL + "/genealogy/save-population",
                        {
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
                        },
                        "Save failed"
                    );
                    if (data.population_id != null) {
                        currentPopulationId = data.population_id;
                        syncCurrentPopulationIdToStorage();
                    }
                } catch (e) {
                    console.warn("Genealogy save failed:", e);
                }
            }
        } catch (e) {
            console.error(e);
            showGridError(e.message || "Failed to compile", true);
        } finally {
            showLoading(false);
        }
    }

    async function addToGrid(genomes) {
        if (!genomes || !genomes.length) return;
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
        showLoading(true);
        try {
            var compData = await window.ApiClient.compile(payload, getColorMode());
            var newShaders = compData.shaders || [];
            if (!currentGenomes) currentGenomes = [];
            if (!currentPopulation) currentPopulation = [];
            currentGenomes.push.apply(currentGenomes, genomes);
            currentPopulation.push.apply(currentPopulation, newShaders);
            var grid = getGrid();
            newShaders.forEach(function (pattern) {
                var result = window.PatternRenderer.createPatternCard(
                    patternCardCallbacks(pattern)
                );
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
        } catch (e) {
            console.error(e);
            if (window.Toast)
                window.Toast.show(
                    "Add failed",
                    e.message || "Failed to compile",
                    "error"
                );
        } finally {
            showLoading(false);
        }
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
        var el = document.getElementById(IDS.breedBtn);
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

    function breedGeneration() {
        var breedEl = document.getElementById(IDS.breedBtn);
        if (breedEl && breedEl.classList.contains("disabled")) return;
        setBreedButtonDisabled(true);
        showLoading(true);

        if (!currentGenomes) {
            if (window.Toast)
                window.Toast.error(
                    "No population loaded. Start with New random population or Load population."
                );
            showLoading(false);
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
            showLoading(false);
            updateStats();
            setBreedButtonDisabled(false);
            return;
        }

        var sizeInput = document.getElementById(IDS.populationSizeInput);
        var populationSize = Math.max(
            2,
            Math.min(50, parseInt(sizeInput && sizeInput.value, 10) || 12)
        );

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
                showLoading(false);
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
        var totalEl = document.getElementById(IDS.totalClicks);
        if (totalEl) totalEl.textContent = totalClicks;
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

    function getPatterns() {
        var list = Array.from(patterns.values());
        if (fullscreenPatternData) list.push(fullscreenPatternData);
        return list;
    }

    function getCurrentPopulation() {
        return currentPopulation;
    }

    function onGenomeUpdated(individualId, idx, genome) {
        if (currentGenomes && idx >= 0) currentGenomes[idx] = genome;
    }

    function init(apiUrl, ids) {
        API_URL = apiUrl;
        IDS = ids;
    }

    function setGenealogyState(populationId, branchName) {
        currentPopulationId = populationId;
        currentBranchName = branchName || "main";
        syncCurrentPopulationIdToStorage();
    }

    window.AppCore = {
        init: init,
        setGenealogyState: setGenealogyState,
        loadFromStatelessGenomes: loadFromStatelessGenomes,
        addToGrid: addToGrid,
        getCurrentGenomesForSave: getCurrentGenomesForSave,
        getGenomeForPattern: getGenomeForPattern,
        updatePatternShader: updatePatternShader,
        setupPattern: setupPattern,
        renderPattern: renderPattern,
        openFullscreen: openFullscreen,
        closeFullscreen: closeFullscreen,
        breedGeneration: breedGeneration,
        savePattern: savePattern,
        getPatterns: getPatterns,
        getCurrentPopulation: getCurrentPopulation,
        onGenomeUpdated: onGenomeUpdated,
        getPatternsMap: function () {
            return patterns;
        },
    };
})();
