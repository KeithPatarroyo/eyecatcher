/**
 * GenealogyNetworkConfig: vis.js network options (physics vs hierarchical).
 * Exposes: GenealogyNetworkConfig.buildNetworkOptions(hierarchicalLayout)
 */
(() => {
    "use strict";

    const DEFAULTS = {
        repelForce: 5000,
        centerForce: 0.1,
        linkDistance: 300,
        linkForce: 0.05,
        damping: 0.09,
    };

    const num = (id, fallback) =>
        parseFloat(document.getElementById(id)?.value || fallback);

    const buildNetworkOptions = (hierarchicalLayout) => {
        const barnesHut = {
            gravitationalConstant: -num("repel-force", DEFAULTS.repelForce),
            centralGravity: num("center-force", DEFAULTS.centerForce),
            springLength: num("link-distance", DEFAULTS.linkDistance),
            springConstant: num("link-force", DEFAULTS.linkForce),
            damping: num("damping", DEFAULTS.damping),
            avoidOverlap: 0.15,
        };

        return {
            layout: {
                hierarchical: hierarchicalLayout
                    ? {
                          direction: "UD",
                          sortMethod: "directed",
                          nodeSpacing: 250,
                          levelSeparation: 220,
                          treeSpacing: 300,
                          blockShifting: true,
                          edgeMinimization: true,
                          parentCentralization: true,
                      }
                    : false,
            },
            physics: {
                enabled: !hierarchicalLayout,
                stabilization: {
                    enabled: true,
                    iterations: 300,
                    updateInterval: 1,
                    fit: false,
                },
                barnesHut,
                solver: "barnesHut",
                adaptiveTimestep: true,
                timestep: 0.35,
                maxVelocity: 50,
                minVelocity: 0.1,
            },
            interaction: {
                hover: true,
                navigationButtons: true,
                keyboard: true,
                tooltipDelay: 200,
                dragNodes: true,
                dragView: true,
                zoomView: true,
                hideEdgesOnDrag: false,
                multiselect: false,
            },
            nodes: {
                font: { face: "monospace", size: 11 },
                chosen: {
                    node(values, _id, selected, hovering) {
                        if (hovering) {
                            values.size += 5;
                            values.borderWidth += 1;
                        }
                        if (selected) values.borderWidth += 1;
                    },
                    label: false,
                },
                shadow: {
                    enabled: true,
                    color: "rgba(0, 0, 0, 0.5)",
                    size: 8,
                    x: 0,
                    y: 3,
                },
            },
            edges: {
                smooth: {
                    enabled: true,
                    type: "continuous",
                    roundness: 0.2,
                    forceDirection: hierarchicalLayout ? "vertical" : "none",
                },
                length: hierarchicalLayout
                    ? undefined
                    : num("link-distance", DEFAULTS.linkDistance),
            },
        };
    };

    window.GenealogyNetworkConfig = { buildNetworkOptions };
})();
