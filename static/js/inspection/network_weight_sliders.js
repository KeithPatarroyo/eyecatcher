/**
 * Weight adjustment sliders for network sidebar.
 * Depends: Toast, ApiClient. Init with deps from NetworkVisualizer.
 * Exposes: init(), setupWeightSliders(), scrollToWeightSlider().
 */
(function () {
    "use strict";

    const WEIGHT_MIN = -5;
    const WEIGHT_MAX = 5;

    let _deps = null;

    function applyWeightChange(individualId, connection, networkType, newWeight) {
        if (!_deps || typeof _deps.getGenomeForPattern !== "function") {
            return Promise.resolve();
        }
        return _deps.getGenomeForPattern(individualId).then(function (genome) {
            if (!genome) {
                window.Toast.show(
                    "Weight update failed",
                    "Could not find genome data",
                    "error"
                );
                return;
            }
            return window.ApiClient.apiFetch(
                _deps.apiUrl + "/adjust-weight",
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
            )
                .then(function (data) {
                    if (data.status === "success") {
                        if (typeof _deps.updatePatternShader === "function") {
                            _deps.updatePatternShader(individualId, data.shader);
                        }
                        var updatedGenome =
                            data.individual != null ? data.individual : data.genome;
                        if (
                            typeof _deps.onGenomeUpdated === "function" &&
                            updatedGenome &&
                            typeof _deps.getCurrentPopulation === "function"
                        ) {
                            const pop = _deps.getCurrentPopulation();
                            if (pop && pop.length) {
                                const idx = pop.findIndex(function (p) {
                                    return p.id === individualId;
                                });
                                if (idx >= 0) {
                                    _deps.onGenomeUpdated(
                                        individualId,
                                        idx,
                                        updatedGenome
                                    );
                                }
                            }
                        }
                        if (typeof _deps.updateNetworkEdgeWeight === "function") {
                            _deps.updateNetworkEdgeWeight(
                                individualId,
                                connection.source,
                                connection.target,
                                newWeight,
                                networkType
                            );
                        }
                    } else {
                        window.Toast.show(
                            "Weight update failed",
                            data.error || "Server error",
                            "error"
                        );
                    }
                })
                .catch(function (err) {
                    window.Toast.show(
                        "Weight update failed",
                        err.message || "Network error",
                        "error"
                    );
                });
        });
    }

    function createWeightSlider(
        individualId,
        connection,
        networkType,
        container,
        labelMap,
        extractNodeLabel
    ) {
        const tpl = document.getElementById("weight-slider-row-tpl");
        if (!tpl || !tpl.content) return;
        const sliderDiv = tpl.content
            .cloneNode(true)
            .querySelector(".weight-slider-item");
        if (!sliderDiv) return;
        sliderDiv.setAttribute("data-network-type", networkType);
        sliderDiv.classList.add("network-" + networkType);
        if (networkType === "time") sliderDiv.classList.add("time-network");
        const sourceLabel =
            (labelMap && labelMap[connection.source]) ||
            (extractNodeLabel && extractNodeLabel(connection.source)) ||
            connection.source;
        const targetLabel =
            (labelMap && labelMap[connection.target]) ||
            (extractNodeLabel && extractNodeLabel(connection.target)) ||
            connection.target;
        const currentWeight = connection.weight;
        sliderDiv.setAttribute("data-source", connection.source);
        sliderDiv.setAttribute("data-target", connection.target);
        sliderDiv.querySelector(".weight-slider-label").textContent =
            sourceLabel + " \u2192 " + targetLabel;
        const slider = sliderDiv.querySelector("input");
        const valueDisplay = sliderDiv.querySelector(".weight-value");
        slider.min = WEIGHT_MIN;
        slider.max = WEIGHT_MAX;
        slider.step = "0.05";
        slider.value = currentWeight;
        slider.setAttribute("data-individual", individualId);
        slider.setAttribute("data-network", networkType);
        slider.setAttribute("data-source", connection.source);
        slider.setAttribute("data-target", connection.target);
        valueDisplay.textContent = currentWeight.toFixed(2);
        slider.addEventListener("input", function (e) {
            const newWeight = parseFloat(e.target.value, 10);
            valueDisplay.textContent = newWeight.toFixed(2);
            applyWeightChange(individualId, connection, networkType, newWeight);
        });
        container.appendChild(sliderDiv);
    }

    function setupWeightSliders(individualId, data) {
        const panel = document.getElementById("weight-adjustment-panel");
        const container = document.getElementById("weight-sliders-container");
        if (!panel || !container) return;
        if (!_deps || typeof _deps.getNetworkTypesFromData !== "function") return;
        if (!data.connections || data.connections.length === 0) {
            panel.classList.add("hidden");
            return;
        }
        container.innerHTML = "";
        panel.classList.remove("hidden");
        const nodeIdToLabel = {};
        if (data.nodes && data.nodes.length) {
            data.nodes.forEach(function (node) {
                nodeIdToLabel[node.id] = node.label;
            });
        }
        const networkTypes = _deps.getNetworkTypesFromData(data);
        networkTypes.forEach(function (networkType) {
            const conns = data.connections.filter(function (c) {
                return c.network === networkType;
            });
            conns.forEach(function (conn) {
                createWeightSlider(
                    individualId,
                    conn,
                    networkType,
                    container,
                    nodeIdToLabel,
                    _deps.extractNodeLabel
                );
            });
        });
    }

    function scrollToWeightSlider(sourceNodeId, targetNodeId) {
        const sliderItems = document.querySelectorAll(".weight-slider-item");
        sliderItems.forEach(function (item) {
            item.classList.remove("highlighted");
        });
        for (let i = 0; i < sliderItems.length; i++) {
            const item = sliderItems[i];
            if (
                item.getAttribute("data-source") === sourceNodeId &&
                item.getAttribute("data-target") === targetNodeId
            ) {
                item.classList.add("highlighted");
                item.scrollIntoView({ behavior: "smooth", block: "center" });
                setTimeout(function () {
                    item.classList.remove("highlighted");
                }, 2000);
                break;
            }
        }
    }

    function init(deps) {
        _deps = deps || null;
    }

    window.NetworkWeightSliders = {
        init: init,
        setupWeightSliders: setupWeightSliders,
        scrollToWeightSlider: scrollToWeightSlider,
    };
})();
