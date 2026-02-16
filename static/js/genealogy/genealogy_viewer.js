/**
 * Genealogy tree viewer (vis.js). Keeps legacy globals initialize()/runWhenReady().
 * Depends on: vis.js, Utils, Toast, GenealogyNetworkConfig, GenealogyPhysics, GenealogyThumbnails, GenealogyExport
 */
const API_URL = window.API_URL || "";

let treeNetwork = null;
let selectedNodeId = null;
let treeNodesById = Object.create(null); // id -> raw node from API (generation_num, branch_name, etc.)
let hierarchicalLayout = false;
let currentPopulationId = null;
let thumbnailCache = new Map();
let savedPositions = null;

const TOAST_DURATION_MS = 5000;
const DEFAULT_NODE_SIZE = 90;

function showGenealogyToast(title, body, type = "success") {
    window.Toast?.show?.(title, body, type, { duration: TOAST_DURATION_MS });
}

async function fetchJson(url, fallback) {
    const res = await fetch(url);
    const data = await res.json().catch(() => null);
    if (!res.ok) {
        const err = new Error(
            data?.error || data?.message || fallback || `Request failed (${res.status})`
        );
        err.status = res.status;
        err.data = data;
        throw err;
    }
    return data;
}

function updateControlsVisibility() {
    document
        .getElementById("physics-controls")
        ?.classList.toggle("hidden", hierarchicalLayout);
}

async function loadStats() {
    try {
        const d = await fetchJson(`${API_URL}/api/genealogy/stats`, "Stats failed");
        document.getElementById("stat-populations").textContent = d.total_populations;
        document.getElementById("stat-individuals").textContent = d.total_individuals;
        document.getElementById("stat-branches").textContent = d.total_branches;
        document.getElementById("stat-max-gen").textContent = d.max_generation;
    } catch (e) {
        console.warn("Stats failed:", e);
    }
}

async function loadBranches() {
    const list = document.getElementById("branch-list");
    if (!list) return;

    list.innerHTML = "";
    try {
        const d = await fetchJson(
            `${API_URL}/api/genealogy/branches`,
            "Branches failed"
        );
        const branches = d.branches || [];

        if (!branches.length) {
            list.appendChild(window.Utils.createListEmptyEl("div", "No branches yet"));
            return;
        }

        const tpl = document.getElementById("branch-list-item-tpl");

        branches.forEach((branch) => {
            const el =
                tpl?.content?.cloneNode(true)?.querySelector?.(".branch-item") ||
                (() => {
                    const div = document.createElement("div");
                    div.className = "branch-item";
                    div.innerHTML = `<div class="branch-name"></div><div class="branch-info"></div>`;
                    return div;
                })();

            el.querySelector(".branch-name").textContent = branch.name || "main";
            const popCount = branch.populations ?? branch.node_count ?? 0;
            const indCount = branch.individuals ?? "—";
            el.querySelector(".branch-info").textContent =
                `${popCount} populations${indCount !== "—" ? ` • ${indCount} individuals` : ""}`;

            el.addEventListener("click", () => {
                const name = branch.name || "main";
                document
                    .querySelectorAll(".branch-item")
                    .forEach((n) => n.classList.remove("active"));
                el.classList.add("active");
                loadTree(name);
            });

            list.appendChild(el);
        });
    } catch (e) {
        list.appendChild(
            window.Utils.createListEmptyEl("div", "Failed to load branches")
        );
    }
}

function getBranchColor(branchName) {
    // Stable-ish palette without external libs.
    const palette = [
        "#ffb703",
        "#8ecae6",
        "#219ebc",
        "#fb8500",
        "#8338ec",
        "#3a86ff",
        "#06d6a0",
        "#ef476f",
    ];
    const s = String(branchName || "main");
    let h = 0;
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    return palette[h % palette.length];
}

function buildVisNodes(treeData) {
    const nodeSize = parseInt(
        document.getElementById("node-size")?.value || DEFAULT_NODE_SIZE,
        10
    );
    return (treeData.nodes || []).map((n) => {
        const branch = n.branch_name || "main";
        const border = getBranchColor(branch);
        return {
            id: n.id,
            label: `#${n.id}\nGen ${n.generation_num ?? "?"}`,
            title: `${branch} • Gen ${n.generation_num ?? "?"}`,
            size: nodeSize / 2,
            shape: "dot",
            color: { border, background: "#111" },
            borderWidth: 2,
            font: { color: "#eee" },
        };
    });
}

