/**
 * Debug overlay module for Eyecatcher
 * Provides real-time signal monitoring and time CPPN output sampling.
 */
const EyecatcherDebug = (function() {
    // Configuration
    let apiUrl = '';
    let getMouseDistanceFn = null;  // Function to get mouse distance to a pattern
    let getPatternsMapFn = null;    // Function to get the patterns Map
    let getSignalStateFn = null;    // Function to get signal state
    
    // State
    let hoveredPatternId = null;
    let timeSamplingEnabled = false;
    let lastSampleTime = 0;
    let lastSampledTimeOutput = null;
    let pendingSampleRequest = false;
    const SAMPLE_INTERVAL_MS = 400;
    
    // DOM elements (created dynamically)
    let toggleBtn = null;
    let overlay = null;
    let elements = {};
    
    /**
     * Create the debug overlay DOM structure
     */
    function createDOM() {
        // Toggle button
        toggleBtn = document.createElement('button');
        toggleBtn.id = 'debug-toggle';
        toggleBtn.textContent = 'Debug';
        document.body.appendChild(toggleBtn);
        
        // Overlay container
        overlay = document.createElement('div');
        overlay.id = 'debug-overlay';
        overlay.className = 'hidden';
        overlay.innerHTML = `
            <h4>Global Signals</h4>
            <div class="debug-row">
                <span class="debug-label">Raw Time:</span>
                <span class="debug-value" id="dbg-time">0.000</span>
            </div>
            <div class="debug-row">
                <span class="debug-label">Mouse Speed:</span>
                <span class="debug-value" id="dbg-mouseSpeed">0.000</span>
            </div>
            <div class="debug-row">
                <span class="debug-label">Activity:</span>
                <span class="debug-value" id="dbg-activity">0.000</span>
            </div>
            <div class="debug-row">
                <span class="debug-label">Mouse Pos:</span>
                <span class="debug-value" id="dbg-mousePos">0, 0</span>
            </div>
            <h4 style="margin-top: 10px;">Hovered Pattern <span id="dbg-pattern-id" style="color: #0a0;">(none)</span></h4>
            <div class="debug-row">
                <span class="debug-label">Mouse Dist:</span>
                <span class="debug-value" id="dbg-mouseDist">-</span>
            </div>
            <h4 style="margin-top: 8px; font-size: 9px; color: #666;">Time CPPN → Visual CPPN</h4>
            <div class="debug-row">
                <span class="debug-label" style="color: #6ca0dc;">Time (output):</span>
                <span class="debug-value" id="dbg-v-time" style="color: #6ca0dc;">-</span>
            </div>
            <div class="debug-checkbox">
                <input type="checkbox" id="dbg-sample-time">
                <label for="dbg-sample-time">Sample time output</label>
            </div>
            <div class="debug-warning" id="dbg-sample-warning" style="display: none;">
                ⚠ Sampling enabled (may add latency)
            </div>
        `;
        document.body.appendChild(overlay);
        
        // Cache element references
        elements = {
            time: document.getElementById('dbg-time'),
            mouseSpeed: document.getElementById('dbg-mouseSpeed'),
            activity: document.getElementById('dbg-activity'),
            mousePos: document.getElementById('dbg-mousePos'),
            patternId: document.getElementById('dbg-pattern-id'),
            mouseDist: document.getElementById('dbg-mouseDist'),
            timeOutput: document.getElementById('dbg-v-time'),
            sampleCheckbox: document.getElementById('dbg-sample-time'),
            sampleWarning: document.getElementById('dbg-sample-warning')
        };
    }
    
    /**
     * Set up event listeners
     */
    function setupEventListeners() {
        // Toggle button
        toggleBtn.addEventListener('click', () => {
            overlay.classList.toggle('hidden');
            toggleBtn.style.display = overlay.classList.contains('hidden') ? 'block' : 'none';
        });
        
        // Double-click overlay to close
        overlay.addEventListener('dblclick', () => {
            overlay.classList.add('hidden');
            toggleBtn.style.display = 'block';
        });
        
        // Sample checkbox
        elements.sampleCheckbox.addEventListener('change', (e) => {
            timeSamplingEnabled = e.target.checked;
            elements.sampleWarning.style.display = timeSamplingEnabled ? 'block' : 'none';
            if (!timeSamplingEnabled) {
                lastSampledTimeOutput = null;
            }
        });
    }
    
    /**
     * Fetch time output from server (sparse sampling)
     */
    async function sampleTimeOutput(patternId, time, mouseSpd, mouseDist, activityLevel) {
        if (pendingSampleRequest) return;
        
        pendingSampleRequest = true;
        lastSampleTime = performance.now();
        
        try {
            const url = `${apiUrl}/time-output?id=${patternId}&time=${time}&mouseSpeed=${mouseSpd}&mouseDist=${mouseDist}&activity=${activityLevel}`;
            const response = await fetch(url);
            const data = await response.json();
            
            // Only update if still hovering the same pattern
            if (hoveredPatternId === patternId && timeSamplingEnabled) {
                lastSampledTimeOutput = data.timeOutput;
            }
        } catch (error) {
            console.error('Error sampling time output:', error);
        } finally {
            pendingSampleRequest = false;
        }
    }
    
    /**
     * Format number for display
     */
    function fmt(v) {
        return v.toFixed(3);
    }
    
    // Public API
    return {
        /**
         * Initialize the debug module
         * @param {Object} config Configuration object
         * @param {string} config.apiUrl Base API URL
         * @param {Function} config.getMouseDistance Function(canvas) that returns mouse distance to canvas center
         * @param {Function} config.getPatterns Function() that returns the patterns Map
         * @param {Function} config.getSignalState Function() that returns signalState object
         */
        init: function(config) {
            apiUrl = config.apiUrl || '';
            getMouseDistanceFn = config.getMouseDistance || (() => 0);
            getPatternsMapFn = config.getPatterns || (() => new Map());
            getSignalStateFn = config.getSignalState || (() => ({ visual: { time: true } }));
            
            createDOM();
            setupEventListeners();
        },
        
        /**
         * Update the debug overlay with current values
         * @param {Object} state Current state
         * @param {number} state.time Animation time (0-1)
         * @param {number} state.mouseSpeed Mouse speed (0-1)
         * @param {number} state.activity Activity level (0-1)
         * @param {number} state.mouseX Mouse X position
         * @param {number} state.mouseY Mouse Y position
         */
        update: function(state) {
            // Skip if hidden
            if (overlay.classList.contains('hidden')) return;
            
            const { time, mouseSpeed, activity, mouseX, mouseY } = state;
            
            // Global signals
            elements.time.textContent = fmt(time);
            elements.mouseSpeed.textContent = fmt(mouseSpeed);
            elements.activity.textContent = fmt(activity);
            elements.mousePos.textContent = `${Math.round(mouseX)}, ${Math.round(mouseY)}`;
            
            const timeEl = elements.timeOutput;
            const signalState = getSignalStateFn();
            const timeEnabled = signalState.visual.time;
            
            // Hovered pattern info
            const patterns = getPatternsMapFn();
            if (hoveredPatternId !== null && patterns.has(hoveredPatternId)) {
                const patternData = patterns.get(hoveredPatternId);
                const mouseDist = getMouseDistanceFn(patternData.canvas);
                
                elements.patternId.textContent = `#${hoveredPatternId}`;
                elements.mouseDist.textContent = fmt(mouseDist);
                
                // Time output - either sampled or placeholder
                if (timeSamplingEnabled && timeEnabled) {
                    // Trigger sparse sampling if enough time has passed
                    const now = performance.now();
                    if (!pendingSampleRequest && (now - lastSampleTime) >= SAMPLE_INTERVAL_MS) {
                        sampleTimeOutput(hoveredPatternId, time, mouseSpeed, mouseDist, activity);
                    }
                    
                    // Display last sampled value or loading indicator
                    if (lastSampledTimeOutput !== null) {
                        timeEl.textContent = fmt(lastSampledTimeOutput);
                        timeEl.classList.remove('disabled');
                        timeEl.classList.add('sampled');
                    } else {
                        timeEl.textContent = '...';
                        timeEl.classList.remove('disabled', 'sampled');
                    }
                } else {
                    // Not sampling - show placeholder
                    timeEl.textContent = timeEnabled ? 'unique' : 'disabled';
                    timeEl.classList.toggle('disabled', !timeEnabled);
                    timeEl.classList.remove('sampled');
                }
            } else {
                elements.patternId.textContent = '(hover to see)';
                elements.mouseDist.textContent = '-';
                timeEl.textContent = '-';
                timeEl.classList.remove('disabled', 'sampled');
                lastSampledTimeOutput = null;
            }
        },
        
        /**
         * Set the currently hovered pattern ID
         * Called from main script on card mouseenter/mouseleave
         * @param {number|null} id Pattern ID or null if not hovering
         */
        setHoveredPatternId: function(id) {
            if (id !== hoveredPatternId) {
                lastSampledTimeOutput = null;  // Reset sample when changing patterns
            }
            hoveredPatternId = id;
        },
        
        /**
         * Get the currently hovered pattern ID
         * @returns {number|null}
         */
        getHoveredPatternId: function() {
            return hoveredPatternId;
        }
    };
})();
