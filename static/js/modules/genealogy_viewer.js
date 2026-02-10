const API_URL = window.API_URL || "";

let treeNetwork = null;
let treeData = { nodes: [], edges: [] };
let selectedNodeId = null;
let hierarchicalLayout = false; // Default to physics layout
let currentPopulationId = null; // Track which population is currently active
let thumbnailCache = new Map(); // Cache rendered thumbnails
let savedPositions = null; // Save positions when switching modes

function updateControlsVisibility() {
    const physicsControls = document.getElementById("physics-controls");
    if (physicsControls) {
        physicsControls.classList.toggle("hidden", hierarchicalLayout);
    }
}

const TOAST_DURATION_MS = 5000;
const DEFAULT_NODE_SIZE = 90;
const THUMBNAIL_CANVAS_SIZE = 128;
const MAX_THUMBNAIL_CACHE = 200;
const PHYSICS_DEFAULTS = {
    repelForce: 5000,
    centerForce: 0.1,
    linkDistance: 300,
    linkForce: 0.05,
    damping: 0.09,
};

function showGenealogyToast(title, body, type = "success") {
    if (typeof window.Toast !== "undefined" && window.Toast.show) {
        window.Toast.show(title, body, type, { duration: TOAST_DURATION_MS });
    } else {
        const container = document.getElementById("toast-container");
        const toast = document.createElement("div");
        toast.className = "toast " + type;
        const titleEl = document.createElement("div");
        titleEl.className = "toast-title";
        titleEl.textContent = title;
        toast.appendChild(titleEl);
        if (body) {
            const bodyEl = document.createElement("div");
            bodyEl.className = "toast-body";
            bodyEl.textContent = body;
            toast.appendChild(bodyEl);
        }
        container.appendChild(toast);
        setTimeout(function () {
            toast.remove();
        }, TOAST_DURATION_MS);
    }
}

// Fetch and display genealogy stats
async function loadStats() {
    try {
        const data = await ApiClient.apiFetch(
            `${API_URL}/genealogy/stats`,
            {},
            "Stats failed"
        );
        document.getElementById("stat-populations").textContent =
            data.total_populations;
        document.getElementById("stat-individuals").textContent =
            data.total_individuals;
        document.getElementById("stat-branches").textContent = data.total_branches;
        document.getElementById("stat-max-gen").textContent = data.max_generation;
    } catch (error) {
        console.error("Failed to load stats:", error);
    }
}

// Fetch and display branches
async function loadBranches() {
    try {
        const data = await ApiClient.apiFetch(
            `${API_URL}/genealogy/branches`,
            {},
            "Branches failed"
        );
        const branchList = document.getElementById("branch-list");
        branchList.innerHTML = "";

        if (!data.branches || data.branches.length === 0) {
            branchList.innerHTML = '<div class="list-empty">No branches yet</div>';
            return;
        }

        const tpl = document.getElementById("branch-list-item-tpl");
        data.branches.forEach((branch) => {
            let item;
            if (tpl && tpl.content) {
                item = tpl.content.cloneNode(true).querySelector(".branch-item");
            }
            if (!item) {
                item = document.createElement("div");
                item.className = "branch-item";
                const nameEl = document.createElement("div");
                nameEl.className = "branch-name";
                item.appendChild(nameEl);
                const infoEl = document.createElement("div");
                infoEl.className = "branch-info";
                item.appendChild(infoEl);
            }
            const nameEl = item.querySelector(".branch-name");
            const infoEl = item.querySelector(".branch-info");
            if (nameEl) nameEl.textContent = branch.name;
            if (infoEl) {
                infoEl.textContent =
                    "Gen " +
                    branch.latest_generation +
                    " \u2022 " +
                    branch.node_count +
                    " node(s)";
            }
            item.onclick = () => {
                // Focus on this branch in the tree
                const branchNodes = treeData.nodes.filter(
                    (n) => n.branch_name === branch.name
                );
                if (branchNodes.length > 0) {
                    treeNetwork.focus(branchNodes[0].id, {
                        scale: 1.0,
                        animation: true,
                    });
                }
            };
            branchList.appendChild(item);
        });
    } catch (error) {
        console.error("Failed to load branches:", error);
    }
}

// Fetch and visualize the tree
async function loadTree() {
    Utils.showLoading(true);
    try {
        const data = await ApiClient.apiFetch(
            `${API_URL}/genealogy/tree`,
            {},
            "Failed to load tree"
        );
        visualizeTree(data.nodes);
        loadStats();
        loadBranches();
        updateCurrentPopulationInfo();
    } catch (e) {
        console.error("Failed to load tree:", e);
        showGenealogyToast(
            "Error",
            Utils.formatApiError(e, "Failed to load tree"),
            "error"
        );
    } finally {
        Utils.showLoading(false);
    }
}