function buildVisEdges(treeData) {
    const width = parseFloat(document.getElementById("link-thickness")?.value || 1.5);
    const arrows = document.getElementById("show-arrows")?.checked === true;

    // Backend returns only nodes (with parent_id); derive edges from parent links.
    const edges =
        treeData.edges && treeData.edges.length > 0
            ? treeData.edges
            : (treeData.nodes || [])
                  .filter((n) => n.parent_id != null)
                  .map((n, i) => ({
                      id: `e-${n.parent_id}-${n.id}-${i}`,
                      from: n.parent_id,
                      to: n.id,
                  }));

    return edges.map((e, i) => ({
        id: e.id ?? `${e.from}-${e.to}-${i}`,
        from: e.from,
        to: e.to,
        width,
        arrows: { to: { enabled: arrows } },
    }));
}

function buildNetworkOptions() {
    return window.GenealogyNetworkConfig?.buildNetworkOptions
        ? window.GenealogyNetworkConfig.buildNetworkOptions(hierarchicalLayout)
        : { physics: { enabled: !hierarchicalLayout } };
}

function attachNetworkHandlers() {
    if (!treeNetwork) return;

    treeNetwork.on("click", (params) => {
        const id = params.nodes?.[0];
        if (id == null) return;
        selectNode(id);
    });

    treeNetwork.on("hoverNode", (params) => {
        const id = params.node;
        if (id == null) return;
        selectedNodeId = id;
    });
}

function selectNode(popId) {
    selectedNodeId = popId;
    const nodes = treeNetwork?.body?.data?.nodes;
    if (!nodes) return;

    nodes.get().forEach((n) =>
        nodes.update({
            id: n.id,
            borderWidth: n.id === popId ? 4 : 2,
        })
    );

    updateCurrentPopulationInfo(popId);
}

async function updateCurrentPopulationInfo(popId) {
    const section = document.getElementById("selected-node-info");
    if (section) section.classList.remove("hidden");

    const node = treeNodesById[popId];
    const setInfo = (id, text) => {
        const el = document.getElementById(id);
        if (el) el.textContent = text ?? "-";
    };
    setInfo("info-id", String(popId));
    setInfo(
        "info-generation",
        node?.generation_num != null ? String(node.generation_num) : "-"
    );
    setInfo("info-branch", node?.branch_name ?? "-");
    setInfo(
        "info-size",
        node?.population_size != null ? String(node.population_size) : "-"
    );
    setInfo("info-created", node?.created_at ?? "-");
}

async function loadPopulation(popId) {
    const loader = window.GenealogyBridge?.loadPopulationById;
    if (typeof loader === "function") {
        await loader(popId);
        currentPopulationId = popId;
        return;
    }

    // Standalone genealogy page: fetch population, store for main app, then redirect.
    try {
        const data = await fetchJson(
            `${API_URL}/api/genealogy/load-population/${popId}`,
            "Load population failed"
        );
        const individuals = data.individuals || data.genomes || [];
        if (!individuals.length) {
            showGenealogyToast(
                "Load population",
                "No individuals in this population.",
                "error"
            );
            return;
        }
        const representationId =
            data.metadata?.experiment_config?.representation_id ??
            data.representation_id ??
            null;
        const payload = {
            individuals,
            population_id: data.population_id ?? popId,
            branch_name: data.branch_name ?? "main",
            generation_num: data.generation_num ?? 0,
            representation_id: representationId,
        };
        try {
            localStorage.setItem("genealogy_load", JSON.stringify(payload));
        } catch (e) {
            showGenealogyToast(
                "Load population",
                "Could not store for redirect (localStorage).",
                "error"
            );
            return;
        }
        const baseUrl = window.API_BASE_PATH != null ? window.API_BASE_PATH : "/";
        window.location.href = baseUrl.replace(/\/+$/, "") || "/";
    } catch (e) {
        console.error("Load population failed:", e);
        showGenealogyToast(
            "Load population",
            e.message || "Failed to load population",
            "error"
        );
    }
}

function visualizeTree(data) {
    const container = document.getElementById("tree-visualization");
    if (!container || !window.vis) return;

    const nodes = new window.vis.DataSet(buildVisNodes(data));
    const edges = new window.vis.DataSet(buildVisEdges(data));

    treeNetwork = new window.vis.Network(
        container,
        { nodes, edges },
        buildNetworkOptions()
    );
    attachNetworkHandlers();
    updateControlsVisibility();

    // Thumbnails are optional and can be slow; batch them.
    window.GenealogyThumbnails?.renderAllThumbnails?.(nodes, thumbnailCache, {
        apiUrl: API_URL,
        defaultNodeSize: DEFAULT_NODE_SIZE,
    });

    // Restore selected node if possible.
    if (selectedNodeId != null) selectNode(selectedNodeId);
}

