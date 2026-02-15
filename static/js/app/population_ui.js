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

    class PopulationUI {
        constructor() {
            this._apiUrl = "";
            this._loadFromStatelessGenomes = null;
            this._addToGrid = null;
            this._getCurrentGenomesForSave = null;
        }

        init(options) {
            this._apiUrl = options.apiUrl || "";
            this._loadFromStatelessGenomes = options.loadFromStatelessGenomes;
            this._addToGrid = options.addToGrid;
            this._getCurrentGenomesForSave = options.getCurrentGenomesForSave;
        }

        async startNewRandomPopulation() {
            var self = this;
            try {
                await window.Utils.withLoading(async function () {
                    try {
                        sessionStorage.removeItem("current_population_data");
                        sessionStorage.removeItem("current_population_id");
                        sessionStorage.removeItem("has_population");
                    } catch (_e) {
                        /* ignore */
                    }
                    var size =
                        (window.EvolutionConfig &&
                            window.EvolutionConfig.DEFAULT_POPULATION_SIZE) ||
                        12;
                    var d = await window.ApiClient.randomPopulation(size);
                    if (self._loadFromStatelessGenomes) {
                        await self._loadFromStatelessGenomes(
                            d.individuals || [],
                            0,
                            true,
                            d.representation_id
                        );
                    }
                });
            } catch (error) {
                console.error("Error starting random population:", error);
                Toast.error("Error: " + (error.message || String(error)));
            }
        }

        async onLoadSavedClick() {
            try {
                if (typeof EyecatcherStorage === "undefined") {
                    if (window.Toast)
                        Toast.error(
                            "Storage not loaded. Check that storage.js is served."
                        );
                    else alert("Storage not loaded. Check that storage.js is served.");
                    return;
                }
                await EyecatcherStorage.init();
                var list = await EyecatcherStorage.listPopulations();
                var ul = document.getElementById("load-list");
                if (!ul) return;
                ul.innerHTML = "";
                if (!list.length) {
                    ul.appendChild(
                        Utils.createListEmptyEl("li", "No saved populations")
                    );
                } else {
                    var self = this;
                    list.forEach(function (pop) {
                        var li = document.createElement("li");
                        li.textContent =
                            (pop.name || "Unnamed") +
                            " (gen " +
                            (pop.generation || 0) +
                            ", " +
                            (pop.genomes || []).length +
                            " patterns)";
                        li.onclick = async function () {
                            document
                                .getElementById("load-list-modal")
                                .classList.remove("show");
                            if (self._loadFromStatelessGenomes) {
                                var r = window.RepresentationRegistry.resolve(pop);
                                await self._loadFromStatelessGenomes(
                                    pop.genomes || [],
                                    pop.generation || 0,
                                    false,
                                    r.representationId
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

        async onSaveCurrentClick() {
            if (typeof EyecatcherStorage === "undefined") {
                Toast.error("Storage not loaded.");
                return;
            }
            var data = this._getCurrentGenomesForSave
                ? await this._getCurrentGenomesForSave()
                : null;
            if (!data || !data.genomes.length) {
                Toast.error(
                    "No population to save. Start with New random population or Load Saved."
                );
                return;
            }
            var name = prompt(
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
                    data.representationId
                );
                Toast.show("Saved", "Population saved to browser storage.", "success");
            } catch (e) {
                Toast.error("Error: " + (e.message || e));
            }
        }

        onImportClick() {
            var input = document.getElementById("import-file");
            if (input) input.click();
        }

        async handleImportFile(file) {
            if (!file) return;
            var name = (file.name || "").toLowerCase();
            try {
                var genomes = [];
                if (name.endsWith(".zip")) {
                    if (typeof JSZip === "undefined") {
                        Toast.error(
                            "Import failed: JSZip not loaded. Check script for jszip.min.js."
                        );
                        return;
                    }
                    var zip = await JSZip.loadAsync(file);
                    var genomeFiles = Object.keys(zip.files).filter(function (n) {
                        return /^genome_.*\.json$/i.test(n);
                    });
                    if (!genomeFiles.length) {
                        Toast.error(
                            "No genome JSON found in zip (expected genome_*.json)."
                        );
                        return;
                    }
                    for (var i = 0; i < genomeFiles.length; i++) {
                        var entry = genomeFiles[i];
                        var text = await zip.files[entry].async("string");
                        var genome = JSON.parse(text);
                        var accepted =
                            genome &&
                            !!window.RepresentationRegistry.findAdapterByGenome(genome);
                        if (accepted) genomes.push(genome);
                    }
                } else {
                    var json = JSON.parse(await file.text());
                    genomes = json.individuals || json.genomes || [];
                    if (genomes.length && typeof EyecatcherStorage !== "undefined") {
                        await EyecatcherStorage.init();
                        var r = window.RepresentationRegistry.resolve({
                            genomes: genomes,
                        });
                        var importPayload = Object.assign({}, json, {
                            representationId:
                                json.representationId || r.representationId,
                        });
                        await EyecatcherStorage.importPopulation(importPayload);
                    }
                }
                if (!genomes.length) {
                    Toast.error("No genomes in file");
                    return;
                }
                var resolved = window.RepresentationRegistry.resolve({
                    genomes: genomes,
                });
                if (this._addToGrid) {
                    await this._addToGrid(genomes);
                }
            } catch (err) {
                Toast.error("Import failed: " + (err.message || err));
            }
        }
    }

    window.PopulationUI = new PopulationUI();
})();
