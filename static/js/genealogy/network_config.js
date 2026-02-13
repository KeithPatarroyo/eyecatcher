/**
 * Vis.js network options for the genealogy tree. Extracted from genealogy_viewer.js.
 * Depends on: DOM (physics sliders, node-size, etc.). Exposes: GenealogyNetworkConfig.buildNetworkOptions.
 */
(function () {
    "use strict";

    const PHYSICS_DEFAULTS = {
        repelForce: 5000,
        centerForce: 0.1,
        linkDistance: 300,
        linkForce: 0.05,
        damping: 0.09,
    };

    function buildNetworkOptions(hierarchicalLayout) {
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
                barnesHut: {
                    gravitationalConstant: -parseFloat(
                        document.getElementById("repel-force")?.value ||
                            PHYSICS_DEFAULTS.repelForce
                    ),
                    centralGravity: parseFloat(
                        document.getElementById("center-force")?.value ||
                            PHYSICS_DEFAULTS.centerForce
                    ),
                    springLength: parseFloat(
                        document.getElementById("link-distance")?.value ||
                            PHYSICS_DEFAULTS.linkDistance
                    ),
                    springConstant: parseFloat(
                        document.getElementById("link-force")?.value ||
                            PHYSICS_DEFAULTS.linkForce
                    ),
                    damping: parseFloat(
                        document.getElementById("damping")?.value ||
                            PHYSICS_DEFAULTS.damping
                    ),
                    avoidOverlap: 0.15,
                },
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
                    node: function (values, id, selected, hovering) {
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
                    : parseFloat(
                          document.getElementById("link-distance")?.value ||
                              PHYSICS_DEFAULTS.linkDistance
                      ),
            },
        };
    }

    window.GenealogyNetworkConfig = { buildNetworkOptions: buildNetworkOptions };
})();
