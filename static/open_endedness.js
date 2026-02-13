/**
 * Open-Endedness Tracking Module
 *
 * Provides functionality to compute and track open-endedness scores
 * for selected patterns during interactive evolution.
 */

const OpenEndednessTracker = (function() {
    // State
    let trackingEnabled = false;
    let isAvailable = true;  // Bypass availability check for now
    let trackedSelections = [];  // Array of { genome, score, timestamp, generation }
    let scoreCache = new Map();  // genome_key -> score (to avoid recomputing)

    // Check if open-endedness scoring is available on the server
    async function checkAvailability() {
        // Bypassed for now - assume available
        isAvailable = true;
        updateToggleState();
        return isAvailable;
    }

    // Compute open-endedness score for a genome
    async function computeScore(genome) {
        const key = genome.key;

        // Check cache first
        if (scoreCache.has(key)) {
            return scoreCache.get(key);
        }

        try {
            const response = await fetch(`${API_URL}/open-endedness`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    genome: genome,
                    num_frames: 16,
                    resolution: 224
                })
            });

            const data = await response.json();

            if (data.available && typeof data.score === 'number') {
                scoreCache.set(key, data.score);
                return data.score;
            } else {
                console.warn('Failed to compute score:', data.error);
                return null;
            }
        } catch (e) {
            console.error('Error computing open-endedness score:', e);
            return null;
        }
    }

    // Track a selection (called when pattern is clicked)
    async function trackSelection(patternId, genome, generation) {
        if (!trackingEnabled || !genome) return null;

        // Show loading indicator on the pattern
        const card = document.querySelector(`.pattern-card[data-id="${patternId}"]`);
        let scoreDisplay = card?.querySelector('.oe-score');

        if (card && !scoreDisplay) {
            scoreDisplay = document.createElement('div');
            scoreDisplay.className = 'oe-score computing';
            scoreDisplay.textContent = '...';
            scoreDisplay.title = 'Computing open-endedness score...';
            card.appendChild(scoreDisplay);
        } else if (scoreDisplay) {
            scoreDisplay.className = 'oe-score computing';
            scoreDisplay.textContent = '...';
        }

        // Compute score (may fail if server doesn't have dependencies)
        const score = await computeScore(genome);

        // Always track the selection, even if score is null
        trackedSelections.push({
            genome: genome,
            score: score,  // may be null if computation failed
            timestamp: new Date().toISOString(),
            generation: generation,
            patternId: patternId
        });
        updateTrackedCount();

        if (score !== null) {
            // Update display with computed score
            if (scoreDisplay) {
                scoreDisplay.className = 'oe-score';
                scoreDisplay.textContent = score.toFixed(3);
                scoreDisplay.title = `Open-endedness score: ${score.toFixed(4)} (lower = more diverse)`;
            }
            return score;
        } else {
            // Score computation failed, but pattern is still tracked
            if (scoreDisplay) {
                scoreDisplay.className = 'oe-score error';
                scoreDisplay.textContent = 'N/A';
                scoreDisplay.title = 'Score unavailable (check server logs)';
            }
            return null;
        }
    }

    // Remove tracking for a pattern (called when pattern is unclicked)
    function untrackSelection(patternId) {
        // Remove from tracked selections (keep only the last one if multiple)
        const idx = trackedSelections.findIndex(s => s.patternId === patternId);
        if (idx !== -1) {
            trackedSelections.splice(idx, 1);
            updateTrackedCount();
        }

        // Remove score display
        const card = document.querySelector(`.pattern-card[data-id="${patternId}"]`);
        const scoreDisplay = card?.querySelector('.oe-score');
        if (scoreDisplay) {
            scoreDisplay.remove();
        }
    }

    // Clear all score displays (e.g., when breeding new generation)
    function clearScoreDisplays() {
        document.querySelectorAll('.oe-score').forEach(el => el.remove());
        scoreCache.clear();
    }

    // Export tracked selections
    function exportTrackedSelections() {
        if (trackedSelections.length === 0) {
            showToast('No selections', 'No patterns have been tracked yet. Enable tracking and click on some patterns.', 'info');
            return;
        }

        const withScores = trackedSelections.filter(s => s.score !== null).length;
        const exportData = {
            name: 'Open-Endedness Tracked Selections',
            exportedAt: new Date().toISOString(),
            totalSelections: trackedSelections.length,
            selectionsWithScores: withScores,
            selections: trackedSelections.map(s => ({
                genome: s.genome,
                score: s.score,  // may be null
                timestamp: s.timestamp,
                generation: s.generation
            }))
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const filename = `oe_tracked_${new Date().toISOString().slice(0, 10)}.json`;
        triggerDownload(blob, filename);

        const msg = withScores < trackedSelections.length
            ? `${trackedSelections.length} selections (${withScores} with scores)`
            : `${trackedSelections.length} selections with scores`;
        showToast('Exported', `${msg} saved to ${filename}`, 'success');
    }

    // Clear tracked selections
    function clearTrackedSelections() {
        trackedSelections = [];
        updateTrackedCount();
        showToast('Cleared', 'Tracked selections cleared', 'info');
    }

    // Toggle tracking on/off
    function toggleTracking() {
        // Availability check bypassed for now
        trackingEnabled = !trackingEnabled;
        console.log('[OE] Tracking toggled:', trackingEnabled);
        updateToggleState();

        if (trackingEnabled) {
            showToast('Tracking enabled', 'Selected patterns will have their open-endedness score computed.', 'info');
        } else {
            clearScoreDisplays();
        }
    }

    // Update UI state
    function updateToggleState() {
        const toggle = document.getElementById('oe-toggle');
        const status = document.getElementById('oe-status');

        if (toggle) {
            if (isAvailable === false) {
                toggle.classList.add('unavailable');
                toggle.title = 'Open-endedness scoring not available (install jax, flax, transformers)';
            } else {
                toggle.classList.remove('unavailable');
                toggle.title = trackingEnabled ? 'Click to disable tracking' : 'Click to enable tracking';
            }

            if (trackingEnabled) {
                toggle.classList.add('active');
            } else {
                toggle.classList.remove('active');
            }
        }

        if (status) {
            status.textContent = trackingEnabled ? 'ON' : 'OFF';
            status.className = trackingEnabled ? 'oe-status active' : 'oe-status';
        }
    }

    function updateTrackedCount() {
        const countEl = document.getElementById('oe-tracked-count');
        if (countEl) {
            countEl.textContent = trackedSelections.length;
        }
    }

    // Initialize the module
    async function init() {
        await checkAvailability();
        updateToggleState();
        updateTrackedCount();
    }

    // Public API
    return {
        init,
        checkAvailability,
        computeScore,
        trackSelection,
        untrackSelection,
        clearScoreDisplays,
        exportTrackedSelections,
        clearTrackedSelections,
        toggleTracking,
        isTrackingEnabled: () => trackingEnabled,
        isAvailable: () => isAvailable,
        getTrackedSelections: () => [...trackedSelections],
        getTrackedCount: () => trackedSelections.length
    };
})();
