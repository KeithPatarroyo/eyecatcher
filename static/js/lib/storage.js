/**
 * Eyecatcher IndexedDB storage module.
 * Stores populations (genomes + generation) for the stateless client.
 *
 * Database: "eyecatcher"
 * Store: populations: { id, name, genomes, generation, representationId, created, modified }
 */
(() => {
    "use strict";

    const DB_NAME = "eyecatcher";
    const DB_VERSION = 1;
    const STORE = "populations";
    const INDEX_MODIFIED = "modified";

    let openPromise = null;

    const openDB = () => {
        if (openPromise) return openPromise;

        openPromise = new Promise((resolve, reject) => {
            const req = indexedDB.open(DB_NAME, DB_VERSION);

            req.onerror = () => reject(req.error);

            req.onupgradeneeded = (e) => {
                const db = e.target.result;

                if (!db.objectStoreNames.contains(STORE)) {
                    const store = db.createObjectStore(STORE, {
                        keyPath: "id",
                        autoIncrement: true,
                    });
                    store.createIndex(INDEX_MODIFIED, INDEX_MODIFIED, {
                        unique: false,
                    });
                } else {
                    // Future-proof: ensure index exists if version bumps later.
                    const tx = e.target.transaction;
                    const store = tx.objectStore(STORE);
                    if (!store.indexNames.contains(INDEX_MODIFIED)) {
                        store.createIndex(INDEX_MODIFIED, INDEX_MODIFIED, {
                            unique: false,
                        });
                    }
                }
            };

            req.onsuccess = () => resolve(req.result);
        });

        return openPromise;
    };

    const runStore = async (mode, fn) => {
        const db = await openDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(STORE, mode);
            const store = tx.objectStore(STORE);

            let result;
            try {
                result = fn(store);
            } catch (e) {
                reject(e);
                return;
            }

            result.onsuccess = () => resolve(result.result);
            result.onerror = () => reject(result.error);
        });
    };

    const isoNow = () => new Date().toISOString();

    const EyecatcherStorage = {
        async init() {
            return openDB();
        },

        async savePopulation(name, genomes, generation, representationId) {
            const now = isoNow();
            const record = {
                name: name || "Unnamed",
                genomes: genomes || [],
                generation: generation ?? 0,
                representationId: representationId ?? null,
                created: now,
                modified: now,
            };

            return runStore("readwrite", (store) => store.add(record));
        },

        async loadPopulation(id) {
            const record = await runStore("readonly", (store) => store.get(id));
            return record || null;
        },

        async listPopulations() {
            const list = await runStore("readonly", (store) => store.getAll());
            return (list || []).sort(
                (a, b) => new Date(b.modified) - new Date(a.modified)
            );
        },

        async importPopulation(json) {
            const name = json?.name || "Imported";
            const genomes = json?.genomes || [];
            const generation = json?.generation ?? 0;
            const representationId = json?.representationId ?? null;

            if (!Array.isArray(genomes) || genomes.length === 0) return null;

            const id = await this.savePopulation(
                name,
                genomes,
                generation,
                representationId
            );
            return { id, name, generation, count: genomes.length };
        },
    };

    // Globals / CommonJS
    if (typeof window !== "undefined") window.EyecatcherStorage = EyecatcherStorage;
    if (typeof module !== "undefined" && module.exports)
        module.exports = EyecatcherStorage;
})();
