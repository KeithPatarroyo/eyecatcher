/**
 * Open-Endedness Scoring Module
 *
 * Computes open-endedness scores for all patterns in the grid
 * using frames captured directly from the WebGL shaders.
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
     */
    function capturePatternFrames(patternData, numFrames, resolution) {
        const { gl, program, positionBuffer, canvas } = patternData;

        // Create an offscreen canvas at the desired resolution
        const offscreenCanvas = document.createElement('canvas');
        offscreenCanvas.width = resolution;
        offscreenCanvas.height = resolution;
        const offscreenGl = offscreenCanvas.getContext('webgl2', { preserveDrawingBuffer: true });

        if (!offscreenGl) {
            console.error('Could not create offscreen WebGL context');
            return null;
        }

        // We need to recreate the program for the offscreen context
        // Get the shader source from the original program (we'll need to pass it)
        // Actually, we can't easily get shader source from a compiled program
        // So we'll render on the existing canvas and capture from there

        // Alternative: render to existing canvas at each time step and capture
        const frames = [];
        const originalWidth = canvas.width;
        const originalHeight = canvas.height;

        // Temporarily resize canvas to capture resolution
        canvas.width = resolution;
        canvas.height = resolution;
        gl.viewport(0, 0, resolution, resolution);

        // Signal state for rendering (all signals enabled for consistent capture)
        const signalState = {
            time: { rawTime: true, mouseSpeed: false, mouseDist: false, inactivity: false },
            visual: { time: true, mouseSpeed: false, mouseDist: false, inactivity: false }
        };

        for (let i = 0; i < numFrames; i++) {
            const time = i / (numFrames - 1);  // 0 to 1

            // Render the pattern at this time
            PatternRenderer.renderPattern(patternData, time, 0, 0, 0, signalState);

            // Capture pixels
            const pixels = new Uint8Array(resolution * resolution * 4);
            gl.readPixels(0, 0, resolution, resolution, gl.RGBA, gl.UNSIGNED_BYTE, pixels);

            // Convert to RGB array (flatten, remove alpha, flip vertically)
            const rgb = new Uint8Array(resolution * resolution * 3);
            for (let y = 0; y < resolution; y++) {
                for (let x = 0; x < resolution; x++) {
                    // WebGL reads bottom-to-top, so flip Y
                    const srcY = resolution - 1 - y;
                    const srcIdx = (srcY * resolution + x) * 4;
                    const dstIdx = (y * resolution + x) * 3;
                    rgb[dstIdx] = pixels[srcIdx];      // R
                    rgb[dstIdx + 1] = pixels[srcIdx + 1];  // G
                    rgb[dstIdx + 2] = pixels[srcIdx + 2];  // B
                }
            }

            // Convert to base64 for transmission
            frames.push(btoa(String.fromCharCode.apply(null, rgb)));
        }

        // Restore original canvas size
        canvas.width = originalWidth;
        canvas.height = originalHeight;
        gl.viewport(0, 0, originalWidth, originalHeight);

        return frames;
    }

    /**
     * Compute OE scores for all patterns using WebGL-rendered frames.
     */
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

        showToast('Computing...', `Capturing frames from ${genomes.length} patterns. Check terminal for progress.`, 'info');

        try {
            // Capture frames from each pattern using WebGL
            const allPatternFrames = [];

            for (let i = 0; i < currentPopulation.length; i++) {
                const pattern = currentPopulation[i];
                const patternData = patterns.get(pattern.id);

                if (!patternData) {
                    console.warn(`Pattern ${pattern.id} not found in patterns map`);
                    allPatternFrames.push({ genome_key: pattern.id, frames: null });
                    continue;
                }

                // Capture frames using WebGL shader
                const frames = capturePatternFrames(patternData, NUM_FRAMES, FRAME_RESOLUTION);
                allPatternFrames.push({
                    genome_key: pattern.id,
                    frames: frames
                });

                // Update progress on the card
                const card = document.querySelector(`.pattern-card[data-id="${pattern.id}"]`);
                const scoreDisplay = card?.querySelector('.oe-score');
                if (scoreDisplay) {
                    scoreDisplay.textContent = `${i + 1}/${currentPopulation.length}`;
                }
            }

            // Send all frames to server for OE computation
            const response = await fetch(`${API_URL}/open-endedness/from-frames`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    patterns: allPatternFrames,
                    num_frames: NUM_FRAMES,
                    resolution: FRAME_RESOLUTION,
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
            showToast('Error', 'Failed to connect to server: ' + e.message, 'error');
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
