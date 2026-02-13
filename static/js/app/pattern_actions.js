/**
 * Pattern interaction handlers: save, click, unclick.
 * Used by app.js grid callbacks. Depends on window.PopulationState, ApiClient, Toast.
 */
(function () {
    "use strict";

    function savePattern(id, buttonEl) {
        var state = window.PopulationState.getState();
        if (!state.currentGenomes || !state.currentGenomes.length) {
            window.Toast.show(
                "Cannot save",
                "No pattern data. Start with New random population or Load population.",
                "error"
            );
            return;
        }
        var idx = state.currentPopulation.findIndex(function (p) {
            return p.id === id;
        });
        var genome =
            idx >= 0 && state.currentGenomes[idx] ? state.currentGenomes[idx] : null;
        if (!genome) {
            window.Toast.show("Cannot save", "Could not get pattern data.", "error");
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
                        "Pattern saved!",
                        "Zip downloaded to your computer.",
                        "success",
                        { duration: 5000 }
                    );
                } else {
                    window.Toast.show(
                        "Pattern saved!",
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

    function clickPattern(id, card, updateStats) {
        var state = window.PopulationState.getState();
        var pattern = state.patterns.get(id);
        if (pattern) {
            var clicks = (pattern.clicks || 0) + 1;
            window.PopulationState.dispatch({
                type: "SET_PATTERN_CLICKS",
                payload: { id: id, clicks: clicks },
            });
            var clickCount = card.querySelector(".click-count");
            if (clickCount) {
                clickCount.textContent = clicks;
                clickCount.classList.remove("zero");
            }
            card.classList.add("selected");
            if (typeof updateStats === "function") updateStats();
        }
    }

    function unclickPattern(id, card, updateStats) {
        var state = window.PopulationState.getState();
        var pattern = state.patterns.get(id);
        if (pattern && (pattern.clicks || 0) > 0) {
            var clicks = pattern.clicks - 1;
            window.PopulationState.dispatch({
                type: "SET_PATTERN_CLICKS",
                payload: { id: id, clicks: clicks },
            });
            var clickCount = card.querySelector(".click-count");
            if (clickCount) {
                clickCount.textContent = clicks;
                if (clicks === 0) {
                    clickCount.classList.add("zero");
                    card.classList.remove("selected");
                }
            }
            if (typeof updateStats === "function") updateStats();
        }
    }

    window.PatternActions = {
        savePattern: savePattern,
        clickPattern: clickPattern,
        unclickPattern: unclickPattern,
    };
})();
