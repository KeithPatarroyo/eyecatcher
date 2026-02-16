/**
 * Organism interaction handlers: save, click, unclick.
 * Used by app.js grid callbacks. Depends on window.PopulationState, ApiClient, Toast.
 */
(() => {
    "use strict";

    const showError = (title, message) => window.Toast?.show?.(title, message, "error");

    const showSuccess = (title, message, opts) =>
        window.Toast?.show?.(title, message, "success", opts);

    const withBusyButton = (buttonEl, busyText, fn) => {
        if (!buttonEl) return fn();

        const originalText = buttonEl.textContent;
        buttonEl.textContent = busyText;
        buttonEl.classList.add("saving");

        return Promise.resolve()
            .then(fn)
            .finally(() => {
                buttonEl.textContent = originalText;
                buttonEl.classList.remove("saving");
            });
    };

    const getGenomeOrNull = (id) => {
        const org = window.PopulationState?.getOrganism?.(id) ?? null;
        return org?.genome ?? null;
    };

    const setFitnessUI = (card, fitness) => {
        const badge = card?.querySelector?.(".fitness-badge") ?? null;
        if (!badge) return;

        badge.textContent = String(fitness);
        badge.classList.toggle("zero", fitness === 0);
        card?.classList.toggle?.("selected", fitness > 0);
    };

    const updateFitness = (id, card, delta, updateStats) => {
        const org = window.PopulationState?.getOrganism?.(id);
        if (!org) return;

        const current = org.fitness || 0;
        const next = Math.max(0, current + delta);
        if (next === current) return;

        window.PopulationState.dispatch({
            type: "SET_ORGANISM_FITNESS",
            payload: { id, fitness: next },
        });

        setFitnessUI(card, next);
        if (typeof updateStats === "function") updateStats();
    };

    class OrganismActions {
        savePattern(id, buttonEl) {
            const organisms = window.PopulationState?.organisms;
            if (!Array.isArray(organisms) || organisms.length === 0) {
                showError(
                    "Cannot save",
                    "No organism data. Start with New random population or Load population."
                );
                return;
            }

            const genome = getGenomeOrNull(id);
            if (!genome) {
                showError("Cannot save", "Could not get organism data.");
                return;
            }

            return withBusyButton(buttonEl, "Compiling...", () =>
                window.ApiClient.save(id, genome)
                    .then((data) => {
                        const downloads = data?.downloads;
                        if (!Array.isArray(downloads) || downloads.length === 0) {
                            showSuccess("Organism saved!", "No download in response.");
                            return;
                        }

                        const file = downloads[0];
                        const blob = file.content_base64
                            ? window.Toast.base64ToBlob(file.content_base64, file.mime)
                            : new Blob([file.content], { type: file.mime });

                        window.Toast.triggerDownload(blob, file.filename);
                        showSuccess(
                            "Organism saved!",
                            "Zip downloaded to your computer.",
                            {
                                duration: 5000,
                            }
                        );
                    })
                    .catch((error) => {
                        console.error("Error saving:", error);
                        showError("Save failed", error?.message || "Network error");
                    })
            );
        }

        clickPattern(id, card, updateStats) {
            updateFitness(id, card, +1, updateStats);
        }

        unclickPattern(id, card, updateStats) {
            updateFitness(id, card, -1, updateStats);
        }
    }

    window.OrganismActions = new OrganismActions();
})();
