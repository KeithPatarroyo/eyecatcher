/**
 * Animation loop: mouse tracking, time modes (loop/oscillate/infinite), and per-frame pattern rendering.
 * Signal values come from a pluggable SignalSource. Set window.SignalSource before init, or pass signalSource in init().
 */
(function () {
    "use strict";

    var ANIMATION_SPEED = 0.005;
    var MOUSE_SPEED_DECAY = 0.95;
    var MOUSE_SPEED_SCALE = 0.005;
    var MOUSE_DIST_SCALE = 300;
    var ACTIVITY_DECAY = 0.985;
    var ACTIVITY_BOOST = 0.15;

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
        }

        _getMouseDistanceToCanvas(canvas) {
            var rect = canvas.getBoundingClientRect();
            var centerX = rect.left + rect.width / 2;
            var centerY = rect.top + rect.height / 2;
            var dx = this._mouseX - centerX;
            var dy = this._mouseY - centerY;
            var dist = Math.sqrt(dx * dx + dy * dy);
            return Math.min(1.0, dist / MOUSE_DIST_SCALE);
        }

        _buildDefaultSignalValues(context) {
            var canvas = context && context.canvas;
            var mouse_dist = canvas ? this._getMouseDistanceToCanvas(canvas) : 0;
            var rect = canvas ? canvas.getBoundingClientRect() : null;
            var mouse_x = rect
                ? Math.min(1.0, Math.max(0.0, (this._mouseX - rect.left) / rect.width))
                : 0.5;
            var mouse_y = rect
                ? Math.min(1.0, Math.max(0.0, (this._mouseY - rect.top) / rect.height))
                : 0.5;
            var computed = {
                raw_time: this._animationTime,
                mouse_speed: this._mouseSpeed,
                mouse_dist: mouse_dist,
                activity: this._activity,
                mouse_x: mouse_x,
                mouse_y: mouse_y,
            };
            if (context && context.gridPosition) {
                var pos = context.gridPosition;
                var GT = window.GridTopology;
                var cols = (GT && GT.getColumns && GT.getColumns()) || 1;
                var total = GT && GT.getAll && GT.getAll() ? GT.getAll().size : 1;
                var rows = cols > 0 ? Math.ceil(total / cols) : 1;
                computed.grid_row = rows > 1 ? pos.row / (rows - 1) : 0;
                computed.grid_col = cols > 1 ? pos.col / (cols - 1) : 0;
            }
            var signalIds =
                (window.EvolutionConfigSignals &&
                    window.EvolutionConfigSignals.SIGNAL_IDS) ||
                Object.keys(computed);
            var out = {};
            signalIds.forEach(function (id) {
                out[id] = computed[id] !== undefined ? computed[id] : 0.0;
            });
            return out;
        }

        getActiveSignalSource() {
            return this._signalSource || this._defaultSource;
        }

        getSignalValues(canvas) {
            var source = this.getActiveSignalSource();
            if (source && typeof source.getValues === "function") {
                return source.getValues({ canvas: canvas || undefined });
            }
            var ids =
                (window.EvolutionConfig && window.EvolutionConfig.SIGNAL_IDS) || [];
            var out = {};
            ids.forEach(function (id) {
                out[id] = id === "raw_time" ? 0.5 : 0;
            });
            return Object.keys(out).length ? out : { raw_time: 0.5 };
        }

        _animate() {
            var self = this;
            if (this._animating) {
                var timeMode =
                    (document.querySelector('input[name="timeMode"]:checked') &&
                        document.querySelector('input[name="timeMode"]:checked')
                            .value) ||
                    "oscillate";

                switch (timeMode) {
                    case "loop":
                        this._animationTime =
                            (this._animationTime + ANIMATION_SPEED) % 1.0;
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
                        this._animationTime =
                            (this._animationTime + ANIMATION_SPEED) % 1.0;
                }

                var normalizedTime = this._animationTime;
                this._mouseSpeed *= MOUSE_SPEED_DECAY;
                this._activity *= ACTIVITY_DECAY;

                var now = performance.now();
                var deltaTime =
                    this._lastFrameTime > 0 ? (now - this._lastFrameTime) / 1000 : 0;
                this._lastFrameTime = now;
                this._frameCount++;

                var patterns = this._getPatterns ? this._getPatterns() : null;
                if (
                    patterns &&
                    this._viewerControls &&
                    this._viewerControls.signalState != null &&
                    window.RepresentationRegistry
                ) {
                    var signalState = this._viewerControls.signalState;
                    var GT = window.GridTopology;
                    var RA = window.RepresentationRegistry;

                    patterns.forEach(function (runtime) {
                        if (!runtime.gl) return;
                        var patternId = runtime.patternId;
                        var renderContext = {
                            gl: runtime.gl,
                            canvas: runtime.canvas,
                            gridPosition: GT ? GT.getPosition(patternId) : null,
                            neighbors: GT ? GT.getNeighbors(patternId) : null,
                            frameCount: self._frameCount,
                            deltaTime: deltaTime,
                            patternId: patternId,
                        };
                        RA.renderFrameWithSignals(
                            runtime,
                            signalState,
                            runtime.canvas,
                            renderContext
                        );
                    });
                }

                if (
                    typeof window.EyecatcherDebug !== "undefined" &&
                    window.EyecatcherDebug.update
                ) {
                    window.EyecatcherDebug.update({
                        time: normalizedTime,
                        mouseSpeed: this._mouseSpeed,
                        activity: this._activity,
                        mouseX: this._mouseX,
                        mouseY: this._mouseY,
                    });
                }
            }
            requestAnimationFrame(function () {
                self._animate();
            });
        }

        init(options) {
            this._getPatterns = (options && options.getPatterns) || null;
            this._viewerControls = (options && options.viewerControls) || null;
            var self = this;
            this._defaultSource = {
                getValues: function (context) {
                    return self._buildDefaultSignalValues(context || {});
                },
            };
            this._signalSource =
                (options && options.signalSource) ||
                window.SignalSource ||
                this._defaultSource;
            window.getSignalSource = this.getActiveSignalSource.bind(this);
            this._lastMouseTime = performance.now();

            document.addEventListener("mousemove", function (e) {
                var now = performance.now();
                var dt = now - self._lastMouseTime;

                self._mouseX = e.clientX;
                self._mouseY = e.clientY;

                if (dt > 0) {
                    var dx = e.clientX - self._lastMouseX;
                    var dy = e.clientY - self._lastMouseY;
                    var distance = Math.sqrt(dx * dx + dy * dy);
                    var instantSpeed = distance / dt;
                    self._mouseSpeed = Math.min(
                        1.0,
                        self._mouseSpeed * 0.7 + instantSpeed * MOUSE_SPEED_SCALE * 0.3
                    );
                }

                self._lastMouseX = e.clientX;
                self._lastMouseY = e.clientY;
                self._lastMouseTime = now;
                self._activity = Math.min(
                    1.0,
                    self._activity + self._mouseSpeed * ACTIVITY_BOOST
                );
            });

            var timeModeRadios = document.querySelectorAll('input[name="timeMode"]');
            timeModeRadios.forEach(function (radio) {
                radio.addEventListener("change", function () {
                    self._animationTime = 0;
                    self._oscillatePhase = 0;
                });
            });
        }

        start() {
            this._animating = true;
            this._lastFrameTime = performance.now();
            this._animate();
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

        getTime() {
            return this._animationTime;
        }

        getFrameCount() {
            return this._frameCount;
        }
    }

    window.AnimationLoop = new AnimationLoop();
})();
