/**
 * API client for Eyecatcher backend. Raw fetch calls; no UI.
 * Sets window.API_URL and window.DEFAULT_DEV_PORT. Exposes: ApiClient.init(apiUrl),
 * ApiClient.compile(individuals), ApiClient.evolve(parents, populationSize),
 * ApiClient.save(id, individual), ApiClient.randomPopulation(size)
 */
(function () {
    "use strict";

    var DEFAULT_DEV_PORT =
        (typeof window !== "undefined" &&
            window.EvolutionConfig &&
            window.EvolutionConfig.DEFAULT_DEV_PORT) ||
        5001;

    function getApiBaseUrl() {
        if (
            typeof window !== "undefined" &&
            window.location &&
            window.location.origin &&
            window.location.protocol &&
            window.location.protocol.indexOf("http") === 0
        ) {
            return window.location.origin + "/api";
        }
        return "http://localhost:" + DEFAULT_DEV_PORT + "/api";
    }

    window.DEFAULT_DEV_PORT = DEFAULT_DEV_PORT;
    window.API_URL = getApiBaseUrl();

    class ApiClient {
        constructor() {
            this._apiUrl = "";
        }

        init(apiUrl) {
            this._apiUrl = apiUrl || "";
        }

        getBase() {
            return this._apiUrl || getApiBaseUrl();
        }

        /**
         * Generic fetch that parses JSON and throws on !r.ok with data.error or defaultMessage.
         * @param {string} url - Full URL
         * @param {RequestInit} [options] - fetch options
         * @param {string} [defaultMessage] - Error message when response has no data.error
         */
        async apiFetch(url, options, defaultMessage) {
            var r = await fetch(url, options || {});
            var data = await r.json().catch(function () {
                return {};
            });
            if (!r.ok) {
                var err = new Error(
                    data.error || defaultMessage || "Request failed (" + r.status + ")"
                );
                err.status = r.status;
                err.data = data;
                throw err;
            }
            return data;
        }

        async compile(individuals, colorMode) {
            var payload = individuals.map(function (g) {
                var copy = Object.assign({}, g);
                copy.clicks = 0;
                return copy;
            });
            var body = { individuals: payload };
            if (colorMode === "hsv" || colorMode === "rgb") body.color_mode = colorMode;
            return this.apiFetch(
                this.getBase() + "/compile",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(body),
                },
                "Compile failed"
            );
        }

        async evolve(parents, populationSize, genealogy) {
            var parentsPayload = (parents || []).map(function (p) {
                return {
                    individual: p.genome || p,
                    fitness: p.fitness != null ? p.fitness : p.clicks || 0,
                };
            });
            var body = {
                parents: parentsPayload,
                population_size: populationSize,
            };
            if (genealogy) {
                if (genealogy.parentPopulationId != null)
                    body.parent_population_id = genealogy.parentPopulationId;
                if (genealogy.generationNum != null)
                    body.generation_num = genealogy.generationNum;
                if (genealogy.branchName) body.branch_name = genealogy.branchName;
            }
            var data = await this.apiFetch(
                this.getBase() + "/evolve",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(body),
                },
                "Evolve failed"
            );
            if (!Array.isArray(data.children)) {
                throw new Error("Evolve failed: no children in response");
            }
            return data;
        }

        async save(id, individual) {
            return this.apiFetch(
                this.getBase() + "/save",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ id: id, individual: individual }),
                },
                "Save failed"
            );
        }

        async fetchConfig() {
            var data = await this.apiFetch(
                this.getBase() + "/config",
                { method: "GET" },
                "Config failed"
            );
            if (typeof window !== "undefined") {
                window.ServerConfig = data;
            }
            return data;
        }

        async patchConfig(updates) {
            var data = await this.apiFetch(
                this.getBase() + "/config",
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(updates || {}),
                },
                "Update config failed"
            );
            if (typeof window !== "undefined") {
                window.ServerConfig = data;
            }
            return data;
        }

        async randomPopulation(size) {
            return this.apiFetch(
                this.getBase() + "/random",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ size: size }),
                },
                "Failed to create random population"
            );
        }

        async evaluate(individuals) {
            return this.apiFetch(
                this.getBase() + "/evaluate",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ individuals: individuals }),
                },
                "Evaluate failed"
            );
        }
    }

    window.ApiClient = new ApiClient();
})();
