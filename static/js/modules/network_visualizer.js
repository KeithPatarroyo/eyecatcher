/**
 * Network visualization module: CPPN sidebar, vis.js graph, weight sliders.
 * Depends: vis (global from CDN), showToast, base64ToBlob (from toast.js).
 * Call init() with dependencies before use. Exposes: toggle(), close(), fitToView(), exportNetwork().
 */
(function () {
    "use strict";

    let _apiUrl = "";
    let _getGenomeForPattern = null;
    let _updatePatternShader = null;
    let _onGenomeUpdated = null;
    let _getCurrentPopulation = null;

    const networkVisualizations = new Map();
    const networkEdges = new Map();
    const networkPhysicsState = new Map();
    let currentNetworkId = null;

    const nodeColors = {
        input: {
            background: "#0066cc",
            border: "#0052a3",
            highlight: { background: "#0080ff", border: "#0052a3" },
        },
        hidden: {
            background: "#28a745",
            border: "#1e7e34",
            highlight: { background: "#34c759", border: "#1e7e34" },
        },
        output: {
            background: "#dc3545",
            border: "#c82333",
            highlight: { background: "#ff3d4d", border: "#c82333" },
        },
    };

    const networkColors = {
        visual: { opacity: 1.0 },
        time: { opacity: 0.5 },
    };

    function extractNodeLabel(nodeId) {
        const parts = String(nodeId).split("_");
        if (parts.length >= 3) {
            const network = parts[0];
            const type = parts[1];
            const id = parts.slice(2).join("_");
            if (type === "input") {
                if (network === "time") {
                    const timeInputNames = {
                        "-1": "rawTime",
                        "-2": "mSpeed",
                        "-3": "mDist",
                        "-4": "inact",
                        "-5": "bias",
                    };
                    return timeInputNames[id] || "in" + id;
                }
                const visualInputNames = {
                    "-1": "x",
                    "-2": "y",
                    "-3": "dist",
                    "-4": "time",
                    "-5": "mSpeed",
                    "-6": "mDist",
                    "-7": "inact",
                    "-8": "bias",
                };
                return visualInputNames[id] || "in" + id;
            }
            if (type === "output") {
                if (network === "time") return "timeOut";
                const outputNames = { 0: "R", 1: "G", 2: "B" };
                return outputNames[id] || "out" + id;
            }
            if (type === "hidden") return "h" + id;
            return id;
        }
        return nodeId;
    }

    function visualizeNetworkInline(individualId, data, container) {
        if (typeof vis === "undefined") {
            if (typeof showToast === "function")
                showToast("Visualization error", "vis.js not loaded", "error");
            return;
        }
        try {
            const vizContainer = container.querySelector(".network-visualization");
            vizContainer.innerHTML = "";
            vizContainer.style.width = "100%";
            vizContainer.style.height = "100%";

            const nodes = new vis.DataSet();
            data.nodes.forEach(function (node) {
                const color = nodeColors[node.type];
                const network = node.network || "visual";
                const opacity = networkColors[network].opacity;
                let label = node.label;
                if (node.type === "hidden") {
                    label += "\nBias: " + node.bias.toFixed(2);
                    if (node.activation) label += "\n" + node.activation;
                }
                label += "\n[" + network + "]";
                const hex = Math.round(opacity * 255)
                    .toString(16)
                    .padStart(2, "0");
                const adjustedColor = {
                    background: color.background + hex,
                    border: color.border + hex,
                    highlight: {
                        background: color.highlight.background + hex,
                        border: color.highlight.border + hex,
                    },
                };
                nodes.add({
                    id: node.id,
                    label: label,
                    color: adjustedColor,
                    shape: "dot",
                    size: node.type === "hidden" ? 20 : 25,
                    font: { size: 9, color: "#fff", face: "monospace" },
                    physics: false,
                    x: node.x || undefined,
                    y: node.y || undefined,
                    title:
                        network.toUpperCase() +
                        " Node " +
                        node.id +
                        " (" +
                        node.type +
                        ")",
                });
            });

            const edges = new vis.DataSet();
            data.connections.forEach(function (conn) {
                const network = conn.network || "visual";
                const width = Math.max(0.5, Math.abs(conn.weight));
                const isPositive = conn.weight > 0;
                let color;
                if (network === "time") {
                    color = isPositive
                        ? "rgba(0, 150, 200, 0.3)"
                        : "rgba(200, 150, 0, 0.3)";
                } else {
                    color = isPositive
                        ? "rgba(0, 200, 100, 0.5)"
                        : "rgba(255, 100, 100, 0.5)";
                }
                edges.add({
                    from: conn.source,
                    to: conn.target,
                    label: "",
                    width: width,
                    color: color,
                    font: { size: 8, color: "#999" },
                    title: network.toUpperCase() + " Weight: " + conn.weight.toFixed(3),
                    arrows: "to",
                    smooth: { type: "continuous" },
                });
            });

            const options = {
                physics: { enabled: false },
                layout: { randomSeed: 42, improvedLayout: true },
                interaction: {
                    hover: true,
                    navigationButtons: false,
                    keyboard: false,
                    zoomView: true,
                    dragView: true,
                },
                nodes: { font: { face: "monospace", size: 9 } },
                edges: {
                    font: { size: 8, align: "middle" },
                    smooth: {
                        enabled: true,
                        type: "cubicBezier",
                        forceDirection: "vertical",
                    },
                },
            };

            const network = new vis.Network(
                vizContainer,
                { nodes: nodes, edges: edges },
                options
            );
            networkVisualizations.set(individualId, network);
            networkEdges.set(individualId, edges);
            networkPhysicsState.set(individualId, false);

            setupWeightSliders(individualId, data);

            network.on("selectEdge", function (params) {
                if (params.edges.length > 0) {
                    const edge = edges.get(params.edges[0]);
                    if (edge) scrollToWeightSlider(edge.from, edge.to);
                }
            });

            setTimeout(function () {
                const net = networkVisualizations.get(individualId);
                if (net) net.fit({ animation: { duration: 500 } });
            }, 100);
        } catch (err) {
            if (typeof showToast === "function")
                showToast(
                    "Visualization error",
                    err.message || "Failed to visualize network",
                    "error"
                );
        }
    }

    function setupWeightSliders(individualId, data) {
        const panel = document.getElementById("weight-adjustment-panel");
        const container = document.getElementById("weight-sliders-container");
        if (!panel || !container) return;
        if (!data.connections || data.connections.length === 0) {
            panel.style.display = "none";
            return;
        }
        container.innerHTML = "";
        panel.style.display = "flex";
        const visualConns = data.connections.filter(function (c) {
            return c.network === "visual";
        });
        const timeConns = data.connections.filter(function (c) {
            return c.network === "time";
        });
        visualConns.forEach(function (conn) {
            createWeightSlider(individualId, conn, "visual", container);
        });
        timeConns.forEach(function (conn) {
            createWeightSlider(individualId, conn, "time", container);
        });
    }

    function createWeightSlider(individualId, connection, networkType, container) {
        const isTimeNetwork = networkType === "time";
        const sliderDiv = document.createElement("div");
        sliderDiv.className =
            "weight-slider-item" + (isTimeNetwork ? " time-network" : "");
        const sourceLabel = extractNodeLabel(connection.source);
        const targetLabel = extractNodeLabel(connection.target);
        const minWeight = -5;
        const maxWeight = 5;
        const currentWeight = connection.weight;
        sliderDiv.setAttribute("data-source", connection.source);
        sliderDiv.setAttribute("data-target", connection.target);
        sliderDiv.innerHTML =
            '<div class="weight-slider-label">' +
            sourceLabel +
            " \u2192 " +
            targetLabel +
            "</div>" +
            '<div class="weight-slider-row">' +
            '<input type="range" class="weight-slider-input" min="' +
            minWeight +
            '" max="' +
            maxWeight +
            '" step="0.05" value="' +
            currentWeight +
            '" ' +
            'data-individual="' +
            individualId +
            '" data-network="' +
            networkType +
            '" data-source="' +
            connection.source +
            '" data-target="' +
            connection.target +
            '" />' +
            '<span class="weight-value">' +
            currentWeight.toFixed(2) +
            "</span></div>";
        const slider = sliderDiv.querySelector("input");
        const valueDisplay = sliderDiv.querySelector(".weight-value");

        slider.addEventListener("input", function (e) {
            const newWeight = parseFloat(e.target.value, 10);
            valueDisplay.textContent = newWeight.toFixed(2);
            if (typeof _getGenomeForPattern !== "function") return;
            _getGenomeForPattern(individualId).then(function (genome) {
                if (!genome) {
                    if (typeof showToast === "function")
                        showToast(
                            "Weight update failed",
                            "Could not find genome data",
                            "error"
                        );
                    return;
                }
                window.ApiClient.apiFetch(
                    _apiUrl + "/adjust-weight",
                    {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            genome: genome,
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
                            if (typeof _updatePatternShader === "function")
                                _updatePatternShader(individualId, data.shader);
                            if (
                                typeof _onGenomeUpdated === "function" &&
                                data.genome &&
                                typeof _getCurrentPopulation === "function"
                            ) {
                                const pop = _getCurrentPopulation();
                                if (pop && pop.length) {
                                    const idx = pop.findIndex(function (p) {
                                        return p.id === individualId;
                                    });
                                    if (idx >= 0)
                                        _onGenomeUpdated(
                                            individualId,
                                            idx,
                                            data.genome
                                        );
                                }
                            }
                            updateNetworkEdgeWeight(
                                individualId,
                                connection.source,
                                connection.target,
                                newWeight,
                                networkType
                            );
                        } else {
                            if (typeof showToast === "function")
                                showToast(
                                    "Weight update failed",
                                    data.error || "Server error",
                                    "error"
                                );
                        }
                    })
                    .catch(function (err) {
                        if (typeof showToast === "function")
                            showToast(
                                "Weight update failed",
                                err.message || "Network error",
                                "error"
                            );
                    });
            });
        });

        container.appendChild(sliderDiv);
    }

    function updateNetworkEdgeWeight(
        individualId,
        sourceId,
        targetId,
        newWeight,
        networkType
    ) {
        const edges = networkEdges.get(individualId);
        if (!edges) return;
        const allEdges = edges.get();
        for (let i = 0; i < allEdges.length; i++) {
            const edge = allEdges[i];
            if (edge.from === sourceId && edge.to === targetId) {
                const width = Math.max(0.5, Math.abs(newWeight));
                const isPositive = newWeight > 0;
                let color;
                if (networkType === "time") {
                    color = isPositive
                        ? "rgba(0, 150, 200, 0.3)"
                        : "rgba(200, 150, 0, 0.3)";
                } else {
                    color = isPositive
                        ? "rgba(0, 200, 100, 0.5)"
                        : "rgba(255, 100, 100, 0.5)";
                }
                edges.update({
                    id: edge.id,
                    width: width,
                    color: color,
                    title:
                        networkType.toUpperCase() + " Weight: " + newWeight.toFixed(3),
                });
                break;
            }
        }
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

    async function toggle(individualId, _card) {
        currentNetworkId = individualId;
        const sidebar = document.getElementById("network-sidebar");
        if (!sidebar) return;
        if (typeof _getGenomeForPattern !== "function") {
            if (typeof showToast === "function")
                showToast("Network error", "Not initialized", "error");
            return;
        }
        const genome = await _getGenomeForPattern(individualId);
        if (!genome) {
            if (typeof showToast === "function")
                showToast(
                    "Network error",
                    "Could not find genome data for this pattern",
                    "error"
                );
            return;
        }
        try {
            const data = await window.ApiClient.apiFetch(
                _apiUrl + "/network",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ genome: genome }),
                },
                "Network error"
            );
            const infoPanel = sidebar.querySelector(".network-info-panel");
            if (infoPanel) {
                const visualNodes = data.nodes.filter(function (n) {
                    return n.network === "visual" && n.type === "hidden";
                }).length;
                const timeNodes = data.nodes.filter(function (n) {
                    return n.network === "time" && n.type === "hidden";
                }).length;
                const visualConns = data.connections.filter(function (c) {
                    return c.network === "visual";
                }).length;
                const timeConns = data.connections.filter(function (c) {
                    return c.network === "time";
                }).length;
                const nodesEl = infoPanel.querySelector("[data-nodes]");
                const connsEl = infoPanel.querySelector("[data-connections]");
                if (nodesEl)
                    nodesEl.textContent = "V:" + visualNodes + " T:" + timeNodes;
                if (connsEl)
                    connsEl.textContent = "V:" + visualConns + " T:" + timeConns;
            }
            visualizeNetworkInline(individualId, data, sidebar);
            sidebar.classList.add("open");
        } catch (err) {
            if (typeof showToast === "function")
                showToast(
                    "Network error",
                    err.message || "Failed to load network",
                    "error"
                );
        }
    }

    function close() {
        const sidebar = document.getElementById("network-sidebar");
        if (sidebar) sidebar.classList.remove("open");
        if (currentNetworkId && networkVisualizations.has(currentNetworkId)) {
            networkVisualizations.get(currentNetworkId).destroy();
            networkVisualizations.delete(currentNetworkId);
            networkEdges.delete(currentNetworkId);
        }
        currentNetworkId = null;
    }

    function fitToView() {
        if (currentNetworkId) {
            const network = networkVisualizations.get(currentNetworkId);
            if (network) network.fit({ animation: { duration: 500 } });
        }
    }

    function exportNetwork() {
        if (!currentNetworkId) return;
        const network = networkVisualizations.get(currentNetworkId);
        if (!network) return;
        const data = network.body.data;
        const exportData = {
            id: currentNetworkId,
            nodes: data.nodes.get(),
            edges: data.edges.get(),
        };
        const json = JSON.stringify(exportData, null, 2);
        const blob = new Blob([json], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "network_" + currentNetworkId + ".json";
        a.click();
        URL.revokeObjectURL(url);
    }

    function init(options) {
        options = options || {};
        _apiUrl = options.apiUrl || "";
        _getGenomeForPattern = options.getGenomeForPattern || null;
        _updatePatternShader = options.updatePatternShader || null;
        _onGenomeUpdated = options.onGenomeUpdated || null;
        _getCurrentPopulation = options.getCurrentPopulation || null;

        const closeBtn = document.getElementById("network-sidebar-close");
        if (closeBtn) closeBtn.addEventListener("click", close);
        const fitBtn = document.getElementById("network-fit-btn");
        if (fitBtn) fitBtn.addEventListener("click", fitToView);
        const exportBtn = document.getElementById("network-export-btn");
        if (exportBtn) exportBtn.addEventListener("click", exportNetwork);
    }

    window.NetworkVisualizer = {
        toggle: toggle,
        close: close,
        fitToView: fitToView,
        exportNetwork: exportNetwork,
        init: init,
        get currentId() {
            return currentNetworkId;
        },
    };
})();
