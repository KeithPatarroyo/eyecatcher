/**
 * Open-Endedness Scoring Module
 *
 * Computes open-endedness scores for all patterns in the grid
 * when the OE Score button is pressed.
 */

const OpenEndednessTracker = (function() {
    // State
    let isComputing = false;
    let scoresComputed = false;
    let currentScores = new Map();  // genome_key -> score

    // Compute OE scores for all patterns in the grid
    async function computeAllScores(genomes, generation) {
        if (isComputing || !genomes || genomes.length === 0) {
            return;
        }

        isComputing = true;
        scoresComputed = false;
        updateToggleState();

        // Show loading indicators on all pattern cards
        const cards = document.querySelectorAll('.pattern-card');
        cards.forEach(card => {
            let scoreDisplay = card.querySelector('.oe-score');
            if (!scoreDisplay) {
                scoreDisplay = document.createElement('div');
                scoreDisplay.className = 'oe-score computing';
                scoreDisplay.textContent = '...';
                scoreDisplay.title = 'Computing open-endedness score...';
                card.appendChild(scoreDisplay);
            } else {
                scoreDisplay.className = 'oe-score computing';
                scoreDisplay.textContent = '...';
            }
        });

        showToast('Computing...', `Calculating OE scores for ${genomes.length} patterns. Check terminal for progress.`, 'info');

        try {
            const response = await fetch(`${API_URL}/open-endedness/batch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    genomes: genomes,
                    num_frames: 16,
                    resolution: 64,
                    generation: generation || 0
                })
            });

            const data = await response.json();

            if (data.available && Array.isArray(data.scores)) {
                // Store scores and update displays
                currentScores.clear();
                data.scores.forEach(result => {
                    currentScores.set(result.genome_key, result.score);
                });

                // Update all pattern cards with their scores
                cards.forEach(card => {
                    const patternId = parseInt(card.dataset.id);
                    const score = currentScores.get(patternId);
                    const scoreDisplay = card.querySelector('.oe-score');

                    if (scoreDisplay) {
                        if (typeof score === 'number') {
                            scoreDisplay.className = 'oe-score';
                            scoreDisplay.textContent = score.toFixed(3);
                            scoreDisplay.title = `Open-endedness score: ${score.toFixed(4)} (lower = more diverse)`;
                        } else {
                            scoreDisplay.className = 'oe-score error';
                            scoreDisplay.textContent = 'N/A';
                            scoreDisplay.title = 'Score not available';
                        }
                    }
                });

                scoresComputed = true;
                showToast('Scores computed', `OE scores calculated for ${data.scores.length} patterns`, 'success');
            } else {
                console.error('Failed to compute scores:', data.error);
                clearScoreDisplays();
                showToast('Error', data.error || 'Failed to compute scores', 'error');
            }
        } catch (e) {
            console.error('Error computing open-endedness scores:', e);
            clearScoreDisplays();
            showToast('Error', 'Failed to connect to server', 'error');
        } finally {
            isComputing = false;
            updateToggleState();
        }
    }

    // Clear all score displays
    function clearScoreDisplays() {
        document.querySelectorAll('.oe-score').forEach(el => el.remove());
        currentScores.clear();
        scoresComputed = false;
    }

    // Toggle - compute scores for all patterns
    async function toggleTracking() {
        if (isComputing) {
            showToast('Please wait', 'Score computation in progress...', 'info');
            return;
        }

        if (scoresComputed) {
            // If scores already computed, clear them
            clearScoreDisplays();
            updateToggleState();
            return;
        }

        // Get all current genomes and generation from the viewer
        if (typeof currentGenomes !== 'undefined' && currentGenomes && currentGenomes.length > 0) {
            const generation = typeof currentGenerationNum !== 'undefined' ? currentGenerationNum : 0;
            await computeAllScores(currentGenomes, generation);
        } else {
            showToast('No patterns', 'No patterns loaded to compute scores for', 'info');
        }
    }

    // Update UI state
    function updateToggleState() {
        const toggle = document.getElementById('oe-toggle');
        const status = document.getElementById('oe-status');

        if (toggle) {
            toggle.classList.remove('unavailable');

            if (isComputing) {
                toggle.classList.add('computing');
                toggle.title = 'Computing scores...';
            } else {
                toggle.classList.remove('computing');
                toggle.title = scoresComputed ? 'Click to clear scores' : 'Click to compute OE scores for all patterns';
            }

            if (scoresComputed) {
                toggle.classList.add('active');
            } else {
                toggle.classList.remove('active');
            }
        }

        if (status) {
            if (isComputing) {
                status.textContent = '...';
                status.className = 'oe-status computing';
            } else if (scoresComputed) {
                status.textContent = 'ON';
                status.className = 'oe-status active';
            } else {
                status.textContent = 'OFF';
                status.className = 'oe-status';
            }
        }
    }

    // Initialize the module
    async function init() {
        updateToggleState();
    }

    // Public API
    return {
        init,
        computeAllScores,
        clearScoreDisplays,
        toggleTracking,
        isComputing: () => isComputing,
        hasScores: () => scoresComputed,
        getScore: (genomeKey) => currentScores.get(genomeKey)
    };
})();
