/**
 * GenealogyPhysics: slider bindings and a couple of toggles.
 * Exposes: GenealogyPhysics.initPhysicsControls(getNetwork, getHierarchicalLayout, updateControlsVisibility)
 */
import Utils from "../lib/utils.js";

const bindSlider = (inputId, valueSpanId, fmt, onChange) => {
    const input = document.getElementById(inputId);
    const valueSpan = document.getElementById(valueSpanId);
    if (!input || !valueSpan) return;

    const update = () => {
        const v = parseFloat(input.value);
        valueSpan.textContent = fmt(v);
        onChange?.(v);
    };

    input.addEventListener("input", update);
    update();
};

const initPhysicsControls = (
    getNetwork,
    getHierarchicalLayout,
    updateControlsVisibility
) => {
    const setBarnes = (key, value, negate) => {
        const net = getNetwork();
        if (!net || getHierarchicalLayout()) return;
        net.setOptions({
            physics: { barnesHut: { [key]: negate ? -value : value } },
        });
    };

    bindSlider(
        "center-force",
        "center-force-value",
        (v) => v.toFixed(2),
        (v) => setBarnes("centralGravity", v)
    );
    bindSlider(
        "repel-force",
        "repel-force-value",
        (v) => String(v),
        (v) => setBarnes("gravitationalConstant", v, true)
    );
    bindSlider(
        "link-force",
        "link-force-value",
        (v) => v.toFixed(2),
        (v) => setBarnes("springConstant", v)
    );
    bindSlider(
        "link-distance",
        "link-distance-value",
        (v) => String(v),
        (v) => setBarnes("springLength", v)
    );
    bindSlider(
        "damping",
        "damping-value",
        (v) => v.toFixed(2),
        (v) => setBarnes("damping", v)
    );

    Utils?.onId?.("show-arrows", (el) => {
        el.addEventListener("change", (e) => {
            const net = getNetwork();
            if (!net) return;
            const edges = net.body.data.edges;
            edges.get().forEach((edge) =>
                edges.update({
                    id: edge.id,
                    arrows: { to: { enabled: e.target.checked, scaleFactor: 1.0 } },
                })
            );
        });
    });

    bindSlider(
        "node-size",
        "node-size-value",
        (v) => String(v),
        (v) => {
            const net = getNetwork();
            if (!net) return;
            net.body.data.nodes
                .get()
                .forEach((node) =>
                    net.body.data.nodes.update({ id: node.id, size: v / 2 })
                );
        }
    );

    bindSlider(
        "link-thickness",
        "link-thickness-value",
        (v) => v.toFixed(1),
        (v) => {
            const net = getNetwork();
            if (!net) return;
            net.body.data.edges
                .get()
                .forEach((edge) =>
                    net.body.data.edges.update({ id: edge.id, width: v })
                );
        }
    );

    updateControlsVisibility?.();
};

const GenealogyPhysics = { initPhysicsControls };
export default GenealogyPhysics;
export { GenealogyPhysics };
