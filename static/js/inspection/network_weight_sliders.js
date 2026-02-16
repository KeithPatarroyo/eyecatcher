// network_weight_sliders.js (replace whole file)
import Toast from "../lib/toast.js";
import api from "../lib/api_client.js";
import DOM from "../lib/dom.js";

const WEIGHT_MIN = -5;
const WEIGHT_MAX = 5;
const DEBOUNCE_MS = 120;

let _deps = null;
/** Debounce cache: key -> timeoutId (not canonical state). */
const pending = new Map();

const toastError = (title, msg) => Toast.show(title, msg, "error");

const debounceKey = (individualId, networkType, source, target) =>
    `${individualId}::${networkType}::${source}::${target}`;

const applyWeightChange = async (individualId, connection, networkType, newWeight) => {
    if (!_deps || typeof _deps.getGenomeForPattern !== "function") return;

    const genome = await _deps.getGenomeForPattern(individualId);
    if (!genome) {
        toastError("Weight update failed", "Could not find genome data");
        return;
    }

    try {
        const data = await api.apiFetch(
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
    const tpl = DOM.byId("weight-slider-row-tpl");
    const srcLabel =
        labelMap?.[connection.source] ??
        _deps?.extractNodeLabel?.(connection.source) ??
        connection.source;
    const tgtLabel =
        labelMap?.[connection.target] ??
        _deps?.extractNodeLabel?.(connection.target) ??
        connection.target;
    const item = DOM.cloneAndFill(tpl, ".weight-slider-item", {
        ".weight-slider-label": `${srcLabel} → ${tgtLabel}`,
    });
    if (!item) return;

    item.dataset.networkType = networkType;
    item.dataset.source = connection.source;
    item.dataset.target = connection.target;
    item.classList.add(`network-${networkType}`);

    const slider = DOM.qs("input", item);
    const valueEl = DOM.qs(".weight-value", item);
    if (slider) {
        slider.min = WEIGHT_MIN;
        slider.max = WEIGHT_MAX;
        slider.step = "0.05";
        slider.value = connection.weight;
    }
    if (valueEl) valueEl.textContent = Number(connection.weight).toFixed(2);

    container.appendChild(item);
};

function attachWeightSliderDelegation(container) {
    if (container.dataset.weightDelegationBound === "true") return;
    container.dataset.weightDelegationBound = "true";

    DOM.on(container, "input", (e) => {
        const slider = e.target;
        if (slider.type !== "range" && slider.type !== "number") return;
        const item = slider.closest(".weight-slider-item");
        if (!item) return;

        const individualId = container.dataset.individualId;
        const networkType = item.dataset.networkType;
        const source = item.dataset.source;
        const target = item.dataset.target;
        const w = Number(slider.value);

        const valueEl = item.querySelector(".weight-value");
        if (valueEl) valueEl.textContent = w.toFixed(2);

        const key = debounceKey(individualId, networkType, source, target);
        const prev = pending.get(key);
        if (prev) clearTimeout(prev);
        pending.set(
            key,
            setTimeout(() => {
                pending.delete(key);
                applyWeightChange(
                    individualId,
                    { source, target, weight: w },
                    networkType,
                    w
                );
            }, DEBOUNCE_MS)
        );
    });
}

const setupWeightSliders = (individualId, data) => {
    const panel = DOM.byId("weight-adjustment-panel");
    const container = DOM.byId("weight-sliders-container");
    if (!panel || !container) return;
    if (!_deps?.getNetworkTypesFromData) return;

    const connections = data?.connections ?? [];
    if (!connections.length) {
        DOM.toggleClass(panel, "hidden", true);
        return;
    }

    container.innerHTML = "";
    DOM.toggleClass(panel, "hidden", false);
    container.dataset.individualId = individualId;
    attachWeightSliderDelegation(container);

    const labelMap = {};
    (data?.nodes ?? []).forEach((n) => (labelMap[n.id] = n.label));

    for (const networkType of _deps.getNetworkTypesFromData(data)) {
        for (const conn of connections.filter((c) => c.network === networkType)) {
            createWeightSlider(individualId, conn, networkType, container, labelMap);
        }
    }
};

const scrollToWeightSlider = (sourceNodeId, targetNodeId) => {
    const container = DOM.byId("weight-sliders-container");
    const items = container?.querySelectorAll?.(".weight-slider-item") ?? [];
    items.forEach((n) => DOM.toggleClass(n, "highlighted", false));

    for (const item of items) {
        if (
            item.dataset.source === sourceNodeId &&
            item.dataset.target === targetNodeId
        ) {
            DOM.toggleClass(item, "highlighted", true);
            item.scrollIntoView({ behavior: "smooth", block: "center" });
            setTimeout(() => DOM.toggleClass(item, "highlighted", false), 2000);
            return;
        }
    }
};

const init = (deps) => {
    _deps = deps || null;
};

window.NetworkWeightSliders = { init, setupWeightSliders, scrollToWeightSlider };
