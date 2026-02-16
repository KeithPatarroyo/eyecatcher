/**
 * Animation loop: mouse tracking, time modes (loop/oscillate/infinite), and per-frame pattern rendering.
 * Signal values come from a pluggable SignalSource. Set window.SignalSource before init, or pass signalSource in init().
 */
(() => {
    "use strict";

    const ANIMATION_SPEED = 0.005;
    const MOUSE_SPEED_DECAY = 0.95;
    const MOUSE_SPEED_SCALE = 0.005;
    const MOUSE_DIST_SCALE = 300;
    const ACTIVITY_DECAY = 0.985;
    const ACTIVITY_BOOST = 0.15;

    const clamp01 = (x) => Math.min(1, Math.max(0, x));

    const getSignalIdsForCurrentRep = () => {
        const cfg = window.getConfig?.() ?? window.EvolutionConfig;
        return (
            (cfg && cfg.getSignalIdsForCurrentRep && cfg.getSignalIdsForCurrentRep()) ??
            []
        );
    };

    const getTimeMode = () =>
        document.querySelector('input[name="timeMode"]:checked')?.value ?? "oscillate";

    class AnimationLoop {
        constructor() {
            this._mouseSpeed = 0;
            this._mouseX = 0;
            this._mouseY = 0;
            this._lastMouseX = 0;
            this._lastMouseY = 0;
            this._lastMouseTime = 0;
            this._activity = 0;

            this._animationTime = 0;
            this._oscillatePhase = 0;

            this._animating = true;
            this._getPatterns = null;
            this._viewerControls = null;

            this._signalSource = null;
            this._defaultSource = null;

            this._frameCount = 0;
            this._lastFrameTime = 0;

            this._rafId = null;
            this._animate = this._animate.bind(this);
        }

        _getMouseDistanceToCanvas(canvas) {
            const rect = canvas.getBoundingClientRect();
            const centerX = rect.left + rect.width / 2;
            const centerY = rect.top + rect.height / 2;
            const dx = this._mouseX - centerX;
            const dy = this._mouseY - centerY;
            return Math.min(1, Math.hypot(dx, dy) / MOUSE_DIST_SCALE);
        }

        _defaultSignalValues(context = {}) {
            const canvas = context.canvas;
            const rect = canvas?.getBoundingClientRect?.() ?? null;

            const mouse_dist = canvas ? this._getMouseDistanceToCanvas(canvas) : 0;
            const mouse_x = rect
                ? clamp01((this._mouseX - rect.left) / rect.width)
                : 0.5;
            const mouse_y = rect
                ? clamp01((this._mouseY - rect.top) / rect.height)
                : 0.5;

            const computed = {
                raw_time: this._animationTime,
                mouse_speed: this._mouseSpeed,
                mouse_dist,
                activity: this._activity,
                mouse_x,
                mouse_y,
            };

            if (context.gridPosition) {
                const pos = context.gridPosition;
                const GT = window.GridTopology;
                const cols = GT?.getColumns?.() ?? 1;
                const total = GT?.getAll?.()?.size ?? 1;
                const rows = cols > 0 ? Math.ceil(total / cols) : 1;
                computed.grid_row = rows > 1 ? pos.row / (rows - 1) : 0;
                computed.grid_col = cols > 1 ? pos.col / (cols - 1) : 0;
            }

            const ids = getSignalIdsForCurrentRep();
            const requested = ids.length ? ids : Object.keys(computed);

            const out = {};
            for (const id of requested) out[id] = computed[id] ?? 0.0;
            return out;
        }

        getActiveSignalSource() {
            return this._signalSource || this._defaultSource;
        }

        _getSignalValues(signalContext) {
            const source = this.getActiveSignalSource();
            const values = source?.getValues?.(signalContext);

            if (values && Object.keys(values).length) return values;

            const ids = getSignalIdsForCurrentRep();
            if (!ids.length) return { raw_time: 0.5 };

            const fallback = {};
            for (const id of ids) fallback[id] = id === "raw_time" ? 0.5 : 0;
            return fallback;
        }

        _advanceTime() {
            const timeMode = getTimeMode();
            switch (timeMode) {
                case "loop":
                    this._animationTime = (this._animationTime + ANIMATION_SPEED) % 1.0;
                    break;
                case "oscillate":
                    this._oscillatePhase += ANIMATION_SPEED;
                    this._animationTime =
                        (Math.sin(this._oscillatePhase * Math.PI * 2) + 1) * 0.5;
                    break;
                case "infinite":
                    this._animationTime += ANIMATION_SPEED;
                    break;
                default:
                    this._animationTime = (this._animationTime + ANIMATION_SPEED) % 1.0;
            }
        }

        _animate() {
            if (this._animating) {
                this._advanceTime();
                this._mouseSpeed *= MOUSE_SPEED_DECAY;
                this._activity *= ACTIVITY_DECAY;

                const now = performance.now();
                const deltaTime = this._lastFrameTime
                    ? (now - this._lastFrameTime) / 1000
                    : 0;
                this._lastFrameTime = now;
                this._frameCount++;

                const runtimes = this._getPatterns?.() ?? null;
                const signalState = this._viewerControls?.signalState;

                if (runtimes && signalState != null && window.RepresentationRegistry) {
                    const GT = window.GridTopology;
                    for (const runtime of runtimes) {
                        if (!runtime?.gl) continue;
                        if (runtime.gl.isContextLost?.()) continue;

                        const patternId = runtime.patternId;
                        const renderContext = {
                            gl: runtime.gl,
                            canvas: runtime.canvas,
                            gridPosition: GT?.getPosition?.(patternId) ?? null,
                            neighbors: GT?.getNeighbors?.(patternId) ?? null,
                            frameCount: this._frameCount,
                            deltaTime,
                            patternId,
                        };

                        try {
                            this.renderFrameWithSignals(
                                runtime,
                                signalState,
                                runtime.canvas,
                                renderContext
                            );
                        } catch (err) {
                            console.warn(
                                `Pattern render failed (patternId=${patternId}):`,
                                err
                            );
                        }
                    }
                }

                window.EyecatcherDebug?.update?.({
                    time: this._animationTime,
                    mouseSpeed: this._mouseSpeed,
                    activity: this._activity,
                    mouseX: this._mouseX,
                    mouseY: this._mouseY,
                });
            }

            this._rafId = requestAnimationFrame(this._animate);
        }

        init(options = {}) {
            this._getPatterns = options.getPatterns ?? null;
            this._viewerControls = options.viewerControls ?? null;

            this._defaultSource = {
                getValues: (ctx) => this._defaultSignalValues(ctx),
            };
            this._signalSource =
                options.signalSource ?? window.SignalSource ?? this._defaultSource;

            window.getSignalSource = this.getActiveSignalSource.bind(this);

            this._lastMouseTime = performance.now();

            document.addEventListener("mousemove", (e) => {
                const now = performance.now();
                const dt = now - this._lastMouseTime;

                this._mouseX = e.clientX;
                this._mouseY = e.clientY;

                if (dt > 0) {
                    const dx = e.clientX - this._lastMouseX;
                    const dy = e.clientY - this._lastMouseY;
                    const instantSpeed = Math.hypot(dx, dy) / dt;
                    this._mouseSpeed = Math.min(
                        1.0,
                        this._mouseSpeed * 0.7 + instantSpeed * MOUSE_SPEED_SCALE * 0.3
                    );
                }

                this._lastMouseX = e.clientX;
                this._lastMouseY = e.clientY;
                this._lastMouseTime = now;

                this._activity = Math.min(
                    1.0,
                    this._activity + this._mouseSpeed * ACTIVITY_BOOST
                );
            });

            document.querySelectorAll('input[name="timeMode"]').forEach((radio) => {
                radio.addEventListener("change", () => {
                    this._animationTime = 0;
                    this._oscillatePhase = 0;
                });
            });
        }

        start() {
            this._animating = true;
            this._lastFrameTime = performance.now();
            if (this._rafId == null) this._rafId = requestAnimationFrame(this._animate);
        }

        stop() {
            this._animating = false;
        }

        getMouseSpeed() {
            return this._mouseSpeed;
        }
        getMouseDistance(canvas) {
            return this._getMouseDistanceToCanvas(canvas);
        }
        getActivity() {
            return this._activity;
        }
        getMouseX() {
            return this._mouseX;
        }
        getMouseY() {
            return this._mouseY;
        }

        /**
         * Get signal values from the active source (or defaults), build params via current
         * representation substrate, and render one frame. Used by the animation loop,
         * genealogy thumbnails, and community previews.
         * @param {Object} runtime - From WebGLUtils.setupPattern (gl, program, positionBuffer, canvas)
         * @param {Object} signalState - Flat { signal_id: boolean } for CPPN toggles
         * @param {HTMLCanvasElement} [contextCanvas]
         * @param {Object} [context] - Optional { canvas, gridPosition, neighbors, patternId, ... }
         */
        renderFrameWithSignals(runtime, signalState, contextCanvas, context = {}) {
            const signalContext =
                contextCanvas != null || context.canvas != null
                    ? { ...context, canvas: contextCanvas ?? context.canvas }
                    : { ...context };

            const signalValues = this._getSignalValues(signalContext);

            const representation =
                window.RepresentationRegistry?.currentRepresentation?.();
            const substrate = representation?.substrate;
            const phenotype = representation?.phenotype;

            const params = substrate?.buildParams?.(phenotype, signalValues) ?? {};
            substrate?.render?.(runtime, params, signalState || {});
        }
    }

    window.AnimationLoop = new AnimationLoop();
})();
