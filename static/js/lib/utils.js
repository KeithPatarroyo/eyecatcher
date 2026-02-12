/**
 * Shared pure helpers for the frontend.
 * Exposes: formatBytes, escapeHtml, showLoading, safeGetItem, safeSetItem,
 * formatApiError, createListEmptyEl, onId, and constants BYTES_KB, BYTES_MB.
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
        if (el) el.classList.toggle("hidden", !show);
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

    /**
     * Get a user-facing error message from an API error (supports e.data.error and e.message).
     * @param {Error|{data?:{error?:string}, message?:string}} e
     * @param {string} fallback
     * @returns {string}
     */
    function formatApiError(e, fallback) {
        if (!e) return fallback;
        if (e.data && typeof e.data.error === "string") return e.data.error;
        if (typeof e.message === "string") return e.message;
        return fallback;
    }

    /**
     * Create an empty-state element (e.g. "No items yet") with class list-empty.
     * @param {string} tag - "li" or "div"
     * @param {string} text - Message text
     * @returns {HTMLElement}
     */
    function createListEmptyEl(tag, text) {
        var el = document.createElement(tag);
        el.className = "list-empty";
        el.textContent = text;
        return el;
    }

    /**
     * Run a callback with the element for the given id, if present.
     * @param {string} id - Element id
     * @param {function(HTMLElement): void} fn - Callback given the element
     */
    function onId(id, fn) {
        var el = document.getElementById(id);
        if (el) fn(el);
    }

    window.Utils = {
        formatBytes: formatBytes,
        escapeHtml: escapeHtml,
        showLoading: showLoading,
        safeGetItem: safeGetItem,
        safeSetItem: safeSetItem,
        formatApiError: formatApiError,
        createListEmptyEl: createListEmptyEl,
        onId: onId,
        BYTES_KB: BYTES_KB,
        BYTES_MB: BYTES_MB,
    };
    window.formatBytes = formatBytes;
    window.escapeHtml = escapeHtml;
    window.showLoading = showLoading;
})();