function buildVisNodes(nodes) {
    const visNodes = new vis.DataSet();
    const nodeSize = parseInt(
        document.getElementById("node-size")?.value || DEFAULT_NODE_SIZE,
        10
    );
    nodes.forEach((node) => {
        const isCurrent =
            currentPopulationId && node.id === parseInt(currentPopulationId);
        const color = getBranchColor(node.branch_name);
        const borderColor = isCurrent ? "#FFD700" : "#0066cc";
        const borderWidth = isCurrent ? 5 : 2;
        visNodes.add({
            id: node.id,
            label: undefined,
            color: {
                background: color,
                border: borderColor,
                highlight: { background: "#0080ff", border: borderColor },
            },
            shape: "dot",
            borderWidth: borderWidth,
            size: nodeSize / 2,
            mass: 2,
            title: `Generation ${node.generation_num} (${node.branch_name})\n${node.population_size} individuals${isCurrent ? "\n★ Current Population" : ""}`,
        });
    });
    return visNodes;
}

function buildVisEdges(nodes) {
    const visEdges = new vis.DataSet();
    const showArrows = document.getElementById("show-arrows")?.checked !== false;
    const linkThickness = parseFloat(
        document.getElementById("link-thickness")?.value || 2
    );
    nodes.forEach((node) => {
        if (node.parent_id !== null) {
            visEdges.add({
                from: node.parent_id,
                to: node.id,
                arrows: { to: { enabled: showArrows, scaleFactor: 1.0 } },
                color: {
                    color: "rgba(136, 136, 136, 0.4)",
                    highlight: "rgba(0, 102, 204, 0.8)",
                    hover: "rgba(0, 102, 204, 0.6)",
                },
                width: linkThickness,
                smooth: {
                    enabled: true,
                    type: "continuous",
                    roundness: 0.2,
                },
                selectionWidth: linkThickness + 1,
            });
        }
    });
    return visEdges;
}

