/**
 * ApiClient: wrapper around backend REST API.
 */
const DEFAULT_TIMEOUT_MS = 45_000;

const joinUrl = (base, path) => {
    const b = (base || "").replace(/\/+$/, "");
    const p = String(path || "").replace(/^\/+/, "");
    return b ? `${b}/${p}` : `/${p}`;
};

const buildError = async (res, fallback) => {
    let data = null;
    try {
        data = await res.json();
    } catch {
        /* ignore */
    }

    const msg =
        data?.error || data?.message || `${fallback} (${res.status} ${res.statusText})`;

    const err = new Error(msg);
    err.status = res.status;
    err.data = data;
    return err;
};

const fetchJson = async (url, opts = {}) => {
    const {
        method = "GET",
        body,
        timeoutMs = DEFAULT_TIMEOUT_MS,
        headers = {},
        signal,
    } = opts;

    const controller = !signal ? new AbortController() : null;
    const effectiveSignal = signal || controller.signal;

    const timer =
        controller &&
        setTimeout(() => {
            try {
                controller.abort();
            } catch {
                /* ignore */
            }
        }, timeoutMs);

    try {
        const res = await fetch(url, {
            method,
            headers: {
                "Content-Type": "application/json",
                ...headers,
            },
            body: body !== undefined ? JSON.stringify(body) : undefined,
            signal: effectiveSignal,
        });

        if (!res.ok) throw await buildError(res, "Request failed");
        // Some endpoints may respond with empty body; tolerate that.
        const text = await res.text();
        return text ? JSON.parse(text) : null;
    } finally {
        if (timer) clearTimeout(timer);
    }
};

/**
 * Single entry point: call API and return { ok, data } or { ok: false, error, status?, data? }.
 * Does not throw on HTTP errors; use for consistent error handling and toast in one place.
 */
const request = async (url, opts = {}) => {
    const {
        method = "GET",
        body,
        timeoutMs = DEFAULT_TIMEOUT_MS,
        headers = {},
        signal,
    } = opts;

    const controller = !signal ? new AbortController() : null;
    const effectiveSignal = signal || controller.signal;
    const timer =
        controller &&
        setTimeout(() => {
            try {
                controller.abort();
            } catch {
                /* ignore */
            }
        }, timeoutMs);

    try {
        const res = await fetch(url, {
            method,
            headers: {
                "Content-Type": "application/json",
                ...headers,
            },
            body: body !== undefined ? JSON.stringify(body) : undefined,
            signal: effectiveSignal,
        });

        let data = null;
        const text = await res.text();
        if (text) {
            try {
                data = JSON.parse(text);
            } catch {
                data = { message: text };
            }
        }

        if (!res.ok) {
            const err = await buildError(res, "Request failed");
            return {
                ok: false,
                error: err.message,
                status: err.status,
                data: err.data ?? data,
            };
        }
        return { ok: true, data };
    } catch (e) {
        const msg = e?.message ?? String(e);
        return { ok: false, error: msg, status: e?.status, data: e?.data };
    } finally {
        if (timer) clearTimeout(timer);
    }
};

class ApiClient {
    constructor() {
        this._baseUrl = "";
    }

    init(baseUrl) {
        this._baseUrl = baseUrl || "";
    }

    _url(path) {
        return joinUrl(this._baseUrl, path);
    }

    /**
     * Request that returns { ok, data } or { ok: false, error, status?, data? }. Use with toastError for one error path.
     */
    async request(pathOrUrl, opts = {}) {
        const url =
            pathOrUrl.startsWith("http") || pathOrUrl.startsWith("/")
                ? pathOrUrl
                : this._url(pathOrUrl);
        return request(url, opts);
    }

    get(pathOrUrl, opts = {}) {
        return this.request(pathOrUrl, { ...opts, method: "GET" });
    }

    post(pathOrUrl, body, opts = {}) {
        return this.request(pathOrUrl, { ...opts, method: "POST", body });
    }

