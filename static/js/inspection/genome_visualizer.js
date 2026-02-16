// genome_visualizer.js (minimal rewrite, replace whole file)
(() => {
    "use strict";

    let _apiUrl = "";
    let _getGenomeForPattern = null;
    let _updatePatternRule = null;
    let _onGenomeUpdated = null;
    let _getCurrentPopulation = null;

    /** Inspection state: individualId -> vis.Network (not canonical; UI-only). */
    const networks = new Map();
    /** Inspection state: individualId -> vis.DataSet edges (for weight updates). */
    const edgesById = new Map();
    let currentId = null;

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

    const hashString = (s) => {
        let h = 0;
        const str = String(s);
        for (let i = 0; i < str.length; i++) h = str.charCodeAt(i) + ((h << 5) - h);
        return h;
    };

    const getNetworkTypesFromData = (data) => {
        const types = new Set();
        data?.nodes?.forEach((n) => n.network && types.add(n.network));
        data?.connections?.forEach((c) => c.network && types.add(c.network));
        return types.size ? [...types] : ["main"];
    };

    const colorForNetwork = (networkType, isPositive) => {
        const hue = Math.abs(hashString(networkType) % 360);
        const sat = 60;
        const light = isPositive ? 45 : 55;
        return `hsla(${hue},${sat}%,${light}%,0.4)`;
    };

    const opacityForNetwork = (networkType) =>
        0.4 + (Math.abs(hashString(networkType)) % 60) / 100;

    const extractNodeLabel = (nodeId) => {
        const parts = String(nodeId).split("_");
        if (parts.length < 3) return nodeId;

        const type = parts[1];
        const id = parts.slice(2).join("_");
        if (type === "input") return `in${id}`;
        if (type === "output") return `out${id}`;
        if (type === "hidden") return `h${id}`;
        return id;
    };

    const updateNetworkEdgeWeight = (
        individualId,
        sourceId,
        targetId,
        newWeight,
        networkType
    ) => {
        const edges = edgesById.get(individualId);
        if (!edges) return;

        const allEdges = edges.get();
        for (const edge of allEdges) {
            if (edge.from !== sourceId || edge.to !== targetId) continue;

            edges.update({
                id: edge.id,
                width: Math.max(0.5, Math.abs(newWeight)),
                color: colorForNetwork(networkType, newWeight > 0),
                title: `${networkType.toUpperCase()} Weight: ${newWeight.toFixed(3)}`,
            });
            return;
        }
    };

    const visualizeNetworkInline = (individualId, data, sidebar) => {
        if (typeof vis === "undefined") {
            window.Toast?.show?.("Visualization error", "vis.js not loaded", "error");
            return;
        }

        const vizContainer = sidebar.querySelector(".network-visualization");
        if (!vizContainer) return;
        vizContainer.innerHTML = "";

        const networkTypes = getNetworkTypesFromData(data);

        const nodes = new vis.DataSet();
        (data?.nodes ?? []).forEach((node) => {
            const base = nodeColors[node.type] ?? nodeColors.hidden;
            const network = node.network || networkTypes[0] || "main";
            const opacity = opacityForNetwork(network);
            const hex = Math.round(opacity * 255)
                .toString(16)
                .padStart(2, "0");

            const groupPrefix =
                node.group && node.type !== "hidden" ? `[${node.group}] ` : "";
            let label = groupPrefix + (node.label || node.id);

            if (node.type === "hidden") {
                label += `\nBias: ${(node.bias ?? 0).toFixed(2)}`;
                if (node.activation) label += `\n${node.activation}`;
            }
            label += `\n[${network}]`;

            const adjusted = {
                background: base.background + hex,
                border: base.border + hex,
                highlight: {
                    background: base.highlight.background + hex,
                    border: base.highlight.border + hex,
                },
            };

            const hoverTitle = `${node.group ? `${node.group}: ` : ""}${node.label ? node.label.split("\n")[0] : node.id} (${node.type})`;

            nodes.add({
                id: node.id,
                label,
                color: adjusted,
                shape: "dot",
                size: node.type === "hidden" ? 20 : 25,
                font: { size: 9, color: "#fff", face: "monospace" },
                physics: false,
                x: node.x || undefined,
                y: node.y || undefined,
                title: hoverTitle,
            });
        });

        const edges = new vis.DataSet();
        (data?.connections ?? []).forEach((conn) => {
            const network = conn.network || networkTypes[0] || "main";
            edges.add({
                from: conn.source,
                to: conn.target,
                width: Math.max(0.5, Math.abs(conn.weight)),
                color: colorForNetwork(network, conn.weight > 0),
                title: `${network.toUpperCase()} Weight: ${conn.weight.toFixed(3)}`,
                arrows: "to",
                smooth: { type: "continuous" },
            });
        });

        const network = new vis.Network(
            vizContainer,
            { nodes, edges },
            {
                physics: { enabled: false },
                layout: { randomSeed: 42, improvedLayout: true },
                interaction: {
                    hover: true,
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
            }
        );

        networks.set(individualId, network);
        edgesById.set(individualId, edges);

        window.NetworkWeightSliders?.setupWeightSliders?.(individualId, data);

        network.on("selectEdge", (params) => {
            const edgeId = params?.edges?.[0];
            if (!edgeId) return;
            const edge = edges.get(edgeId);
            if (!edge) return;
            window.NetworkWeightSliders?.scrollToWeightSlider?.(edge.from, edge.to);
        });

        setTimeout(
            () => networks.get(individualId)?.fit?.({ animation: { duration: 500 } }),
            100
        );
    };

    const close = () => {
        const sidebar = DOM.byId("network-sidebar");
        if (sidebar) DOM.toggleClass(sidebar, "open", false);

        if (currentId && networks.has(currentId)) {
            networks.get(currentId).destroy();
            networks.delete(currentId);
            edgesById.delete(currentId);
        }
        currentId = null;
    };

    const fitToView = () =>
        currentId && networks.get(currentId)?.fit?.({ animation: { duration: 500 } });

    const exportNetwork = () => {
        if (!currentId) return;
        const network = networks.get(currentId);
        if (!network) return;

        const data = network.body.data;
        const exportData = {
            id: currentId,
            nodes: data.nodes.get(),
            edges: data.edges.get(),
        };
        const blob = new Blob([JSON.stringify(exportData, null, 2)], {
            type: "application/json",
        });

        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `network_${currentId}.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const toggle = async (individualId) => {
        const sidebar = DOM.byId("network-sidebar");
        if (!sidebar) return;

        if (sidebar.classList.contains("open") && currentId === individualId) {
            close();
            return;
        }

        currentId = individualId;

        if (typeof _getGenomeForPattern !== "function") {
            window.Toast?.show?.("Network error", "Not initialized", "error");
            return;
        }

        const genome = await _getGenomeForPattern(individualId);
        if (!genome) {
            window.Toast?.show?.(
                "Network error",
                "Could not find genome data for this pattern",
                "error"
            );
            return;
        }

        try {
            const data = await window.ApiClient.apiFetch(
                `${_apiUrl}/api/network`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ individual: genome }),
                },
                "Network error"
            );

            const infoPanel = sidebar.querySelector(".network-info-panel");
            if (infoPanel) {
                const types = getNetworkTypesFromData(data);
                const nodeCounts = types.map(
                    (t) =>
                        `${t.substring(0, 1).toUpperCase()}:${
                            (data.nodes ?? []).filter(
                                (n) => n.network === t && n.type === "hidden"
                            ).length
                        }`
                );
                const connCounts = types.map(
                    (t) =>
                        `${t.substring(0, 1).toUpperCase()}:${
                            (data.connections ?? []).filter((c) => c.network === t)
                                .length
                        }`
                );

                infoPanel
                    .querySelector("[data-nodes]")
                    ?.replaceChildren(document.createTextNode(nodeCounts.join(" ")));
                infoPanel
                    .querySelector("[data-connections]")
                    ?.replaceChildren(document.createTextNode(connCounts.join(" ")));
            }

            visualizeNetworkInline(individualId, data, sidebar);
            DOM.toggleClass(sidebar, "open", true);
        } catch (err) {
            window.Toast?.show?.(
                "Network error",
                err?.message || "Failed to load network",
                "error"
            );
        }
    };

    const init = (options = {}) => {
        _apiUrl = options.apiUrl || "";
        _getGenomeForPattern = options.getGenomeForPattern || null;
        _updatePatternRule = options.updatePatternRule || null;
        _onGenomeUpdated = options.onGenomeUpdated || null;
        _getCurrentPopulation = options.getCurrentPopulation || null;

        window.NetworkWeightSliders?.init?.({
            apiUrl: _apiUrl,
            getGenomeForPattern: _getGenomeForPattern,
            updatePatternRule: _updatePatternRule,
            onGenomeUpdated: _onGenomeUpdated,
            getCurrentPopulation: _getCurrentPopulation,
            updateNetworkEdgeWeight,
            getNetworkTypesFromData,
            extractNodeLabel,
        });

        const sidebar = DOM.byId("network-sidebar");
        if (sidebar) {
            DOM.delegate(sidebar, "click", "[data-network-action]", (ev, el) => {
                const action = el.dataset.networkAction;
                if (action === "close") close();
                else if (action === "fit") fitToView();
                else if (action === "export") exportNetwork();
            });
        }
    };

    window.NetworkVisualizer = {
        toggle,
        close,
        fitToView,
        exportNetwork,
        init,
        get currentId() {
            return currentId;
        },
    };
})();
