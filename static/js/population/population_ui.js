/* global EyecatcherStorage: readonly */
/**
 * PopulationUI: save/load/import populations (IndexedDB) + start random population.
 * Depends on: EyecatcherStorage, RepresentationRegistry, EvolutionConfig.
 */
import Toast from "../lib/toast.js";
import Utils from "../lib/utils.js";
import api from "../lib/api_client.js";
import DOM from "../lib/dom.js";
import RepresentationRegistry from "../representation/representation_registry.js";
import { getConfig } from "../evolution/experiment_config.js";

const toast = (title, message, type = "info", opts) =>
    Toast.show(title, message, type, opts);

const ensureStorage = async () => {
    if (typeof EyecatcherStorage === "undefined") {
        toast("Storage missing", "storage.js not loaded or not served.", "error");
        return null;
    }
    await EyecatcherStorage.init();
    return EyecatcherStorage;
};

const clearSessionPopulationFlags = () => {
    try {
        sessionStorage.removeItem("current_population_data");
        sessionStorage.removeItem("current_population_id");
        sessionStorage.removeItem("has_population");
    } catch {
        /* ignore */
    }
};

const getGenomesFromZip = async (file) => {
    if (typeof JSZip === "undefined") {
        toast("Import failed", "JSZip not loaded (missing jszip.min.js).", "error");
        return [];
    }

    const zip = await JSZip.loadAsync(file);
    const genomeFiles = Object.keys(zip.files).filter((n) =>
        /^genome_.*\.json$/i.test(n)
    );
    if (!genomeFiles.length) {
        toast(
            "Import failed",
            "No genome JSON found in zip (expected genome_*.json).",
            "error"
        );
        return [];
    }

    const genomes = [];
    for (const entry of genomeFiles) {
        const text = await zip.files[entry].async("string");
        const genome = JSON.parse(text);
        if (genome && RepresentationRegistry?.findByGenome?.(genome))
            genomes.push(genome);
    }
    return genomes;
};

const getGenomesFromJsonFile = async (file) => {
    const json = JSON.parse(await file.text());
    const genomes = json.individuals || json.genomes || [];
    return { json, genomes };
};

class PopulationUI {
    constructor() {
        this._apiUrl = "";
        this._loadFromStatelessGenomes = null;
        this._addToGrid = null;
        this._getCurrentGenomesForSave = null;
    }

    init({ apiUrl, loadFromStatelessGenomes, addToGrid, getCurrentGenomesForSave }) {
        this._apiUrl = apiUrl || "";
        this._loadFromStatelessGenomes = loadFromStatelessGenomes || null;
        this._addToGrid = addToGrid || null;
        this._getCurrentGenomesForSave = getCurrentGenomesForSave || null;
    }

    async startNewRandomPopulation() {
        try {
            await Utils.withLoading(async () => {
                clearSessionPopulationFlags();

                const size = getConfig()?.DEFAULT_POPULATION_SIZE || 12;
                const d = await api.randomPopulation(size);

                if (this._loadFromStatelessGenomes) {
                    await this._loadFromStatelessGenomes(
                        d.individuals || [],
                        0,
                        true,
                        d.representation_id
                    );
                }
            });
        } catch (e) {
            console.error("Error starting random population:", e);
            toast("Error", e?.message || String(e), "error");
        }
    }

    async onLoadSavedClick() {
        try {
            const storage = await ensureStorage();
            if (!storage) return;

            const list = await storage.listPopulations();
            const ul = DOM.byId("load-list");
            if (!ul) return;

            ul.innerHTML = "";

            if (!list.length) {
                ul.appendChild(Utils.createListEmptyEl("li", "No saved populations"));
            } else {
                for (const pop of list) {
                    const li = document.createElement("li");
                    const count = (pop.genomes || []).length;
                    li.textContent = `${pop.name || "Unnamed"} (gen ${pop.generation || 0}, ${count} patterns)`;

                    DOM.on(li, "click", async () => {
                        DOM.toggleClass(DOM.byId("load-list-modal"), "show", false);
                        if (!this._loadFromStatelessGenomes) return;

                        const r = RepresentationRegistry.resolve(pop);
                        await this._loadFromStatelessGenomes(
                            pop.genomes || [],
                            pop.generation || 0,
                            false,
                            r.representationId
                        );
                    });

                    ul.appendChild(li);
                }
            }

            DOM.toggleClass(DOM.byId("load-list-modal"), "show", true);
        } catch (e) {
            toast("Error", e?.message || String(e), "error");
        }
    }

    async onSaveCurrentClick() {
        const storage = await ensureStorage();
        if (!storage) return;

        const data = this._getCurrentGenomesForSave
            ? await this._getCurrentGenomesForSave()
            : null;
        if (!data?.genomes?.length) {
            toast(
                "Nothing to save",
                "No population to save. Start with New random population or Load Saved.",
                "error"
            );
            return;
        }

        const name = prompt(
            "Name this population:",
            `Session ${new Date().toLocaleDateString()}`
        );
        if (name == null) return;

        try {
            await storage.savePopulation(
                name.trim() || "Unnamed",
                data.genomes,
                data.generation,
                data.representationId
            );
            toast("Saved", "Population saved to browser storage.", "success");
        } catch (e) {
            toast("Error", e?.message || String(e), "error");
        }
    }

    onImportClick() {
        DOM.byId("import-file")?.click();
    }

    async handleImportFile(file) {
        if (!file) return;

        try {
            const lower = (file.name || "").toLowerCase();
            let genomes = [];
            let json = null;

            if (lower.endsWith(".zip")) {
                genomes = await getGenomesFromZip(file);
            } else {
                const parsed = await getGenomesFromJsonFile(file);
                json = parsed.json;
                genomes = parsed.genomes || [];
            }

            if (!Array.isArray(genomes) || genomes.length === 0) {
                toast("Import failed", "No genomes in file.", "error");
                return;
            }

            // Store JSON imports into IndexedDB when possible (nice for researcher workflows).
            if (json && typeof EyecatcherStorage !== "undefined") {
                const storage = await ensureStorage();
                if (storage) {
                    const r = RepresentationRegistry.resolve({ genomes });
                    await storage.importPopulation({
                        ...json,
                        representationId: json.representationId || r.representationId,
                    });
                }
            }

            // Add to current grid/state (delegated to PopulationLoader via injected callback)
            if (this._addToGrid) await this._addToGrid(genomes);
        } catch (e) {
            toast("Import failed", e?.message || String(e), "error");
        }
    }
}

const populationUI = new PopulationUI();
export default populationUI;
window.PopulationUI = populationUI;
