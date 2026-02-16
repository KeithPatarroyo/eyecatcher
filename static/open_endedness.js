/**
 * Open-Endedness Scoring Module
 *
 * Computes open-endedness scores for all patterns in the grid
 * using frames captured directly from the WebGL shaders.
 * Processes one pattern at a time to avoid WebGL context limits.
 */

const OpenEndednessTracker = (function() {
    // State
    let isComputing = false;
    let scoresComputed = false;
    let currentScores = new Map();  // genome_key -> score

    // Configuration
    const NUM_FRAMES = 16;
    const FRAME_RESOLUTION = 64;

    /**
     * Capture frames from a pattern's WebGL canvas at different time values.
     * Uses the same shader that renders in the interactive viewer.
     * Captures at current canvas size to avoid WebGL context issues.
     */
    function capturePatternFrames(patternData, numFrames) {
        const { gl, program, positionBuffer, canvas } = patternData;

        if (!gl || !program) {
            console.error('Invalid pattern data for frame capture');
            return null;
        }

        // Check if context is lost
        if (gl.isContextLost()) {
            console.error('WebGL context is lost for this pattern');
            return null;
        }

        const frames = [];
        const width = canvas.width;
        const height = canvas.height;

        // Signal state for rendering (only time enabled for consistent capture)
        const signalState = {
            time: { rawTime: true, mouseSpeed: false, mouseDist: false, inactivity: false },
            visual: { time: true, mouseSpeed: false, mouseDist: false, inactivity: false }
        };

        for (let i = 0; i < numFrames; i++) {
            const time = i / (numFrames - 1);  // 0 to 1

            // Render the pattern at this time
            PatternRenderer.renderPattern(patternData, time, 0, 0, 0, signalState);

            // Capture pixels at current canvas size
            const pixels = new Uint8Array(width * height * 4);
            gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);

            // Convert to RGB array (flatten, remove alpha, flip vertically)
            const rgb = new Uint8Array(width * height * 3);
            for (let y = 0; y < height; y++) {
                for (let x = 0; x < width; x++) {
                    // WebGL reads bottom-to-top, so flip Y
                    const srcY = height - 1 - y;
                    const srcIdx = (srcY * width + x) * 4;
                    const dstIdx = (y * width + x) * 3;
                    rgb[dstIdx] = pixels[srcIdx];      // R
                    rgb[dstIdx + 1] = pixels[srcIdx + 1];  // G
                    rgb[dstIdx + 2] = pixels[srcIdx + 2];  // B
                }
            }

            // Convert to base64 for transmission (chunked to avoid stack overflow)
            let binary = '';
            const chunkSize = 8192;
            for (let j = 0; j < rgb.length; j += chunkSize) {
                const chunk = rgb.subarray(j, Math.min(j + chunkSize, rgb.length));
                binary += String.fromCharCode.apply(null, chunk);
            }
            frames.push(btoa(binary));
        }

        // Re-render at current animation time to restore display
        const currentTime = typeof animationTime !== 'undefined' ? animationTime : 0;
        const currentSignalState = typeof window.signalState !== 'undefined' ? window.signalState : signalState;
        PatternRenderer.renderPattern(patternData, currentTime, 0, 0, 0, currentSignalState);

        return { frames, width, height };
    }

    /**
     * Compute OE score for a single pattern by sending its frames to the server.
     */
    async function computeSinglePatternScore(patternId, frameData, generation) {
        try {
            const response = await fetch(`${API_URL}/open-endedness/from-frames`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    patterns: [{
                        genome_key: patternId,
                        frames: frameData.frames,
                        width: frameData.width,
                        height: frameData.height
                    }],
                    num_frames: NUM_FRAMES,
                    generation: generation || 0
                })
            });

            const data = await response.json();

            if (data.available && Array.isArray(data.scores) && data.scores.length > 0) {
                return data.scores[0].score;
            } else {
                console.error('Failed to compute score for pattern', patternId, data.error);
                return null;
            }
        } catch (e) {
            console.error('Error computing score for pattern', patternId, e);
            return null;
        }
    }

    /**
     * Compute OE scores for all patterns, one at a time.
     */
    async function computeAllScores(genomes, generation) {
        if (isComputing || !genomes || genomes.length === 0) {
            return;
        }

        isComputing = true;
        scoresComputed = false;
        currentScores.clear();
        updateToggleState();

        // Show loading indicators on all pattern cards
        const cards = document.querySelectorAll('.pattern-card');
        cards.forEach(card => {
            let scoreDisplay = card.querySelector('.oe-score');
            if (!scoreDisplay) {
                scoreDisplay = document.createElement('div');
                scoreDisplay.className = 'oe-score computing';
                scoreDisplay.textContent = '...';
                scoreDisplay.title = 'Waiting to compute...';
                card.appendChild(scoreDisplay);
            } else {
                scoreDisplay.className = 'oe-score computing';
                scoreDisplay.textContent = '...';
            }
        });

        showToast('Computing...', `Processing ${currentPopulation.length} patterns one at a time. Check terminal for progress.`, 'info');

        let successCount = 0;

        // Process patterns one at a time
        for (let i = 0; i < currentPopulation.length; i++) {
            const pattern = currentPopulation[i];
            const patternData = patterns.get(pattern.id);
            const card = document.querySelector(`.pattern-card[data-id="${pattern.id}"]`);
            const scoreDisplay = card?.querySelector('.oe-score');

            if (!patternData) {
                console.warn(`Pattern ${pattern.id} not found in patterns map`);
                if (scoreDisplay) {
                    scoreDisplay.className = 'oe-score error';
                    scoreDisplay.textContent = 'N/A';
                }
                continue;
            }

            // Update progress indicator
            if (scoreDisplay) {
                scoreDisplay.textContent = `${i + 1}...`;
                scoreDisplay.title = `Computing (${i + 1}/${currentPopulation.length})...`;
            }

            // Capture frames for this pattern (at current canvas size)
            const frameData = capturePatternFrames(patternData, NUM_FRAMES);

            if (!frameData || !frameData.frames) {
                console.warn(`Failed to capture frames for pattern ${pattern.id}`);
                if (scoreDisplay) {
                    scoreDisplay.className = 'oe-score error';
                    scoreDisplay.textContent = 'ERR';
                }
                continue;
            }

            // Send to server and get score
            const score = await computeSinglePatternScore(pattern.id, frameData, generation);

            if (typeof score === 'number') {
                currentScores.set(pattern.id, score);
                successCount++;

                if (scoreDisplay) {
                    scoreDisplay.className = 'oe-score';
                    scoreDisplay.textContent = score.toFixed(3);
                    scoreDisplay.title = `Open-endedness score: ${score.toFixed(4)} (lower = more diverse)`;
                }
            } else {
                if (scoreDisplay) {
                    scoreDisplay.className = 'oe-score error';
                    scoreDisplay.textContent = 'N/A';
                    scoreDisplay.title = 'Score not available';
                }
            }

            // Small delay between patterns to let WebGL stabilize
            await new Promise(resolve => setTimeout(resolve, 50));
        }

        isComputing = false;
        scoresComputed = successCount > 0;
        updateToggleState();

        if (successCount > 0) {
            showToast('Scores computed', `OE scores calculated for ${successCount} patterns`, 'success');
        } else {
            showToast('Error', 'Failed to compute any scores', 'error');
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