function buildNetworkOptions() {
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
            zoomSpeed: 1,
            hideEdgesOnDrag: false,
            hideEdgesOnZoom: false,
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
                    if (selected) {
                        values.borderWidth += 1;
                    }
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

function attachNetworkHandlers(network, _visNodes) {
    network.on("click", (params) => {
        if (params.nodes.length > 0) selectNode(params.nodes[0]);
    });
    network.on("dragEnd", (_params) => {
        if (!hierarchicalLayout) {
            savedPositions = network.getPositions();
        }
    });
    if (!hierarchicalLayout) {
        network.once("stabilizationIterationsDone", function () {
            setTimeout(() => {
                network.fit({
                    animation: {
                        duration: 800,
                        easingFunction: "easeInOutQuad",
                    },
                });
            }, 100);
            Utils.showLoading(false);
        });
    } else {
        setTimeout(() => {
            network.fit({
                animation: {
                    duration: 500,
                    easingFunction: "easeInOutQuad",
                },
            });
            Utils.showLoading(false);
        }, 100);
    }
}

// Visualize the tree using vis.js
function visualizeTree(nodes) {
    treeData.nodes = nodes;
    const container = document.getElementById("tree-visualization");
    const visNodes = buildVisNodes(nodes);
    const visEdges = buildVisEdges(nodes);
    const options = buildNetworkOptions();

    if (treeNetwork) {
        treeNetwork.destroy();
    }
    treeNetwork = new vis.Network(
        container,
        { nodes: visNodes, edges: visEdges },
        options
    );

    if (savedPositions && !hierarchicalLayout) {
        setTimeout(() => {
            const currentNodes = visNodes.get();
            currentNodes.forEach((node) => {
                if (savedPositions[node.id]) {
                    visNodes.update({
                        id: node.id,
                        x: savedPositions[node.id].x,
                        y: savedPositions[node.id].y,
                        fixed: false,
                    });
                }
            });
            treeNetwork.stabilize(50);
        }, 100);
    }

    attachNetworkHandlers(treeNetwork, visNodes);
    setTimeout(() => {
        renderAllThumbnails(visNodes);
    }, 500);
}

// Select a node and show its info
function selectNode(nodeId) {
    selectedNodeId = nodeId;
    const node = treeData.nodes.find((n) => n.id === nodeId);

    if (!node) return;

    document.getElementById("selected-node-info").classList.remove("hidden");
    document.getElementById("info-id").textContent = node.id;
    document.getElementById("info-generation").textContent = node.generation_num;
    document.getElementById("info-branch").textContent = node.branch_name;
    document.getElementById("info-size").textContent = node.population_size;
    document.getElementById("info-created").textContent = new Date(
        node.created_at
    ).toLocaleString();
}

// Update current population info display
function updateCurrentPopulationInfo() {
    const section = document.getElementById("current-population-section");
    if (!currentPopulationId || !treeData.nodes) {
        section.classList.add("hidden");
        return;
    }

    const popId = parseInt(currentPopulationId);
    const node = treeData.nodes.find((n) => n.id === popId);

    if (!node) {
        section.classList.add("hidden");
        return;
    }

    section.classList.remove("hidden");
    document.getElementById("current-id").textContent = node.id;
    document.getElementById("current-generation").textContent = node.generation_num;
}

// Load a population into the main viewer
async function loadPopulation(populationId) {
    Utils.showLoading(true);
    try {
        const data = await ApiClient.apiFetch(
            `${API_URL}/genealogy/load-population/${populationId}`,
            {},
            "Failed to load population"
        );
        // Store in localStorage for cross-tab communication (this tab -> main viewer)
        // localStorage is shared across tabs, enabling genealogy tree -> main viewer handoff
        Utils.safeSetItem(
            localStorage,
            "genealogy_load",
            JSON.stringify({
                genomes: data.genomes,
                generation_num: data.generation_num,
                population_id: data.population_id,
                branch_name: data.branch_name,
            })
        );

        showGenealogyToast("Success", "Population loaded! Redirecting...", "success");

        // Redirect to main viewer after a short delay
        setTimeout(() => {
            window.location.href = "/";
        }, 1000);
    } catch (e) {
        console.error("Failed to load population:", e);
        showGenealogyToast(
            "Error",
            Utils.formatApiError(e, "Failed to load population"),
            "error"
        );
    } finally {
        Utils.showLoading(false);
    }
}

// Get a color for a branch name
function getBranchColor(branchName) {
    // Simple hash-based color generation
    let hash = 0;
    for (let i = 0; i < branchName.length; i++) {
        hash = branchName.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hue = hash % 360;
    return `hsl(${hue}, 60%, 30%)`;
}

// Render a thumbnail for a population
async function renderThumbnail(populationId) {
    // Check cache first
    if (thumbnailCache.has(populationId)) {
        return thumbnailCache.get(populationId);
    }

    try {
        const data = await ApiClient.apiFetch(
            `${API_URL}/genealogy/population-thumbnail/${populationId}`,
            {},
            "No thumbnail"
        );
        if (!data.genome) return null;

        const compileData = await ApiClient.apiFetch(
            `${API_URL}/compile`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ genomes: [data.genome] }),
            },
            "Compile failed"
        );
        if (!compileData.shaders || !compileData.shaders[0]) return null;

        const shader = compileData.shaders[0].shader;

        // Create a small canvas and render
        const canvas = document.createElement("canvas");
        canvas.width = THUMBNAIL_CANVAS_SIZE;
        canvas.height = THUMBNAIL_CANVAS_SIZE;

        // Check if PatternRenderer is available
        if (!window.PatternRenderer) {
            console.warn(
                `PatternRenderer not available for population ${populationId}`
            );
            return null;
        }

        const patternData = PatternRenderer.setupPattern(canvas, shader);
        if (!patternData) {
            console.warn(`Failed to setup pattern for population ${populationId}`);
            return null;
        }

        // Render a single frame
        const signalState = {
            time: {
                rawTime: true,
                mouseSpeed: true,
                mouseDist: true,
                inactivity: true,
            },
            visual: {
                time: true,
                mouseSpeed: true,
                mouseDist: true,
                inactivity: true,
            },
        };
        PatternRenderer.renderPattern(patternData, 0.5, 0, 0, 0, signalState);

        // Convert to data URL
        const dataUrl = canvas.toDataURL("image/png");
        if (thumbnailCache.size >= MAX_THUMBNAIL_CACHE) {
            const firstKey = thumbnailCache.keys().next().value;
            if (firstKey !== undefined) thumbnailCache.delete(firstKey);
        }
        thumbnailCache.set(populationId, dataUrl);
        return dataUrl;
    } catch (error) {
        console.error(
            `Failed to render thumbnail for population ${populationId}:`,
            error
        );
        return null;
    }
}

