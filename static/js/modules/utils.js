/**
 * Shared pure helpers for the frontend.
 * Exposes: formatBytes, escapeHtml, showLoading, and constants BYTES_KB, BYTES_MB.
 */
(function () {
    "use strict";

    var BYTES_KB = 1024;
    var BYTES_MB = 1024 * 1024;

    function formatBytes(n) {
        if (n >= BYTES_MB) return (n / BYTES_MB).toFixed(1) + " MB";
        if (n >= BYTES_KB) return (n / BYTES_KB).toFixed(1) + " KB";
        return n + " B";
    }

    function escapeHtml(s) {
        var div = document.createElement("div");
        div.textContent = s;
        return div.innerHTML;
    }

    function showLoading(show) {
        var el = document.getElementById("loading");
        if (el) el.style.display = show ? "block" : "none";
    }

    window.Utils = {
        formatBytes: formatBytes,
        escapeHtml: escapeHtml,
        showLoading: showLoading,
        BYTES_KB: BYTES_KB,
        BYTES_MB: BYTES_MB,
    };
    window.formatBytes = formatBytes;
    window.escapeHtml = escapeHtml;
    window.showLoading = showLoading;
})();
