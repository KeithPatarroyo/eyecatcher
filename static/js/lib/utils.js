/**
 * Shared pure helpers for the frontend.
 * Exposes: formatBytes, escapeHtml, showLoading, withLoading,
 * safeGetItem, safeSetItem, formatApiError, createListEmptyEl, onId, onRoleButtonKeydown,
 * and constants BYTES_KB, BYTES_MB.
 */

const BYTES_KB = 1024;
const BYTES_MB = 1024 * 1024;

let _populationLoader = null;
let _populationState = null;

function setPopulationRefs(loader, state) {
    _populationLoader = loader ?? null;
    _populationState = state ?? null;
}

const formatBytes = (n) => {
    if (n >= BYTES_MB) return `${(n / BYTES_MB).toFixed(1)} MB`;
    if (n >= BYTES_KB) return `${(n / BYTES_KB).toFixed(1)} KB`;
    return `${n} B`;
};

const escapeHtml = (s) => {
    const div = document.createElement("div");
    div.textContent = String(s ?? "");
    return div.innerHTML;
};

const showLoading = (show) => {
    const loader =
        _populationLoader?.showLoading ?? window.PopulationLoader?.showLoading;
    if (typeof loader === "function") return loader(Boolean(show));

    const el = document.getElementById("loading");
    if (el) el.classList.toggle("hidden", !show);
};

/**
 * Run an async function with loading state (UI + PopulationState).
 * Clears loading in finally, even on errors.
 * @param {() => Promise<any>} fn
 */
const withLoading = async (fn) => {
    const state = _populationState ?? window.PopulationState;
    showLoading(true);
    state?.dispatch?.({ type: "SET_LOADING", payload: true });

    try {
        return await fn();
    } finally {
        showLoading(false);
        state?.dispatch?.({ type: "SET_LOADING", payload: false });
    }
};

/**
 * Run an async task with optional button disable, loading state, and single error/finally path.
 * @param {Object} opts
 * @param {HTMLButtonElement|HTMLElement|null} [opts.button] - disabled during task, re-enabled in finally
 * @param {(show: boolean) => void} [opts.setLoading] - called with true before task, false in finally
 * @param {() => Promise<any>} opts.task - async function to run
 * @param {(err: any) => void} [opts.onError] - called on catch (e.g. toast + log)
 * @param {() => void} [opts.onFinally] - called in finally after re-enable and setLoading(false)
 */
const runTask = async (opts) => {
    const { button, setLoading, task, onError, onFinally } = opts || {};
    if (button) {
        button.disabled = true;
        if (button.setAttribute) button.setAttribute("aria-disabled", "true");
    }
    if (setLoading) setLoading(true);
    try {
        return await task();
    } catch (err) {
        if (onError) onError(err);
    } finally {
        if (button) {
            button.disabled = false;
            if (button.setAttribute) button.setAttribute("aria-disabled", "false");
        }
        if (setLoading) setLoading(false);
        if (onFinally) onFinally();
    }
};

/**
 * Safe storage get. Returns value or fallback on error or missing.
 * @param {Storage} storage
 * @param {string} key
 * @param {string|null} fallback
 */
const safeGetItem = (storage, key, fallback) => {
    try {
        const v = storage?.getItem?.(key);
        return v != null ? v : fallback;
    } catch {
        return fallback;
    }
};

/**
 * Safe storage set. Ignores errors (e.g. private mode).
 * @param {Storage} storage
 * @param {string} key
 * @param {string} value
 */
const safeSetItem = (storage, key, value) => {
    try {
        storage?.setItem?.(key, value);
    } catch {
        /* ignore */
    }
};

/**
 * Get a user-facing error message from an API error.
 * Supports e.data.error and e.message.
 * @param {any} e
 * @param {string} fallback
 */
const formatApiError = (e, fallback) => {
    if (!e) return fallback;
    const apiError = e?.data?.error;
    if (typeof apiError === "string") return apiError;
    if (typeof e?.message === "string") return e.message;
    return fallback;
};

/**
 * Create an empty-state element (e.g. "No items yet") with class list-empty.
 * @param {"li"|"div"|"p"|string} tag
 * @param {string} text
 */
const createListEmptyEl = (tag, text) => {
    const el = document.createElement(tag);
    el.className = "list-empty";
    el.textContent = text;
    return el;
};

/**
 * Run a callback with the element for the given id, if present.
 * @param {string} id
 * @param {(el: HTMLElement) => void} fn
 */
const onId = (id, fn) => {
    const el = document.getElementById(id);
    if (el) fn(el);
};

/**
 * Attach click and keydown (Enter/Space) to a button-like element.
 * @param {HTMLElement} el
 * @param {() => void} fn
 */
const onRoleButtonKeydown = (el, fn) => {
    if (!el) return;
    el.addEventListener("click", fn);
    el.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            fn();
        }
    });
};

const Utils = {
    formatBytes,
    escapeHtml,
    showLoading,
    withLoading,
    runTask,
    safeGetItem,
    safeSetItem,
    formatApiError,
    createListEmptyEl,
    onId,
    onRoleButtonKeydown,
    setPopulationRefs,
    BYTES_KB,
    BYTES_MB,
};

export {
    formatBytes,
    escapeHtml,
    showLoading,
    withLoading,
    runTask,
    setPopulationRefs,
};
export default Utils;

window.Utils = Utils;
window.formatBytes = formatBytes;
window.escapeHtml = escapeHtml;
window.showLoading = showLoading;
