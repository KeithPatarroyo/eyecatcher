/**
 * Organism interaction handlers: save, click, unclick.
 * Used by app.js grid callbacks.
 */
import Toast from "../lib/toast.js";
import api from "../lib/api_client.js";
import DOM from "../lib/dom.js";
import populationState from "../population/population_state.js";

const showError = (title, message) => Toast.show(title, message, "error");

const showSuccess = (title, message, opts) =>
    Toast.show(title, message, "success", opts);

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

const getOrganismFlexible = (id) => {
    const PS = populationState;
    if (!PS?.getOrganism) return null;
    if (PS.getOrganism(id)) return PS.getOrganism(id);
    const s = id != null ? String(id) : "";
    if (PS.getOrganism(s)) return PS.getOrganism(s);
    if (/^\d+$/.test(s)) return PS.getOrganism(parseInt(s, 10)) ?? null;
    return null;
};

const getGenomeOrNull = (id) => getOrganismFlexible(id)?.genome ?? null;

const setFitnessUI = (card, fitness) => {
    const badge = card?.querySelector?.(".fitness-badge") ?? null;
    if (!badge) return;
    DOM.setText(badge, String(fitness));
    DOM.toggleClass(badge, "zero", fitness === 0);
    DOM.toggleClass(card, "selected", fitness > 0);
};

const updateFitness = (id, card, delta, updateStats) => {
    const org = getOrganismFlexible(id);
    if (!org) return;

    const current = org.fitness || 0;
    const next = Math.max(0, current + delta);
    if (next === current) return;

    const payloadId = typeof org.id !== "undefined" ? org.id : id;
    populationState.dispatch({
        type: "SET_ORGANISM_FITNESS",
        payload: { id: payloadId, fitness: next },
    });

    setFitnessUI(card, next);
    if (typeof updateStats === "function") updateStats();
};

class OrganismActions {
    savePattern(id, buttonEl) {
        const organisms = populationState?.organisms;
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
            api
                .save(id, genome)
                .then((data) => {
                    const downloads = data?.downloads;
                    if (!Array.isArray(downloads) || downloads.length === 0) {
                        showSuccess("Organism saved!", "No download in response.");
                        return;
                    }

                    const file = downloads[0];
                    const blob = file.content_base64
                        ? Toast.base64ToBlob(file.content_base64, file.mime)
                        : new Blob([file.content], { type: file.mime });

                    Toast.triggerDownload(blob, file.filename);
                    showSuccess("Organism saved!", "Zip downloaded to your computer.", {
                        duration: 5000,
                    });
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

const organismActions = new OrganismActions();
export default organismActions;
window.OrganismActions = organismActions;