// Render thumbnails for all nodes (batched parallel to avoid sequential delay)
const THUMBNAIL_BATCH_SIZE = 8;
async function renderAllThumbnails(visNodes) {
    const nodes = visNodes.get();
    const nodeSize = parseInt(
        document.getElementById("node-size")?.value || DEFAULT_NODE_SIZE,
        10
    );

    for (let i = 0; i < nodes.length; i += THUMBNAIL_BATCH_SIZE) {
        const batch = nodes.slice(i, i + THUMBNAIL_BATCH_SIZE);
        const results = await Promise.all(
            batch.map(async (node) => ({
                id: node.id,
                color: node.color,
                thumbnail: await renderThumbnail(node.id),
            }))
        );
        results.forEach((r) => {
            if (r.thumbnail) {
                visNodes.update({
                    id: r.id,
                    shape: "circularImage",
                    image: r.thumbnail,
                    size: nodeSize / 2,
                    borderWidth: 3,
                    mass: 2,
                    color: {
                        border: r.color.border,
                        background: "transparent",
                    },
                    shapeProperties: {
                        useBorderWithImage: true,
                    },
                });
            }
        });
    }
}

function attachEventListeners() {
    document.getElementById("refresh-btn").onclick = () => {
        loadTree();
    };

    document.getElementById("download-genealogy-btn").onclick = async () => {
        const modal = document.getElementById("export-genealogy-modal");
        try {
            const sizes = await ApiClient.apiFetch(
                `${API_URL}/genealogy/export-sizes`,
                {},
                "Could not load sizes"
            );
            document.getElementById("export-full-size").textContent =
                sizes.full.populations +
                " populations, " +
                sizes.full.individuals +
                " individuals (~" +
                window.formatBytes(sizes.full.estimated_bytes) +
                ")";

            const branchList = document.getElementById("export-branch-list");
            const branchesGroup = document.getElementById("export-branches-group");
            branchList.innerHTML = "";
            const branches = sizes.branches || [];
            branchesGroup.hidden = branches.length === 0;
            const tpl = document.getElementById("export-branch-option-tpl");
            branches.forEach((b) => {
                if (!tpl || !tpl.content) return;
                const label = tpl.content.cloneNode(true).querySelector("label");
                if (!label) return;
                const radio = label.querySelector('input[type="radio"]');
                const titleSpan = label.querySelector(".export-option-title");
                const sizeSpan = label.querySelector(".export-size");
                const branchName = b.name || "main";
                const safeId = "export-branch-" + branchName.replace(/\W/g, "_");
                radio.id = safeId;
                radio.value = branchName;
                titleSpan.textContent = branchName;
                sizeSpan.textContent =
                    b.populations +
                    " pop., " +
                    b.individuals +
                    " ind. (~" +
                    window.formatBytes(b.estimated_bytes) +
                    ")";
                branchList.appendChild(label);
            });
            modal.hidden = false;
        } catch (e) {
            showGenealogyToast(
                "Could not load sizes",
                Utils.formatApiError(e, "Network error"),
                "error"
            );
        }
    };

    document.getElementById("export-modal-cancel").onclick = () => {
        document.getElementById("export-genealogy-modal").hidden = true;
    };
    document.querySelector(".export-modal-backdrop").onclick = () => {
        document.getElementById("export-genealogy-modal").hidden = true;
    };
    document.addEventListener("keydown", (e) => {
        const modal = document.getElementById("export-genealogy-modal");
        if (e.key === "Escape" && modal && !modal.hidden) modal.hidden = true;
    });
    document.getElementById("export-modal-download").onclick = async () => {
        const scope = document.querySelector('input[name="export-scope"]:checked');
        const branchName = scope && scope.value !== "full" ? scope.value : null;
        const modal = document.getElementById("export-genealogy-modal");
        modal.hidden = true;
        try {
            const url = branchName
                ? `${API_URL}/genealogy/export?branch_name=${encodeURIComponent(branchName)}`
                : `${API_URL}/genealogy/export`;
            const data = await ApiClient.apiFetch(url, {}, "Download failed");
            const blob = new Blob([JSON.stringify(data, null, 2)], {
                type: "application/json",
            });
            const urlObj = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = urlObj;
            a.download = branchName
                ? `genealogy-${branchName}-${new Date().toISOString().slice(0, 10)}.json`
                : `genealogy-export-${new Date().toISOString().slice(0, 10)}.json`;
            a.click();
            URL.revokeObjectURL(urlObj);
            showGenealogyToast(
                "Downloaded",
                (branchName ? 'Branch "' + branchName + '"' : "Full tree") +
                    " exported as JSON.",
                "success"
            );
        } catch (e) {
            showGenealogyToast(
                "Download failed",
                Utils.formatApiError(e, "Network error"),
                "error"
            );
        }
    };

    document.getElementById("reset-genealogy-btn").onclick = async () => {
        if (!confirm("Clear all genealogy data? This cannot be undone.")) return;
        try {
            await ApiClient.apiFetch(
                `${API_URL}/genealogy/reset`,
                { method: "POST" },
                "Reset failed"
            );
            try {
                if (typeof localStorage !== "undefined")
                    localStorage.removeItem("genealogy_branch_counter");
            } catch (_) {
                /* ignore */
            }
            try {
                if (typeof sessionStorage !== "undefined")
                    sessionStorage.removeItem("current_population_id");
            } catch (_) {
                /* ignore */
            }
            thumbnailCache.clear();
            savedPositions = null;
            selectedNodeId = null;
            showGenealogyToast(
                "Genealogy reset",
                "All populations and branches cleared.",
                "success"
            );
            loadTree();
        } catch (e) {
            showGenealogyToast(
                "Reset failed",
                Utils.formatApiError(e, "Network error"),
                "error"
            );
        }
    };

    document.getElementById("fit-btn").onclick = () => {
        if (treeNetwork) {
            treeNetwork.fit({ animation: { duration: 500 } });
        }
    };

    document.getElementById("hierarchical-btn").onclick = function () {
        if (!hierarchicalLayout) {
            if (treeNetwork) {
                savedPositions = treeNetwork.getPositions();
            }
            hierarchicalLayout = true;
            this.classList.add("active");
            document.getElementById("physics-btn").classList.remove("active");
            loadTree();
            updateControlsVisibility();
        }
    };

    document.getElementById("physics-btn").onclick = function () {
        if (hierarchicalLayout) {
            hierarchicalLayout = false;
            this.classList.add("active");
            document.getElementById("hierarchical-btn").classList.remove("active");
            loadTree();
            updateControlsVisibility();
        }
    };

    document.getElementById("load-population-btn").onclick = () => {
        if (selectedNodeId !== null) {
            loadPopulation(selectedNodeId);
        }
    };

    document.getElementById("focus-current-btn").onclick = () => {
        if (currentPopulationId && treeNetwork) {
            const popId = parseInt(currentPopulationId);
            treeNetwork.focus(popId, {
                scale: 1.5,
                animation: {
                    duration: 800,
                    easingFunction: "easeInOutQuad",
                },
            });
            // Also select it to show info
            selectNode(popId);
        }
    };
}

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

