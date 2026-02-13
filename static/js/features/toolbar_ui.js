/**
 * Toolbar UI: Start Fresh dropdown, help toggle, settings panel, population size −/+.
 * Call initToolbarUI() after DOM and PopulationUI / CommunityUI are available.
 */
(function () {
    "use strict";

    function initStartFreshDropdown() {
        const btn = document.getElementById("start-fresh-btn");
        const menu = document.getElementById("start-fresh-dropdown");
        if (!btn || !menu) return;
        function close() {
            menu.hidden = true;
            btn.setAttribute("aria-expanded", "false");
        }
        function open() {
            menu.hidden = false;
            btn.setAttribute("aria-expanded", "true");
        }
        function toggle() {
            if (menu.hidden) open();
            else close();
        }
        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            toggle();
        });
        btn.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                toggle();
            }
        });
        menu.querySelectorAll("[data-action]").forEach(function (item) {
            function act() {
                if (item.dataset.action === "random")
                    window.PopulationUI.startNewRandomPopulation();
                else if (item.dataset.action === "load")
                    window.PopulationUI.onLoadSavedClick();
                close();
            }
            if (window.Utils && window.Utils.onRoleButtonKeydown) {
                window.Utils.onRoleButtonKeydown(item, act);
            } else {
                item.addEventListener("click", act);
                item.addEventListener("keydown", function (e) {
                    if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        act();
                    }
                });
            }
        });
        document.addEventListener("click", close);
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") close();
        });
    }

    function initHelpToggle() {
        const helpBtn = document.getElementById("help-btn");
        const instructions = document.getElementById("instructions");
        if (!helpBtn || !instructions) return;
        function toggleHelp() {
            instructions.hidden = !instructions.hidden;
            helpBtn.setAttribute(
                "title",
                instructions.hidden ? "Show help" : "Hide help"
            );
        }
        if (window.Utils && window.Utils.onRoleButtonKeydown) {
            window.Utils.onRoleButtonKeydown(helpBtn, toggleHelp);
        } else {
            helpBtn.addEventListener("click", toggleHelp);
            helpBtn.addEventListener("keydown", function (e) {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleHelp();
                }
            });
        }
    }

    /**
     * Sync the toolbar "Next generation size" input to EvolutionConfig default.
     * Call after fetchConfig/mergeFromServer and after Settings Apply so both stay in sync.
     */
    function syncToolbarPopulationSizeFromConfig() {
        var input = document.getElementById("population-size-input");
        if (!input) return;
        var cfg = window.EvolutionConfig || {};
        var minP = cfg.MIN_POPULATION_SIZE !== undefined ? cfg.MIN_POPULATION_SIZE : 2;
        var maxP = cfg.MAX_POPULATION_SIZE !== undefined ? cfg.MAX_POPULATION_SIZE : 50;
        var defaultP =
            cfg.DEFAULT_POPULATION_SIZE !== undefined
                ? cfg.DEFAULT_POPULATION_SIZE
                : 12;
        var v = Math.max(minP, Math.min(maxP, defaultP));
        input.value = String(v);
        input.min = String(minP);
        input.max = String(maxP);
    }

    function initExperimentParamsPanel() {
        const popInput = document.getElementById("param-population-size");
        const maxPopInput = document.getElementById("param-max-population-size");
        const crossoverInput = document.getElementById("param-crossover-probability");
        const substrateSelect = document.getElementById("param-substrate-id");
        const applyBtn = document.getElementById("experiment-params-apply");
        if (!popInput || !maxPopInput || !crossoverInput || !applyBtn) return;
        const cfg = window.EvolutionConfig || {};

        function refreshFromConfig() {
            var toolbarEl = document.getElementById("population-size-input");
            var toolbarVal = toolbarEl ? parseInt(toolbarEl.value, 10) : NaN;
            var minP =
                cfg.MIN_POPULATION_SIZE !== undefined ? cfg.MIN_POPULATION_SIZE : 2;
            var maxP =
                cfg.MAX_POPULATION_SIZE !== undefined ? cfg.MAX_POPULATION_SIZE : 50;
            var defaultP =
                cfg.DEFAULT_POPULATION_SIZE !== undefined
                    ? cfg.DEFAULT_POPULATION_SIZE
                    : 12;
            if (!isNaN(toolbarVal) && toolbarVal >= minP && toolbarVal <= maxP) {
                popInput.value = String(toolbarVal);
            } else {
                popInput.value = String(defaultP);
            }
            maxPopInput.value = String(
                cfg.MAX_POPULATION_SIZE !== undefined ? cfg.MAX_POPULATION_SIZE : 50
            );
            crossoverInput.value = String(
                cfg.CROSSOVER_PROBABILITY !== undefined
                    ? cfg.CROSSOVER_PROBABILITY
                    : 0.3
            );
            if (substrateSelect) {
                var current =
                    (window.PopulationState &&
                        window.PopulationState.getState &&
                        window.PopulationState.getState().substrateId) ||
                    cfg.DEFAULT_SUBSTRATE_ID ||
                    "dual_cppn";
                if (
                    Array.isArray(cfg.available_substrate_ids) &&
                    cfg.available_substrate_ids.length > 0
                ) {
                    substrateSelect.innerHTML = "";
                    cfg.available_substrate_ids.forEach(function (id) {
                        var opt = document.createElement("option");
                        opt.value = id;
                        opt.textContent = id;
                        substrateSelect.appendChild(opt);
                    });
                }
                if (
                    current &&
                    [].some.call(substrateSelect.options, function (o) {
                        return o.value === current;
                    })
                ) {
                    substrateSelect.value = current;
                }
            }
        }

        function apply() {
            var population_size = parseInt(popInput.value, 10);
            var max_population_size = parseInt(maxPopInput.value, 10);
            var crossover_probability = parseFloat(crossoverInput.value);
            if (
                isNaN(population_size) ||
                population_size < 1 ||
                isNaN(max_population_size) ||
                max_population_size < 1 ||
                isNaN(crossover_probability) ||
                crossover_probability < 0 ||
                crossover_probability > 1
            ) {
                return;
            }
            var updates = {
                population_size: population_size,
                max_population_size: max_population_size,
                crossover_probability: crossover_probability,
            };
            if (substrateSelect && substrateSelect.value) {
                updates.substrate_id = substrateSelect.value;
            }
            var previousSubstrateId =
                (window.PopulationState &&
                    window.PopulationState.getState &&
                    window.PopulationState.getState().substrateId) ||
                null;
            window.ApiClient.patchConfig(updates).then(
                function (config) {
                    if (
                        window.EvolutionConfig &&
                        window.EvolutionConfig.mergeFromServer
                    ) {
                        window.EvolutionConfig.mergeFromServer(config);
                    }
                    if (
                        window.ToolbarUI &&
                        window.ToolbarUI.syncToolbarPopulationSizeFromConfig
                    ) {
                        window.ToolbarUI.syncToolbarPopulationSizeFromConfig();
                    }
                    if (
                        updates.substrate_id &&
                        config.substrate_id !== previousSubstrateId &&
                        typeof window.onSubstrateSwitched === "function"
                    ) {
                        window.onSubstrateSwitched(config);
                    }
                },
                function () {
                    refreshFromConfig();
                }
            );
        }

        refreshFromConfig();
        applyBtn.addEventListener("click", apply);
        if (window.Utils && window.Utils.onRoleButtonKeydown) {
            window.Utils.onRoleButtonKeydown(applyBtn, apply);
        }
        applyBtn.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                apply();
            }
        });
        window.ToolbarUI = window.ToolbarUI || {};
        window.ToolbarUI.refreshExperimentParamsFromConfig = refreshFromConfig;
        window.ToolbarUI.syncToolbarPopulationSizeFromConfig =
            syncToolbarPopulationSizeFromConfig;
    }

    function initSettingsPanel() {
        const btn = document.getElementById("settings-btn");
        const panel = document.getElementById("settings-panel");
        if (!btn || !panel) return;
        function toggle() {
            panel.hidden = !panel.hidden;
            const open = !panel.hidden;
            btn.setAttribute("aria-expanded", String(open));
            btn.setAttribute("title", open ? "Close settings" : "Settings");
            if (
                open &&
                window.ToolbarUI &&
                window.ToolbarUI.refreshExperimentParamsFromConfig
            ) {
                window.ToolbarUI.refreshExperimentParamsFromConfig();
            }
        }
        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            toggle();
        });
        btn.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                toggle();
            }
        });
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") {
                panel.hidden = true;
                btn.setAttribute("aria-expanded", "false");
            }
        });
        const moderateBtn = document.getElementById("settings-moderate-btn");
        if (moderateBtn) {
            moderateBtn.addEventListener("click", function () {
                window.CommunityUI.openAdminModal();
            });
        }
        initExperimentParamsPanel();
    }

    function initPopulationSizeControls() {
        const input = document.getElementById("population-size-input");
        const downBtn = document.getElementById("population-size-down");
        const upBtn = document.getElementById("population-size-up");
        if (!input || !downBtn || !upBtn) return;
        var cfg = window.EvolutionConfig || {};
        var minP = cfg.MIN_POPULATION_SIZE !== undefined ? cfg.MIN_POPULATION_SIZE : 2;
        // Fallback must match EvolutionConfig; see evolution_config.js
        var maxP = cfg.MAX_POPULATION_SIZE !== undefined ? cfg.MAX_POPULATION_SIZE : 50;
        var defaultP =
            cfg.DEFAULT_POPULATION_SIZE !== undefined
                ? cfg.DEFAULT_POPULATION_SIZE
                : 12;
        function clamp(v) {
            return Math.max(minP, Math.min(maxP, isNaN(v) ? defaultP : v));
        }
        function update(val) {
            input.value = clamp(Number(val));
        }
        syncToolbarPopulationSizeFromConfig();
        function stepDown() {
            update(Number(input.value) - 1);
        }
        function stepUp() {
            update(Number(input.value) + 1);
        }
        if (window.Utils && window.Utils.onRoleButtonKeydown) {
            window.Utils.onRoleButtonKeydown(downBtn, stepDown);
            window.Utils.onRoleButtonKeydown(upBtn, stepUp);
        } else {
            downBtn.addEventListener("click", stepDown);
            downBtn.addEventListener("keydown", function (e) {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    stepDown();
                }
            });
            upBtn.addEventListener("click", stepUp);
            upBtn.addEventListener("keydown", function (e) {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    stepUp();
                }
            });
        }
        input.addEventListener("change", function () {
            update(input.value);
        });
    }

    function initToolbarKeydown() {
        const toolbarEl = document.getElementById("toolbar");
        if (!toolbarEl) return;
        toolbarEl.addEventListener("keydown", function (e) {
            if (
                (e.key === "Enter" || e.key === " ") &&
                e.target.getAttribute &&
                e.target.getAttribute("role") === "button"
            ) {
                e.preventDefault();
                e.target.click();
            }
        });
    }

    function initToolbarUI() {
        initStartFreshDropdown();
        initHelpToggle();
        initSettingsPanel();
        initPopulationSizeControls();
        initToolbarKeydown();
    }

    window.initToolbarUI = initToolbarUI;
})();
