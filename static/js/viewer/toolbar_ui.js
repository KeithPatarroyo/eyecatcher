/**
 * Toolbar UI: Start Fresh dropdown, help toggle, settings panel, population size −/+.
 * Call ToolbarUI.init() after DOM and PopulationUI / CommunityUI are available.
 */
(function () {
    "use strict";

    function bindButton(el, fn) {
        if (el == null) return;
        if (window.Utils && window.Utils.onRoleButtonKeydown) {
            window.Utils.onRoleButtonKeydown(el, fn);
        } else {
            el.addEventListener("click", fn);
            el.addEventListener("keydown", function (e) {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    fn();
                }
            });
        }
    }

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
            bindButton(item, act);
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
        bindButton(helpBtn, toggleHelp);
    }

    /**
     * Sync the toolbar "Next generation size" input to EvolutionConfig default.
     * Call after fetchConfig/mergeFromServer and after Settings Apply so both stay in sync.
     */
    function syncToolbarPopulationSizeFromConfigImpl() {
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

    function initExperimentParamsPanel(toolbarUI) {
        const popInput = document.getElementById("param-population-size");
        const maxPopInput = document.getElementById("param-max-population-size");
        const crossoverInput = document.getElementById("param-crossover-probability");
        const substrateSelect = document.getElementById("param-representation-id");
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
                    window.PopulationState.representationId ||
                    cfg.DEFAULT_SUBSTRATE_ID ||
                    window.RepresentationRegistry.resolve({}).representationId ||
                    (window.RepresentationRegistry.getDefaultRepresentationId
                        ? window.RepresentationRegistry.getDefaultRepresentationId()
                        : "");
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
                updates.representation_id = substrateSelect.value;
            }
            var previousRepresentationId =
                window.PopulationState.representationId || null;
            window.ApiClient.patchConfig(updates).then(
                function (config) {
                    if (
                        window.EvolutionConfig &&
                        window.EvolutionConfig.mergeFromServer
                    ) {
                        window.EvolutionConfig.mergeFromServer(config);
                    }
                    if (toolbarUI) {
                        toolbarUI.syncToolbarPopulationSizeFromConfig();
                    }
                    if (
                        updates.representation_id &&
                        config.representation_id !== previousRepresentationId &&
                        typeof window.onRepresentationSwitched === "function"
                    ) {
                        window.onRepresentationSwitched(config);
                    }
                },
                function () {
                    refreshFromConfig();
                }
            );
        }

        refreshFromConfig();
        bindButton(applyBtn, apply);
        if (toolbarUI) {
            toolbarUI.refreshExperimentParamsFromConfig = refreshFromConfig;
        }
    }

    function initSettingsPanel(toolbarUI) {
        var btn = document.getElementById("settings-btn");
        var panel = document.getElementById("settings-panel");
        if (!btn || !panel) return;
        function toggle() {
            panel.hidden = !panel.hidden;
            var open = !panel.hidden;
            btn.setAttribute("aria-expanded", String(open));
            btn.setAttribute("title", open ? "Close settings" : "Settings");
            if (open && toolbarUI && toolbarUI.refreshExperimentParamsFromConfig) {
                toolbarUI.refreshExperimentParamsFromConfig();
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
        var moderateBtn = document.getElementById("settings-moderate-btn");
        if (moderateBtn) {
            moderateBtn.addEventListener("click", function () {
                window.CommunityUI.openAdminModal();
            });
        }
        initExperimentParamsPanel(toolbarUI);
    }

    function initPopulationSizeControls(toolbarUI) {
        var input = document.getElementById("population-size-input");
        var downBtn = document.getElementById("population-size-down");
        var upBtn = document.getElementById("population-size-up");
        if (!input || !downBtn || !upBtn) return;
        var cfg = window.EvolutionConfig || {};
        var minP = cfg.MIN_POPULATION_SIZE !== undefined ? cfg.MIN_POPULATION_SIZE : 2;
        // Fallback must match EvolutionConfig (EyecatcherConfig.defaults in config.generated.js)
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
        if (toolbarUI) toolbarUI.syncToolbarPopulationSizeFromConfig();
        function stepDown() {
            update(Number(input.value) - 1);
        }
        function stepUp() {
            update(Number(input.value) + 1);
        }
        bindButton(downBtn, stepDown);
        bindButton(upBtn, stepUp);
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

    class ToolbarUI {
        constructor() {
            this.refreshExperimentParamsFromConfig = function () {};
        }

        init() {
            initStartFreshDropdown();
            initHelpToggle();
            initSettingsPanel(this);
            initPopulationSizeControls(this);
            initToolbarKeydown();
        }

        syncToolbarPopulationSizeFromConfig() {
            syncToolbarPopulationSizeFromConfigImpl();
        }
    }

    window.ToolbarUI = new ToolbarUI();
})();
