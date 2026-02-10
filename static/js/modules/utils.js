/**
 * Shared pure helpers for the frontend.
 * Exposes: formatBytes, escapeHtml, showLoading, safeGetItem, safeSetItem,
 * and constants BYTES_KB, BYTES_MB.
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

    /**
     * Safe storage get. Returns value or fallback on error or missing.
     * @param {Storage} storage - localStorage or sessionStorage
     * @param {string} key
     * @param {string|null} fallback
     * @returns {string|null}
     */
    function safeGetItem(storage, key, fallback) {
        try {
            if (typeof storage === "undefined" || !storage) return fallback;
            var v = storage.getItem(key);
            return v != null ? v : fallback;
        } catch (_e) {
            return fallback;
        }
    }

    /**
     * Safe storage set. Ignores errors (e.g. private mode).
     * @param {Storage} storage - localStorage or sessionStorage
     * @param {string} key
     * @param {string} value
     */
    function safeSetItem(storage, key, value) {
        try {
            if (typeof storage !== "undefined" && storage) storage.setItem(key, value);
        } catch (_e) {
            /* ignore */
        }
    }

    window.Utils = {
        formatBytes: formatBytes,
        escapeHtml: escapeHtml,
        showLoading: showLoading,
        safeGetItem: safeGetItem,
        safeSetItem: safeSetItem,
        BYTES_KB: BYTES_KB,
        BYTES_MB: BYTES_MB,
    };
    window.formatBytes = formatBytes;
    window.escapeHtml = escapeHtml;
    window.showLoading = showLoading;
})();
