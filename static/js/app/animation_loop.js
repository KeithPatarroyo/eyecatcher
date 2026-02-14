/**
 * Animation loop: mouse tracking, time modes (loop/oscillate/infinite), and per-frame pattern rendering.
 * Exposes: AnimationLoop.init(), AnimationLoop.start(), AnimationLoop.stop(),
 *   AnimationLoop.getSignalValues(canvas), AnimationLoop.getMouseSpeed(), AnimationLoop.getMouseDistance(canvas),
 *   AnimationLoop.getActivity(), AnimationLoop.getMouseX(), AnimationLoop.getMouseY(), AnimationLoop.getTime()
 *
 * Signal values come from a pluggable SignalSource (getValues(context) -> { raw_time, mouse_speed, mouse_dist, activity }).
 * Set window.SignalSource before init, or pass signalSource in init(); otherwise the built-in viewer source is used.
 */
(function () {
    "use strict";

    const ANIMATION_SPEED = 0.005;
    const MOUSE_SPEED_DECAY = 0.95;
    const MOUSE_SPEED_SCALE = 0.005;
    const MOUSE_DIST_SCALE = 300;
    const ACTIVITY_DECAY = 0.985;
    const ACTIVITY_BOOST = 0.15;

    let mouseSpeed = 0;
    let mouseX = 0;
    let mouseY = 0;
    let lastMouseX = 0;
    let lastMouseY = 0;
    let lastMouseTime = 0;
    let activity = 0;
    let animationTime = 0;
    let oscillatePhase = 0;
    let animating = true;

    let _getPatterns = null;
    let _patternRenderer = null;
    let _viewerControls = null;
    /** @type {{ getValues: function({ canvas?: HTMLCanvasElement }): Object } | null } */
    let _signalSource = null;
    /** Default source: viewer mouse + time; created in init(). */
    let _defaultSource = null;

    let _frameCount = 0;
    let _lastFrameTime = 0;

    function getMouseDistanceToCanvas(canvas) {
        const rect = canvas.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const dx = mouseX - centerX;
        const dy = mouseY - centerY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        return Math.min(1.0, dist / MOUSE_DIST_SCALE);
    }

    /** Build default signal values from viewer state (mouse + time). Used by _defaultSource. Keys from SIGNAL_IDS; values from viewer or 0. Adds grid_row, grid_col when context.gridPosition exists. */
    function buildDefaultSignalValues(context) {
        const canvas = context && context.canvas;
        const mouse_dist = canvas ? getMouseDistanceToCanvas(canvas) : 0;
        const rect = canvas ? canvas.getBoundingClientRect() : null;
        const mouse_x = rect
            ? Math.min(1.0, Math.max(0.0, (mouseX - rect.left) / rect.width))
            : 0.5;
        const mouse_y = rect
            ? Math.min(1.0, Math.max(0.0, (mouseY - rect.top) / rect.height))
            : 0.5;
        const computed = {
            raw_time: animationTime,
            mouse_speed: mouseSpeed,
            mouse_dist: mouse_dist,
            activity: activity,
            mouse_x: mouse_x,
            mouse_y: mouse_y,
        };
        if (context && context.gridPosition) {
            const pos = context.gridPosition;
            const GT = window.GridTopology;
            const cols = (GT && GT.getColumns && GT.getColumns()) || 1;
            const total = GT && GT.getAll && GT.getAll() ? GT.getAll().size : 1;
            const rows = cols > 0 ? Math.ceil(total / cols) : 1;
            computed.grid_row = rows > 1 ? pos.row / (rows - 1) : 0;
            computed.grid_col = cols > 1 ? pos.col / (cols - 1) : 0;
        }
        const signalIds =
            (window.EvolutionConfigSignals &&
                window.EvolutionConfigSignals.SIGNAL_IDS) ||
            Object.keys(computed);
        const out = {};
        signalIds.forEach(function (id) {
            out[id] = computed[id] !== undefined ? computed[id] : 0.0;
        });
        return out;
    }

    /** Returns the active signal source (custom or default). Used by getSignalValues and by community/genealogy. */
    function getActiveSignalSource() {
        return _signalSource || _defaultSource;
    }

    function getSignalValues(canvas) {
        const source = getActiveSignalSource();
        if (source && typeof source.getValues === "function") {
            return source.getValues({ canvas: canvas || undefined });
        }
        const ids = (window.EvolutionConfig && window.EvolutionConfig.SIGNAL_IDS) || [];
        const out = {};
        ids.forEach(function (id) {
            out[id] = id === "raw_time" ? 0.5 : 0;
        });
        return Object.keys(out).length ? out : { raw_time: 0.5 };
    }

    function animate() {
        if (animating) {
            const timeMode =
                document.querySelector('input[name="timeMode"]:checked')?.value ||
                "oscillate";

            switch (timeMode) {
                case "loop":
                    animationTime = (animationTime + ANIMATION_SPEED) % 1.0;
                    break;
                case "oscillate":
                    oscillatePhase += ANIMATION_SPEED;
                    animationTime = (Math.sin(oscillatePhase * Math.PI * 2) + 1) * 0.5;
                    break;
                case "infinite":
                    animationTime += ANIMATION_SPEED;
                    break;
                default:
                    animationTime = (animationTime + ANIMATION_SPEED) % 1.0;
            }

            const normalizedTime = animationTime;
            mouseSpeed *= MOUSE_SPEED_DECAY;
            activity *= ACTIVITY_DECAY;

            const now = performance.now();
            const deltaTime = _lastFrameTime > 0 ? (now - _lastFrameTime) / 1000 : 0;
            _lastFrameTime = now;
            _frameCount++;

            const patterns = _getPatterns ? _getPatterns() : null;
            if (
                patterns &&
                _patternRenderer &&
                _viewerControls &&
                _viewerControls.signalState != null
            ) {
                const signalState = _viewerControls.signalState;
                const SA = window.SubstrateAdapters;
                const state =
                    window.PopulationState &&
                    window.PopulationState.getState &&
                    window.PopulationState.getState();
                const substrateId = state ? state.substrateId : null;
                const resolved =
                    SA && SA.safeResolve
                        ? SA.safeResolve({ substrateId: substrateId })
                        : { adapter: null };
                const adapter = resolved.adapter;
                const GT = window.GridTopology;

                patterns.forEach(function (patternData) {
                    if (adapter && adapter.lifecycle === "self-managed") return;
                    if (!patternData.gl) return;
                    var patternId = patternData.patternId;
                    var renderContext = {
                        gl: patternData.gl,
                        canvas: patternData.canvas,
                        gridPosition: GT ? GT.getPosition(patternId) : null,
                        neighbors: GT ? GT.getNeighbors(patternId) : null,
                        frameCount: _frameCount,
                        deltaTime: deltaTime,
                        patternId: patternId,
                    };
                    if (adapter && typeof adapter.onBeforeRender === "function") {
                        adapter.onBeforeRender(patternData, renderContext);
                    }
                    _patternRenderer.renderWithSignals(
                        patternData,
                        _patternRenderer,
                        signalState,
                        patternData.canvas,
                        renderContext
                    );
                    if (adapter && typeof adapter.onAfterRender === "function") {
                        adapter.onAfterRender(patternData, renderContext);
                    }
                });
            }

            if (
                typeof window.EyecatcherDebug !== "undefined" &&
                window.EyecatcherDebug.update
            ) {
                window.EyecatcherDebug.update({
                    time: normalizedTime,
                    mouseSpeed: mouseSpeed,
                    activity: activity,
                    mouseX: mouseX,
                    mouseY: mouseY,
                });
            }
        }
        requestAnimationFrame(animate);
    }

    function init(options) {
        _getPatterns = options.getPatterns || null;
        _patternRenderer = options.patternRenderer || null;
        _viewerControls = options.viewerControls || null;
        _defaultSource = {
            getValues: function (context) {
                return buildDefaultSignalValues(context || {});
            },
        };
        _signalSource =
            (options && options.signalSource) || window.SignalSource || _defaultSource;
        window.getSignalSource = getActiveSignalSource;
        lastMouseTime = performance.now();

        document.addEventListener("mousemove", function (e) {
            const now = performance.now();
            const dt = now - lastMouseTime;

            mouseX = e.clientX;
            mouseY = e.clientY;

            if (dt > 0) {
                const dx = e.clientX - lastMouseX;
                const dy = e.clientY - lastMouseY;
                const distance = Math.sqrt(dx * dx + dy * dy);
                const instantSpeed = distance / dt;
                mouseSpeed = Math.min(
                    1.0,
                    mouseSpeed * 0.7 + instantSpeed * MOUSE_SPEED_SCALE * 0.3
                );
            }

            lastMouseX = e.clientX;
            lastMouseY = e.clientY;
            lastMouseTime = now;
            activity = Math.min(1.0, activity + mouseSpeed * ACTIVITY_BOOST);
        });

        const timeModeRadios = document.querySelectorAll('input[name="timeMode"]');
        timeModeRadios.forEach(function (radio) {
            radio.addEventListener("change", function () {
                animationTime = 0;
                oscillatePhase = 0;
            });
        });
    }

    function start() {
        animating = true;
        _lastFrameTime = performance.now();
        requestAnimationFrame(animate);
    }

    function stop() {
        animating = false;
    }

    window.AnimationLoop = {
        init: init,
        start: start,
        stop: stop,
        getSignalValues: getSignalValues,
        getMouseSpeed: function () {
            return mouseSpeed;
        },
        getMouseDistance: getMouseDistanceToCanvas,
        getActivity: function () {
            return activity;
        },
        getMouseX: function () {
            return mouseX;
        },
        getMouseY: function () {
            return mouseY;
        },
        getTime: function () {
            return animationTime;
        },
        getFrameCount: function () {
            return _frameCount;
        },
    };
})();
