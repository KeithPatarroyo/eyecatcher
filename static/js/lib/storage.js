/**
 * Eyecatcher IndexedDB storage module.
 * Stores populations (genomes + generation) and settings for the stateless client.
 *
 * Database: "eyecatcher"
 * Object stores:
 *   - populations: { id, name, genomes, generation, created, modified }
 *   - settings: { key, value }
 */
const EyecatcherStorage = (function () {
    const DB_NAME = "eyecatcher";
    const DB_VERSION = 1;
    const POPULATIONS_STORE = "populations";
    const SETTINGS_STORE = "settings";

    let db = null;

    function open() {
        return new Promise((resolve, reject) => {
            if (db) {
                resolve(db);
                return;
            }
            const req = indexedDB.open(DB_NAME, DB_VERSION);
            req.onerror = () => reject(req.error);
            req.onsuccess = () => {
                db = req.result;
                resolve(db);
            };
            req.onupgradeneeded = (e) => {
                const database = e.target.result;
                if (!database.objectStoreNames.contains(POPULATIONS_STORE)) {
                    const pop = database.createObjectStore(POPULATIONS_STORE, {
                        keyPath: "id",
                        autoIncrement: true,
                    });
                    pop.createIndex("modified", "modified", { unique: false });
                }
                if (!database.objectStoreNames.contains(SETTINGS_STORE)) {
                    database.createObjectStore(SETTINGS_STORE, { keyPath: "key" });
                }
            };
        });
    }

    return {
        async init() {
            await open();
            return db;
        },

        async savePopulation(name, genomes, generation) {
            const database = await open();
            const now = new Date().toISOString();
            const record = {
                name: name || "Unnamed",
                genomes: genomes,
                generation: generation,
                created: now,
                modified: now,
            };
            return new Promise((resolve, reject) => {
                const tx = database.transaction(POPULATIONS_STORE, "readwrite");
                const store = tx.objectStore(POPULATIONS_STORE);
                const req = store.add(record);
                req.onsuccess = () => resolve(req.result);
                req.onerror = () => reject(req.error);
            });
        },

        async updatePopulation(id, name, genomes, generation) {
            const database = await open();
            const existing = await this.loadPopulation(id);
            if (!existing) return null;
            const record = {
                id: id,
                name: name != null ? name : existing.name,
                genomes: genomes != null ? genomes : existing.genomes,
                generation: generation != null ? generation : existing.generation,
                created: existing.created,
                modified: new Date().toISOString(),
            };
            return new Promise((resolve, reject) => {
                const tx = database.transaction(POPULATIONS_STORE, "readwrite");
                const store = tx.objectStore(POPULATIONS_STORE);
                const req = store.put(record);
                req.onsuccess = () => resolve(id);
                req.onerror = () => reject(req.error);
            });
        },

        async loadPopulation(id) {
            const database = await open();
            return new Promise((resolve, reject) => {
                const tx = database.transaction(POPULATIONS_STORE, "readonly");
                const req = tx.objectStore(POPULATIONS_STORE).get(id);
                req.onsuccess = () => resolve(req.result || null);
                req.onerror = () => reject(req.error);
            });
        },

        async listPopulations() {
            const database = await open();
            return new Promise((resolve, reject) => {
                const tx = database.transaction(POPULATIONS_STORE, "readonly");
                const req = tx.objectStore(POPULATIONS_STORE).getAll();
                req.onsuccess = () => {
                    const list = (req.result || []).sort(
                        (a, b) => new Date(b.modified) - new Date(a.modified)
                    );
                    resolve(list);
                };
                req.onerror = () => reject(req.error);
            });
        },

        async deletePopulation(id) {
            const database = await open();
            return new Promise((resolve, reject) => {
                const tx = database.transaction(POPULATIONS_STORE, "readwrite");
                const req = tx.objectStore(POPULATIONS_STORE).delete(id);
                req.onsuccess = () => resolve();
                req.onerror = () => reject(req.error);
            });
        },

        async exportPopulation(id) {
            const pop = await this.loadPopulation(id);
            if (!pop) return null;
            return {
                name: pop.name,
                generation: pop.generation,
                genomes: pop.genomes,
                exportedAt: new Date().toISOString(),
            };
        },

        async importPopulation(json) {
            const name = json.name || "Imported";
            const genomes = json.genomes || [];
            const generation = json.generation != null ? json.generation : 0;
            if (!genomes.length) return null;
            const id = await this.savePopulation(name, genomes, generation);
            return { id, name, generation, count: genomes.length };
        },

        async getSetting(key) {
            const database = await open();
            return new Promise((resolve, reject) => {
                const tx = database.transaction(SETTINGS_STORE, "readonly");
                const req = tx.objectStore(SETTINGS_STORE).get(key);
                req.onsuccess = () =>
                    resolve(req.result ? req.result.value : undefined);
                req.onerror = () => reject(req.error);
            });
        },

        async setSetting(key, value) {
            const database = await open();
            return new Promise((resolve, reject) => {
                const tx = database.transaction(SETTINGS_STORE, "readwrite");
                const req = tx.objectStore(SETTINGS_STORE).put({ key, value });
                req.onsuccess = () => resolve();
                req.onerror = () => reject(req.error);
            });
        },
    };
})();

// Ensure global in browser (works even if script runs in strict mode or before DOM)
if (typeof window !== "undefined") {
    window.EyecatcherStorage = EyecatcherStorage;
}
if (typeof module !== "undefined" && module.exports) {
    module.exports = EyecatcherStorage;
}