async function loadTree(branchName = null) {
    await Promise.all([loadStats(), loadBranches()]);

    const url = branchName
        ? `${API_URL}/api/genealogy/tree?branch_name=${encodeURIComponent(branchName)}`
        : `${API_URL}/api/genealogy/tree`;

    try {
        const data = await fetchJson(url, "Tree load failed");
        treeNodesById = Object.create(null);
        (data.nodes || []).forEach((n) => {
            treeNodesById[n.id] = n;
        });
        visualizeTree(data);

        // Focus current population if known
        const stored = window.Utils.safeGetItem(
            sessionStorage,
            "current_population_id",
            null
        );
        currentPopulationId = stored ? parseInt(stored, 10) : null;
        if (
            currentPopulationId != null &&
            treeNetwork?.body?.data?.nodes?.get(currentPopulationId)
        ) {
            treeNetwork.focus(currentPopulationId, {
                scale: 1.5,
                animation: { duration: 800, easingFunction: "easeInOutQuad" },
            });
            selectNode(currentPopulationId);
        }
    } catch (e) {
        console.error("Failed to load tree:", e);
        showGenealogyToast("Genealogy", e.message || "Failed to load tree", "error");
    }
}

function setLayoutMode(hierarchical) {
    hierarchicalLayout = hierarchical;
    const hierBtn = document.getElementById("hierarchical-btn");
    const physBtn = document.getElementById("physics-btn");
    hierBtn?.classList.toggle("active", hierarchical);
    physBtn?.classList.toggle("active", !hierarchical);

    if (!treeNetwork) return;

    if (hierarchical) {
        savedPositions = treeNetwork.getPositions();
        treeNetwork.setOptions(buildNetworkOptions());
        treeNetwork.fit({ animation: { duration: 400 } });
    } else {
        treeNetwork.setOptions(buildNetworkOptions());
        if (savedPositions && treeNetwork.body?.data?.nodes) {
            const nodes = treeNetwork.body.data.nodes;
            Object.keys(savedPositions).forEach((id) => {
                const pos = savedPositions[id];
                if (pos) nodes.update({ id: Number(id) || id, x: pos.x, y: pos.y });
            });
        }
        treeNetwork.stabilize();
    }
    updateControlsVisibility();
}

function bindLayoutEvents() {
    document
        .getElementById("hierarchical-btn")
        ?.addEventListener("click", () => setLayoutMode(true));
    document
        .getElementById("physics-btn")
        ?.addEventListener("click", () => setLayoutMode(false));
}

async function resetGenealogy() {
    if (!confirm("Clear all genealogy data? This cannot be undone.")) return;
    try {
        const res = await fetch(`${API_URL}/api/genealogy/reset`, { method: "POST" });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            throw new Error(
                data?.error || data?.message || `Reset failed (${res.status})`
            );
        }
        showGenealogyToast(
            "Genealogy",
            "All genealogy data has been cleared.",
            "success"
        );
        try {
            if (typeof localStorage !== "undefined")
                localStorage.removeItem("genealogy_branch_counter");
            if (typeof sessionStorage !== "undefined")
                sessionStorage.removeItem("current_population_id");
        } catch (_e) {
            /* ignore */
        }
        selectedNodeId = null;
        document.getElementById("selected-node-info")?.classList.add("hidden");
        await loadTree();
    } catch (e) {
        console.error("Reset genealogy failed:", e);
        showGenealogyToast(
            "Reset failed",
            e.message || "Could not clear genealogy data",
            "error"
        );
    }
}

function bindActionEvents() {
    document
        .getElementById("load-population-btn")
        ?.addEventListener("click", async () => {
            if (selectedNodeId == null) return;
            await loadPopulation(selectedNodeId);
        });

    document.getElementById("refresh-btn")?.addEventListener("click", () => loadTree());
    document
        .getElementById("fit-btn")
        ?.addEventListener("click", () => treeNetwork?.fit?.({ animation: true }));
    document
        .getElementById("reset-genealogy-btn")
        ?.addEventListener("click", () => resetGenealogy());
}

function initPhysicsControls() {
    window.GenealogyPhysics?.initPhysicsControls?.(
        () => treeNetwork,
        () => hierarchicalLayout,
        updateControlsVisibility
    );
}

function attachEventListeners() {
    bindLayoutEvents();
    bindActionEvents();
    if (window.GenealogyExport?.bindExportModalEvents)
        window.GenealogyExport.bindExportModalEvents(showGenealogyToast, API_URL);
}

function initialize() {
    currentPopulationId = window.Utils.safeGetItem(
        sessionStorage,
        "current_population_id",
        null
    );
    attachEventListeners();
    initPhysicsControls();
    loadTree();
}

function runWhenReady() {
    if (document.readyState === "loading")
        document.addEventListener("DOMContentLoaded", initialize);
    else initialize();
}
runWhenReady();