// Initialize physics controls
function initPhysicsControls() {
    const setPhysics = (key, value, negate) => {
        if (treeNetwork && !hierarchicalLayout) {
            treeNetwork.setOptions({
                physics: {
                    barnesHut: { [key]: negate ? -value : value },
                },
            });
        }
    };
    bindSliderInput(
        "center-force",
        "center-force-value",
        (v) => v.toFixed(2),
        (v) => setPhysics("centralGravity", v)
    );
    bindSliderInput(
        "repel-force",
        "repel-force-value",
        (v) => String(v),
        (v) => setPhysics("gravitationalConstant", v, true)
    );
    bindSliderInput(
        "link-force",
        "link-force-value",
        (v) => v.toFixed(2),
        (v) => setPhysics("springConstant", v)
    );
    bindSliderInput(
        "link-distance",
        "link-distance-value",
        (v) => String(v),
        (v) => setPhysics("springLength", v)
    );
    bindSliderInput(
        "damping",
        "damping-value",
        (v) => v.toFixed(2),
        (v) => setPhysics("damping", v)
    );

    // Show arrows
    document.getElementById("show-arrows").addEventListener("change", function (e) {
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

    bindSliderInput(
        "node-size",
        "node-size-value",
        (v) => String(v),
        (value) => {
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
            if (treeNetwork) {
                treeNetwork.body.data.edges.get().forEach((edge) => {
                    treeNetwork.body.data.edges.update({ id: edge.id, width: value });
                });
            }
        }
    );

    updateControlsVisibility();
}

// Initialize function
function initialize() {
    // Get current population ID from session storage (tab-specific state)
    // This is set by the main viewer when a population is loaded
    currentPopulationId = Utils.safeGetItem(
        sessionStorage,
        "current_population_id",
        null
    );
    if (currentPopulationId) {
        console.log("Current population:", currentPopulationId);
    }

    attachEventListeners();
    initPhysicsControls();
    loadTree();
}

// Always run initialization when the script loads
// The script is at the bottom of the body, so DOM is ready
initialize();
