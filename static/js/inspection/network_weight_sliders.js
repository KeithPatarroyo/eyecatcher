// network_weight_sliders.js (replace whole file)
(() => {
    "use strict";

    const WEIGHT_MIN = -5;
    const WEIGHT_MAX = 5;
    const DEBOUNCE_MS = 120;

    let _deps = null;
    const pending = new Map(); // key -> timeoutId

    const toastError = (title, msg) => window.Toast?.show?.(title, msg, "error");

    const debounceKey = (individualId, networkType, source, target) =>
        `${individualId}::${networkType}::${source}::${target}`;

    const applyWeightChange = async (
        individualId,
        connection,
        networkType,
        newWeight
    ) => {
        if (!_deps || typeof _deps.getGenomeForPattern !== "function") return;

        const genome = await _deps.getGenomeForPattern(individualId);
        if (!genome) {
            toastError("Weight update failed", "Could not find genome data");
            return;
        }

        try {
            const data = await window.ApiClient.apiFetch(
                `${_deps.apiUrl}/api/adjust-weight`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        individual: genome,
                        network: networkType,
                        source: connection.source,
                        target: connection.target,
                        weight: newWeight,
                    }),
                },
                "Weight update failed"
            );

            if (data.status !== "success") {
                toastError("Weight update failed", data.error || "Server error");
                return;
            }

            _deps.updatePatternRule?.(individualId, data.rule);

            const updatedGenome = data.individual ?? data.genome;
            if (
                _deps.onGenomeUpdated &&
                updatedGenome &&
                typeof _deps.getCurrentPopulation === "function"
            ) {
                const pop = _deps.getCurrentPopulation();
                const idx = Array.isArray(pop)
                    ? pop.findIndex((p) => p.id === individualId)
                    : -1;
                if (idx >= 0) _deps.onGenomeUpdated(individualId, idx, updatedGenome);
            }

            _deps.updateNetworkEdgeWeight?.(
                individualId,
                connection.source,
                connection.target,
                newWeight,
                networkType
            );
        } catch (err) {
            toastError("Weight update failed", err?.message || "Network error");
        }
    };

    const createWeightSlider = (
        individualId,
        connection,
        networkType,
        container,
        labelMap
    ) => {
        const tpl = document.getElementById("weight-slider-row-tpl");
        const item = tpl?.content
            ?.cloneNode(true)
            ?.querySelector?.(".weight-slider-item");
        if (!item) return;

        item.dataset.networkType = networkType;
        item.dataset.source = connection.source;
        item.dataset.target = connection.target;
        item.classList.add(`network-${networkType}`);

        const srcLabel =
            labelMap?.[connection.source] ??
            _deps?.extractNodeLabel?.(connection.source) ??
            connection.source;
        const tgtLabel =
            labelMap?.[connection.target] ??
            _deps?.extractNodeLabel?.(connection.target) ??
            connection.target;

        item.querySelector(".weight-slider-label").textContent =
            `${srcLabel} → ${tgtLabel}`;

        const slider = item.querySelector("input");
        const valueEl = item.querySelector(".weight-value");
        const setValue = (w) => (valueEl.textContent = Number(w).toFixed(2));

        slider.min = WEIGHT_MIN;
        slider.max = WEIGHT_MAX;
        slider.step = "0.05";
        slider.value = connection.weight;
        setValue(connection.weight);

        slider.addEventListener("input", (e) => {
            const w = Number(e.target.value);
            setValue(w);

            const key = debounceKey(
                individualId,
                networkType,
                connection.source,
                connection.target
            );
            const prev = pending.get(key);
            if (prev) clearTimeout(prev);

            pending.set(
                key,
                setTimeout(() => {
                    pending.delete(key);
                    applyWeightChange(individualId, connection, networkType, w);
                }, DEBOUNCE_MS)
            );
        });

        container.appendChild(item);
    };

    const setupWeightSliders = (individualId, data) => {
        const panel = document.getElementById("weight-adjustment-panel");
        const container = document.getElementById("weight-sliders-container");
        if (!panel || !container) return;
        if (!_deps?.getNetworkTypesFromData) return;

        const connections = data?.connections ?? [];
        if (!connections.length) {
            panel.classList.add("hidden");
            return;
        }

        container.innerHTML = "";
        panel.classList.remove("hidden");

        const labelMap = {};
        (data?.nodes ?? []).forEach((n) => (labelMap[n.id] = n.label));

        for (const networkType of _deps.getNetworkTypesFromData(data)) {
            for (const conn of connections.filter((c) => c.network === networkType)) {
                createWeightSlider(
                    individualId,
                    conn,
                    networkType,
                    container,
                    labelMap
                );
            }
        }
    };

    const scrollToWeightSlider = (sourceNodeId, targetNodeId) => {
        const items = document.querySelectorAll(".weight-slider-item");
        items.forEach((n) => n.classList.remove("highlighted"));

        for (const item of items) {
            if (
                item.dataset.source === sourceNodeId &&
                item.dataset.target === targetNodeId
            ) {
                item.classList.add("highlighted");
                item.scrollIntoView({ behavior: "smooth", block: "center" });
                setTimeout(() => item.classList.remove("highlighted"), 2000);
                return;
            }
        }
    };

    const init = (deps) => {
        _deps = deps || null;
    };

    window.NetworkWeightSliders = { init, setupWeightSliders, scrollToWeightSlider };
})();
