/**
 * Physics and slider controls for the genealogy tree. Extracted from genealogy_viewer.js.
 * Exposes: GenealogyPhysics.bindSliderInput, GenealogyPhysics.PHYSICS_SLIDERS, GenealogyPhysics.initPhysicsControls.
 */
(function () {
    "use strict";

    function bindSliderInput(inputId, valueSpanId, formatter, onValueChange) {
        const input = document.getElementById(inputId);
        const valueSpan = document.getElementById(valueSpanId);
        if (!input || !valueSpan) return;
        input.addEventListener("input", function (e) {
            const value = parseFloat(e.target.value);
            valueSpan.textContent = formatter(value);
            if (onValueChange) onValueChange(value);
        });
    }

    const PHYSICS_SLIDERS = [
        {
            inputId: "center-force",
            valueSpanId: "center-force-value",
            formatter: (v) => v.toFixed(2),
            key: "centralGravity",
            negate: false,
        },
        {
            inputId: "repel-force",
            valueSpanId: "repel-force-value",
            formatter: (v) => String(v),
            key: "gravitationalConstant",
            negate: true,
        },
        {
            inputId: "link-force",
            valueSpanId: "link-force-value",
            formatter: (v) => v.toFixed(2),
            key: "springConstant",
            negate: false,
        },
        {
            inputId: "link-distance",
            valueSpanId: "link-distance-value",
            formatter: (v) => String(v),
            key: "springLength",
            negate: false,
        },
        {
            inputId: "damping",
            valueSpanId: "damping-value",
            formatter: (v) => v.toFixed(2),
            key: "damping",
            negate: false,
        },
    ];

    function initPhysicsControls(
        getTreeNetwork,
        getHierarchicalLayout,
        updateControlsVisibility
    ) {
        const setPhysics = (key, value, negate) => {
            const treeNetwork = getTreeNetwork();
            if (treeNetwork && !getHierarchicalLayout()) {
                treeNetwork.setOptions({
                    physics: {
                        barnesHut: { [key]: negate ? -value : value },
                    },
                });
            }
        };
        PHYSICS_SLIDERS.forEach((s) => {
            bindSliderInput(s.inputId, s.valueSpanId, s.formatter, (v) =>
                setPhysics(s.key, v, s.negate)
            );
        });

        const Utils = window.Utils;
        if (Utils && Utils.onId) {
            Utils.onId("show-arrows", (el) => {
                el.addEventListener("change", function (e) {
                    const treeNetwork = getTreeNetwork();
                    if (treeNetwork) {
                        const edges = treeNetwork.body.data.edges;
                        const allEdges = edges.get();
                        allEdges.forEach((edge) => {
                            edges.update({
                                id: edge.id,
                                arrows: {
                                    to: {
                                        enabled: e.target.checked,
                                        scaleFactor: 1.0,
                                    },
                                },
                            });
                        });
                    }
                });
            });

            bindSliderInput(
                "node-size",
                "node-size-value",
                (v) => String(v),
                (value) => {
                    const treeNetwork = getTreeNetwork();
                    if (treeNetwork) {
                        treeNetwork.body.data.nodes.get().forEach((node) => {
                            treeNetwork.body.data.nodes.update({
                                id: node.id,
                                size: value / 2,
                            });
                        });
                    }
                }
            );
            bindSliderInput(
                "link-thickness",
                "link-thickness-value",
                (v) => v.toFixed(1),
                (value) => {
                    const treeNetwork = getTreeNetwork();
                    if (treeNetwork) {
                        treeNetwork.body.data.edges.get().forEach((edge) => {
                            treeNetwork.body.data.edges.update({
                                id: edge.id,
                                width: value,
                            });
                        });
                    }
                }
            );
        }

        if (updateControlsVisibility) updateControlsVisibility();
    }

    window.GenealogyPhysics = {
        bindSliderInput: bindSliderInput,
        PHYSICS_SLIDERS: PHYSICS_SLIDERS,
        initPhysicsControls: initPhysicsControls,
    };
})();