    /**
     * If result is not ok, show toast and log. Call after get/post when you want a single error path.
     */
    toastError(result, title = "Error") {
        if (result?.ok) return;
        const msg = result?.error ?? "Request failed";
        if (window.Toast?.show) window.Toast.show(title, msg, "error");
        console.warn(`[ApiClient] ${title}:`, msg);
    }

    /**
     * Low-level fetch wrapper for callers that build their own URL and options.
     * Body should already be JSON.stringify'd if present.
     * @param {string} url - full URL
     * @param {RequestInit} opts - raw fetch options
     * @param {string} [fallbackError] - error message if response is not ok
     * @returns {Promise<any>}
     */
    async apiFetch(url, opts = {}, fallbackError = "Request failed") {
        const res = await fetch(url, opts);
        if (!res.ok) throw await buildError(res, fallbackError);
        const text = await res.text();
        return text ? JSON.parse(text) : null;
    }

    // ---- Config ----
    fetchConfig() {
        return fetchJson(this._url("/api/config"));
    }

    patchConfig(partialConfig) {
        return fetchJson(this._url("/api/config"), {
            method: "PATCH",
            body: partialConfig,
        });
    }

    // ---- Random population ----
    randomPopulation(size) {
        return fetchJson(this._url("/api/random"), {
            method: "POST",
            body: { size },
        });
    }

    // ---- Evolution / express pipeline ----
    develop(genomes, colorMode) {
        return fetchJson(this._url("/api/develop"), {
            method: "POST",
            body: { individuals: genomes, color_mode: colorMode },
        });
    }

    express(genomes, inputs, expressOptions) {
        return fetchJson(this._url("/api/express"), {
            method: "POST",
            body: {
                individuals: genomes,
                inputs: inputs || {},
                options: expressOptions || undefined,
            },
        });
    }

    evolve(parents, populationSize, opts = {}) {
        return fetchJson(this._url("/api/evolve"), {
            method: "POST",
            body: {
                parents,
                population_size: populationSize,
                parent_population_id: opts.parentPopulationId,
                generation_num: opts.generationNum,
                branch_name: opts.branchName,
            },
        });
    }

    save(id, genome) {
        return fetchJson(this._url("/api/save"), {
            method: "POST",
            body: { id, individual: genome },
            timeoutMs: 120_000, // compiling can take longer
        });
    }

    // ---- Community ----
    communityList() {
        return fetchJson(this._url("/api/community"));
    }

    communitySubmit(payload) {
        return fetchJson(this._url("/api/community/submit"), {
            method: "POST",
            body: payload,
        });
    }

    communityLoad(ids) {
        return fetchJson(this._url("/api/community/load"), {
            method: "POST",
            body: { ids },
        });
    }

    communityAdminList(adminKey) {
        return fetchJson(this._url("/api/admin/submissions"), {
            method: "GET",
            headers: { "X-Admin-Key": adminKey },
        });
    }

    communityAdminDelete(adminKey, ids) {
        return fetchJson(this._url("/api/community/admin/delete"), {
            method: "POST",
            body: { admin_key: adminKey, ids },
        });
    }

    // ---- Genealogy ----
    genealogyCreatePopulation(name) {
        return fetchJson(this._url("/api/genealogy/create_population"), {
            method: "POST",
            body: { name },
        });
    }

    genealogySaveGeneration(payload) {
        return fetchJson(this._url("/api/genealogy/save_generation"), {
            method: "POST",
            body: payload,
        });
    }

    genealogyListPopulations() {
        return fetchJson(this._url("/api/genealogy/list_populations"));
    }

    genealogyListBranches(populationId) {
        return fetchJson(this._url("/api/genealogy/list_branches"), {
            method: "POST",
            body: { population_id: populationId },
        });
    }

    genealogyLoadGeneration(payload) {
        return fetchJson(this._url("/api/genealogy/load_generation"), {
            method: "POST",
            body: payload,
        });
    }
}

export default ApiClient;
window.ApiClient = new ApiClient();
