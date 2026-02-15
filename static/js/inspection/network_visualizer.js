/**
 * Network visualization module: CPPN sidebar, vis.js graph, weight sliders.
 * Depends: vis (global from CDN), Toast (from toast.js).
 * Call init() with dependencies before use. Exposes: toggle(), close(), fitToView(), exportNetwork().
 */
(function () {
    "use strict";

    let _apiUrl = "";
    let _getGenomeForPattern = null;
    let _updatePatternRule = null;
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

    function getNetworkTypesFromData(data) {
        const types = new Set();
        if (data.nodes) {
            data.nodes.forEach(function (n) {
                if (n.network) types.add(n.network);
            });
        }
        if (data.connections) {
            data.connections.forEach(function (c) {
                if (c.network) types.add(c.network);
            });
        }
        return types.size ? Array.from(types) : ["main"];
    }

    function colorForNetwork(networkType, isPositive) {
        let hash = 0;
        const s = String(networkType);
        for (let i = 0; i < s.length; i++) {
            hash = s.charCodeAt(i) + ((hash << 5) - hash);
        }
        const hue = Math.abs(hash % 360);
        const sat = 60;
        const light = isPositive ? 45 : 55;
        return "hsla(" + hue + "," + sat + "%," + light + "%,0.4)";
    }

    function opacityForNetwork(networkType) {
        let hash = 0;
        const s = String(networkType);
        for (let i = 0; i < s.length; i++) {
            hash = s.charCodeAt(i) + ((hash << 5) - hash);
        }
        return 0.4 + (Math.abs(hash) % 60) / 100;
    }

    function extractNodeLabel(nodeId) {
        const parts = String(nodeId).split("_");
        if (parts.length >= 3) {
            const type = parts[1];
            const id = parts.slice(2).join("_");
            if (type === "input") return "in" + id;
            if (type === "output") return "out" + id;
            if (type === "hidden") return "h" + id;
            return id;
        }
        return nodeId;
    }

    function visualizeNetworkInline(individualId, data, container) {
        if (typeof vis === "undefined") {
            Toast.show("Visualization error", "vis.js not loaded", "error");
            return;
        }
        try {
            const vizContainer = container.querySelector(".network-visualization");
            vizContainer.innerHTML = "";

            const networkTypes = getNetworkTypesFromData(data);
            const nodes = new vis.DataSet();
            data.nodes.forEach(function (node) {
                const color = nodeColors[node.type];
                const network = node.network || networkTypes[0] || "main";
                const opacity = opacityForNetwork(network);
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
                const network = conn.network || networkTypes[0] || "main";
                const width = Math.max(0.5, Math.abs(conn.weight));
                const isPositive = conn.weight > 0;
                const color = colorForNetwork(network, isPositive);
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

            if (window.NetworkWeightSliders)
                window.NetworkWeightSliders.setupWeightSliders(individualId, data);

            network.on("selectEdge", function (params) {
                if (params.edges.length > 0) {
                    const edge = edges.get(params.edges[0]);
                    if (edge && window.NetworkWeightSliders)
                        window.NetworkWeightSliders.scrollToWeightSlider(
                            edge.from,
                            edge.to
                        );
                }
            });

            setTimeout(function () {
                const net = networkVisualizations.get(individualId);
                if (net) net.fit({ animation: { duration: 500 } });
            }, 100);
        } catch (err) {
            Toast.show(
                "Visualization error",
                err.message || "Failed to visualize network",
                "error"
            );
        }
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
                const color = colorForNetwork(networkType, isPositive);
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

    async function toggle(individualId, _card) {
        currentNetworkId = individualId;
        const sidebar = document.getElementById("network-sidebar");
        if (!sidebar) return;
        if (typeof _getGenomeForPattern !== "function") {
            Toast.show("Network error", "Not initialized", "error");
            return;
        }
        const genome = await _getGenomeForPattern(individualId);
        if (!genome) {
            Toast.show(
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
                    body: JSON.stringify({ individual: genome }),
                },
                "Network error"
            );
            const infoPanel = sidebar.querySelector(".network-info-panel");
            if (infoPanel) {
                const networkTypes = getNetworkTypesFromData(data);
                const nodeCounts = networkTypes.map(function (t) {
                    return (
                        t.substring(0, 1).toUpperCase() +
                        ":" +
                        data.nodes.filter(function (n) {
                            return n.network === t && n.type === "hidden";
                        }).length
                    );
                });
                const connCounts = networkTypes.map(function (t) {
                    return (
                        t.substring(0, 1).toUpperCase() +
                        ":" +
                        data.connections.filter(function (c) {
                            return c.network === t;
                        }).length
                    );
                });
                const nodesEl = infoPanel.querySelector("[data-nodes]");
                const connsEl = infoPanel.querySelector("[data-connections]");
                if (nodesEl) nodesEl.textContent = nodeCounts.join(" ");
                if (connsEl) connsEl.textContent = connCounts.join(" ");
            }
            visualizeNetworkInline(individualId, data, sidebar);
            sidebar.classList.add("open");
        } catch (err) {
            Toast.show(
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
        _updatePatternRule = options.updatePatternRule || null;
        _onGenomeUpdated = options.onGenomeUpdated || null;
        _getCurrentPopulation = options.getCurrentPopulation || null;

        if (window.NetworkWeightSliders) {
            window.NetworkWeightSliders.init({
                apiUrl: _apiUrl,
                getGenomeForPattern: _getGenomeForPattern,
                updatePatternRule: _updatePatternRule,
                onGenomeUpdated: _onGenomeUpdated,
                getCurrentPopulation: _getCurrentPopulation,
                updateNetworkEdgeWeight: updateNetworkEdgeWeight,
                getNetworkTypesFromData: getNetworkTypesFromData,
                extractNodeLabel: extractNodeLabel,
            });
        }

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
