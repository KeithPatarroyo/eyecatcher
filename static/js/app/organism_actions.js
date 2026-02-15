/**
 * Organism interaction handlers: save, click, unclick.
 * Used by app.js grid callbacks. Depends on window.PopulationState, ApiClient, Toast.
 */
(function () {
    "use strict";

    class OrganismActions {
        savePattern(id, buttonEl) {
            if (!window.PopulationState.organisms.length) {
                window.Toast.show(
                    "Cannot save",
                    "No organism data. Start with New random population or Load population.",
                    "error"
                );
                return;
            }
            var org = window.PopulationState.getOrganism(id);
            var genome = org ? org.genome : null;
            if (!genome) {
                window.Toast.show(
                    "Cannot save",
                    "Could not get organism data.",
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
                        window.Toast.show(
                            "Organism saved!",
                            "Zip downloaded to your computer.",
                            "success",
                            { duration: 5000 }
                        );
                    } else {
                        window.Toast.show(
                            "Organism saved!",
                            "No download in response.",
                            "success"
                        );
                    }
                })
                .catch(function (error) {
                    console.error("Error saving:", error);
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

        clickPattern(id, card, updateStats) {
            var org = window.PopulationState.getOrganism(id);
            if (org) {
                var fitness = (org.fitness || 0) + 1;
                window.PopulationState.dispatch({
                    type: "SET_ORGANISM_FITNESS",
                    payload: { id: id, fitness: fitness },
                });
                var fitnessBadge = card.querySelector(".fitness-badge");
                if (fitnessBadge) {
                    fitnessBadge.textContent = fitness;
                    fitnessBadge.classList.remove("zero");
                }
                card.classList.add("selected");
                if (typeof updateStats === "function") updateStats();
            }
        }

        unclickPattern(id, card, updateStats) {
            var org = window.PopulationState.getOrganism(id);
            if (org && (org.fitness || 0) > 0) {
                var fitness = org.fitness - 1;
                window.PopulationState.dispatch({
                    type: "SET_ORGANISM_FITNESS",
                    payload: { id: id, fitness: fitness },
                });
                var fitnessBadge = card.querySelector(".fitness-badge");
                if (fitnessBadge) {
                    fitnessBadge.textContent = fitness;
                    if (fitness === 0) {
                        fitnessBadge.classList.add("zero");
                        card.classList.remove("selected");
                    }
                }
                if (typeof updateStats === "function") updateStats();
            }
        }
    }

    window.OrganismActions = new OrganismActions();
})();
