/* global EyecatcherStorage: readonly */
/**
 * Population UI Module for Eyecatcher
 *
 * Handles client-side storage interactions (IndexedDB via EyecatcherStorage)
 * and population save/load/export/import functionality.
 *
 * Dependencies:
 * - EyecatcherStorage (from storage.js)
 * - API_URL global
 * - loadFromStatelessGenomes function
 * - addToGrid function (append patterns to current grid)
 * - getCurrentGenomesForSave function (returns client-held genomes + generation, or null)
 */

(function () {
    "use strict";

    // Module state
    let _apiUrl = "";
    let _loadFromStatelessGenomes = null;
    let _addToGrid = null;
    let _getCurrentGenomesForSave = null;

    /**
     * Initialize the population UI module.
     * @param {Object} options
     * @param {string} options.apiUrl - Base API URL
     * @param {Function} options.loadFromStatelessGenomes - Function to load genomes into the grid (replace)
     * @param {Function} options.addToGrid - Function to append genomes to the current grid
     * @param {Function} options.getCurrentGenomesForSave - Function to get current genomes for saving
     */
    function init(options) {
        _apiUrl = options.apiUrl || "";
        _loadFromStatelessGenomes = options.loadFromStatelessGenomes;
        _addToGrid = options.addToGrid;
        _getCurrentGenomesForSave = options.getCurrentGenomesForSave;
    }

    /**
     * Start a new random population from the server.
     */
    async function startNewRandomPopulation() {
        showLoading(true);
        try {
            // Clear any existing session data when starting fresh
            try {
                sessionStorage.removeItem("current_population_data");
                sessionStorage.removeItem("current_population_id");
                sessionStorage.removeItem("has_population");
            } catch (_e) {
                /* ignore */
            }

            // Fallback must match EvolutionConfig; see evolution_config.js
            const size =
                (window.EvolutionConfig &&
                    window.EvolutionConfig.DEFAULT_POPULATION_SIZE) ||
                12;
            const d = await window.ApiClient.randomPopulation(size);
            if (_loadFromStatelessGenomes) {
                await _loadFromStatelessGenomes(
                    d.genomes || [],
                    0,
                    true,
                    d.output_type,
                    d.substrate_id
                );
            }
        } catch (error) {
            console.error("Error starting random population:", error);
            Toast.error("Error: " + (error.message || String(error)));
        } finally {
            showLoading(false);
        }
    }

    /**
     * Open the load saved populations modal.
     */
    async function onLoadSavedClick() {
        try {
            if (typeof EyecatcherStorage === "undefined") {
                if (window.Toast)
                    Toast.error("Storage not loaded. Check that storage.js is served.");
                else alert("Storage not loaded. Check that storage.js is served.");
                return;
            }
            await EyecatcherStorage.init();
            const list = await EyecatcherStorage.listPopulations();
            const ul = document.getElementById("load-list");
            if (!ul) return;
            ul.innerHTML = "";
            if (!list.length) {
                ul.appendChild(Utils.createListEmptyEl("li", "No saved populations"));
            } else {
                list.forEach((pop) => {
                    const li = document.createElement("li");
                    li.textContent =
                        (pop.name || "Unnamed") +
                        " (gen " +
                        (pop.generation || 0) +
                        ", " +
                        (pop.genomes || []).length +
                        " patterns)";
                    li.onclick = async () => {
                        document
                            .getElementById("load-list-modal")
                            .classList.remove("show");
                        if (_loadFromStatelessGenomes) {
                            var outputType;
                            var substrateId;
                            if (pop.substrateId != null) {
                                outputType =
                                    pop.substrateId === "ca" ? "grid" : "shader";
                                substrateId = pop.substrateId;
                            } else if (
                                window.SubstrateAdapters &&
                                window.SubstrateAdapters.resolveFromGenomes
                            ) {
                                var r = window.SubstrateAdapters.resolveFromGenomes(
                                    pop.genomes
                                );
                                outputType = r.outputType;
                                substrateId = r.substrateId;
                            } else {
                                outputType = "shader";
                                substrateId = "dual_cppn";
                            }
                            await _loadFromStatelessGenomes(
                                pop.genomes || [],
                                pop.generation || 0,
                                false,
                                outputType,
                                substrateId
                            );
                        }
                    };
                    ul.appendChild(li);
                });
            }
            document.getElementById("load-list-modal").classList.add("show");
        } catch (e) {
            Toast.error("Error: " + (e.message || e));
        }
    }

    /**
     * Save current population to IndexedDB.
     */
    async function onSaveCurrentClick() {
        if (typeof EyecatcherStorage === "undefined") {
            Toast.error("Storage not loaded.");
            return;
        }
        const data = _getCurrentGenomesForSave
            ? await _getCurrentGenomesForSave()
            : null;
        if (!data || !data.genomes.length) {
            Toast.error(
                "No population to save. Start with New random population or Load Saved."
            );
            return;
        }
        const name = prompt(
            "Name this population:",
            "Session " + new Date().toLocaleDateString()
        );
        if (name == null) return;
        try {
            await EyecatcherStorage.init();
            await EyecatcherStorage.savePopulation(
                name.trim() || "Unnamed",
                data.genomes,
                data.generation,
                data.substrateId
            );
            Toast.show("Saved", "Population saved to browser storage.", "success");
        } catch (e) {
            Toast.error("Error: " + (e.message || e));
        }
    }

    /**
     * Trigger file input for import.
     */
    function onImportClick() {
        const input = document.getElementById("import-file");
        if (input) input.click();
    }

    /**
     * Handle imported file (call this from the file input's change handler).
     * Supports .zip (saved pattern with genome_*.json) or .json (population with genomes array).
     * Adds patterns to the current grid without replacing.
     * @param {File} file - The imported file
     */
    async function handleImportFile(file) {
        if (!file) return;
        const name = (file.name || "").toLowerCase();
        try {
            let genomes = [];
            if (name.endsWith(".zip")) {
                if (typeof JSZip === "undefined") {
                    Toast.error(
                        "Import failed: JSZip not loaded. Check script for jszip.min.js."
                    );
                    return;
                }
                const zip = await JSZip.loadAsync(file);
                const genomeFiles = Object.keys(zip.files).filter((n) =>
                    /^genome_.*\.json$/i.test(n)
                );
                if (!genomeFiles.length) {
                    Toast.error(
                        "No genome JSON found in zip (expected genome_*.json)."
                    );
                    return;
                }
                for (const entry of genomeFiles) {
                    const text = await zip.files[entry].async("string");
                    const genome = JSON.parse(text);
                    var accepted =
                        genome &&
                        window.SubstrateAdapters &&
                        window.SubstrateAdapters.findAdapterByGenome &&
                        !!window.SubstrateAdapters.findAdapterByGenome(genome);
                    if (accepted) genomes.push(genome);
                }
            } else {
                const json = JSON.parse(await file.text());
                genomes = json.genomes || [];
                if (genomes.length && typeof EyecatcherStorage !== "undefined") {
                    await EyecatcherStorage.init();
                    var inferred = "dual_cppn";
                    if (
                        window.SubstrateAdapters &&
                        window.SubstrateAdapters.resolveFromGenomes
                    ) {
                        inferred =
                            window.SubstrateAdapters.resolveFromGenomes(
                                genomes
                            ).substrateId;
                    }
                    var importPayload = Object.assign({}, json, {
                        substrateId: json.substrateId || inferred,
                    });
                    await EyecatcherStorage.importPopulation(importPayload);
                }
            }
            if (!genomes.length) {
                Toast.error("No genomes in file");
                return;
            }
            var outputType = "shader";
            if (
                window.SubstrateAdapters &&
                window.SubstrateAdapters.resolveFromGenomes
            ) {
                var resolved = window.SubstrateAdapters.resolveFromGenomes(genomes);
                outputType = resolved.outputType;
            }
            if (_addToGrid) {
                await _addToGrid(genomes, outputType);
            }
        } catch (err) {
            Toast.error("Import failed: " + (err.message || err));
        }
    }

    window.PopulationUI = {
        init: init,
        startNewRandomPopulation: startNewRandomPopulation,
        onLoadSavedClick: onLoadSavedClick,
        onSaveCurrentClick: onSaveCurrentClick,
        onImportClick: onImportClick,
        handleImportFile: handleImportFile,
    };
})();
