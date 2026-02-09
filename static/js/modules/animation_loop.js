/**
 * Animation loop: mouse tracking, time modes (loop/oscillate/infinite), and per-frame pattern rendering.
 * Exposes: AnimationLoop.init(), AnimationLoop.start(), AnimationLoop.stop(),
 *   AnimationLoop.getMouseSpeed(), AnimationLoop.getMouseDistance(canvas),
 *   AnimationLoop.getActivity(), AnimationLoop.getMouseX(), AnimationLoop.getMouseY(), AnimationLoop.getTime()
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
    let _renderPattern = null;

    function getMouseDistanceToCanvas(canvas) {
        const rect = canvas.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const dx = mouseX - centerX;
        const dy = mouseY - centerY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        return Math.min(1.0, dist / MOUSE_DIST_SCALE);
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

            const patterns = _getPatterns ? _getPatterns() : null;
            if (patterns && _renderPattern) {
                patterns.forEach(function (patternData) {
                    const mouseDist = getMouseDistanceToCanvas(patternData.canvas);
                    _renderPattern(
                        patternData,
                        normalizedTime,
                        mouseSpeed,
                        mouseDist,
                        activity
                    );
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
        _renderPattern = options.renderPattern || null;
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
        requestAnimationFrame(animate);
    }

    function stop() {
        animating = false;
    }

    window.AnimationLoop = {
        init: init,
        start: start,
        stop: stop,
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
    };
})();
