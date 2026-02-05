/**
 * Pattern grid zoom and CPPN signal checkbox state.
 * Exposes: ZoomSignals.patternZoom, ZoomSignals.signalState, ZoomSignals.applyZoom(), ZoomSignals.init()
 */
(function () {
    'use strict';

    const ZOOM_MIN = 0.5;
    const ZOOM_MAX = 2.0;
    const ZOOM_STEP = 0.10;

    const ZoomSignals = {
        patternZoom: 1.0,
        signalState: {
            time: { rawTime: true, mouseSpeed: true, mouseDist: true, inactivity: true },
            visual: { time: true, mouseSpeed: true, mouseDist: true, inactivity: true }
        },
        applyZoom: function () {
            document.documentElement.style.setProperty('--pattern-zoom', String(this.patternZoom));
            const label = document.getElementById('zoom-label');
            if (label) label.textContent = Math.round(this.patternZoom * 100) + '%';
        },
        init: function () {
            const self = this;
            ['rawTime', 'mouseSpeed', 'mouseDist', 'inactivity'].forEach(function (sig) {
                const checkbox = document.getElementById('time-' + sig);
                if (checkbox) {
                    checkbox.addEventListener('change', function (e) {
                        self.signalState.time[sig] = e.target.checked;
                    });
                }
            });
            ['time', 'mouseSpeed', 'mouseDist', 'inactivity'].forEach(function (sig) {
                const checkbox = document.getElementById('visual-' + sig);
                if (checkbox) {
                    checkbox.addEventListener('change', function (e) {
                        self.signalState.visual[sig] = e.target.checked;
                    });
                }
            });
            const zoomIn = document.getElementById('zoom-in');
            const zoomOut = document.getElementById('zoom-out');
            if (zoomIn) {
                zoomIn.addEventListener('click', function () {
                    self.patternZoom = Math.min(ZOOM_MAX, self.patternZoom + ZOOM_STEP);
                    self.applyZoom();
                });
                zoomIn.addEventListener('keydown', function (e) {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        zoomIn.click();
                    }
                });
            }
            if (zoomOut) {
                zoomOut.addEventListener('click', function () {
                    self.patternZoom = Math.max(ZOOM_MIN, self.patternZoom - ZOOM_STEP);
                    self.applyZoom();
                });
                zoomOut.addEventListener('keydown', function (e) {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        zoomOut.click();
                    }
                });
            }
            this.applyZoom();
        }
    };

    window.ZoomSignals = ZoomSignals;
})();
