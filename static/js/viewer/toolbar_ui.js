/**
 * Toolbar UI: Start Fresh dropdown, help toggle, settings panel, experiment params, population size −/+.
 * Call ToolbarUI.init() after DOM and PopulationUI / CommunityUI are available.
 * Uses one delegated click/keydown handler on document for [data-action] elements.
 */
(() => {
    "use strict";

    const $ = (id) => (id ? document.getElementById(id) : null);

    /** @type {Record<string, (ev: Event) => void>} */
    const actionHandlers = Object.create(null);

    const asInt = (v) => {
        const n = parseInt(v, 10);
        return Number.isFinite(n) ? n : NaN;
    };

    const asFloat = (v) => {
        const n = parseFloat(v);
        return Number.isFinite(n) ? n : NaN;
    };

    const clamp = (v, min, max, fallback) => {
        const x = Number.isFinite(v) ? v : fallback;
        return Math.max(min, Math.min(max, x));
    };

    const getCfgNumbers = () => {
        const cfg = window.EvolutionConfig || {};
        const minP = cfg.MIN_POPULATION_SIZE ?? 2;
        const maxP = cfg.MAX_POPULATION_SIZE ?? 50; // should match defaults in config.generated.js
        const defaultP = cfg.DEFAULT_POPULATION_SIZE ?? 12;
        const crossover = cfg.CROSSOVER_PROBABILITY ?? 0.3;
        return { cfg, minP, maxP, defaultP, crossover };
    };

    const initStartFreshDropdown = () => {
        const btn = $("start-fresh-btn");
        const menu = $("start-fresh-dropdown");
        if (!btn || !menu) return;

        const setOpen = (open) => {
            menu.hidden = !open;
            btn.setAttribute("aria-expanded", String(open));
        };

        actionHandlers["start-fresh-toggle"] = (e) => {
            e?.stopPropagation?.();
            setOpen(menu.hidden);
        };

        // Delegated handler for dropdown items (random / load)
        const onActivate = (target) => {
            const actionEl = target?.closest?.("[data-action]");
            const action = actionEl?.dataset?.action;
            if (!action) return;

            if (action === "random") window.PopulationUI?.startNewRandomPopulation?.();
            else if (action === "load") window.PopulationUI?.onLoadSavedClick?.();

            setOpen(false);
        };

        DOM.on(menu, "click", (e) => onActivate(e.target));
        DOM.on(menu, "keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onActivate(e.target);
            }
        });

        DOM.on(document, "click", () => setOpen(false));
        DOM.on(document, "keydown", (e) => {
            if (e.key === "Escape") setOpen(false);
        });
    };

    const initHelpToggle = () => {
        const helpBtn = $("help-btn");
        const instructions = $("instructions");
        if (!helpBtn || !instructions) return;

        actionHandlers["help-toggle"] = () => {
            instructions.hidden = !instructions.hidden;
            helpBtn.setAttribute(
                "title",
                instructions.hidden ? "Show help" : "Hide help"
            );
        };
    };

    /**
     * Sync the toolbar "Next generation size" input to EvolutionConfig default.
     * Call after fetchConfig/mergeFromServer and after Settings Apply so both stay in sync.
     */
    const syncToolbarPopulationSizeFromConfigImpl = () => {
        const input = $("population-size-input");
        if (!input) return;

        const { minP, maxP, defaultP } = getCfgNumbers();
        const v = clamp(defaultP, minP, maxP, defaultP);

        input.value = String(v);
        input.min = String(minP);
        input.max = String(maxP);
    };

    const initExperimentParamsPanel = (toolbarUI) => {
        const popInput = $("param-population-size");
        const maxPopInput = $("param-max-population-size");
        const crossoverInput = $("param-crossover-probability");
        const repSelect = $("param-representation-id");
        if (!popInput || !maxPopInput || !crossoverInput) return;

        const refreshFromConfig = () => {
            const { cfg, minP, maxP, defaultP, crossover } = getCfgNumbers();

            // Prefer whatever is currently in the toolbar input if it is valid.
            const toolbarEl = $("population-size-input");
            const toolbarVal = toolbarEl ? asInt(toolbarEl.value) : NaN;
            const pop = Number.isFinite(toolbarVal)
                ? clamp(toolbarVal, minP, maxP, defaultP)
                : defaultP;

            popInput.value = String(pop);
            maxPopInput.value = String(maxP);
            crossoverInput.value = String(crossover);

            if (!repSelect) return;

            // Populate available representations if provided.
            const available = cfg.available_representation_ids;
            if (Array.isArray(available) && available.length) {
                repSelect.innerHTML = "";
                for (const id of available) {
                    const opt = document.createElement("option");
                    opt.value = id;
                    opt.textContent = id;
                    repSelect.appendChild(opt);
                }
            }

            const current =
                window.PopulationState?.representationId ||
                cfg.DEFAULT_REPRESENTATION_ID ||
                window.RepresentationRegistry?.resolve?.({})?.representationId ||
                window.RepresentationRegistry?.getDefaultRepresentationId?.() ||
                "";

            if (current && [...repSelect.options].some((o) => o.value === current)) {
                repSelect.value = current;
            }
        };

        const apply = () => {
            const { minP, maxP, defaultP } = getCfgNumbers();

            const population_size = clamp(asInt(popInput.value), minP, maxP, defaultP);
            const max_population_size = clamp(
                asInt(maxPopInput.value),
                1,
                10_000,
                maxP
            );
            const crossover_probability = asFloat(crossoverInput.value);

            if (
                !Number.isFinite(crossover_probability) ||
                crossover_probability < 0 ||
                crossover_probability > 1
            ) {
                return;
            }

            const updates = {
                population_size,
                max_population_size,
                crossover_probability,
            };
            if (repSelect?.value) updates.representation_id = repSelect.value;

            const previousRepresentationId =
                window.PopulationState?.representationId ?? null;

            window.ApiClient?.patchConfig?.(updates).then(
                (config) => {
                    window.EvolutionConfig?.mergeFromServer?.(config);
                    toolbarUI?.syncToolbarPopulationSizeFromConfig?.();

                    if (
                        updates.representation_id &&
                        config?.representation_id !== previousRepresentationId &&
                        typeof window.onRepresentationSwitched === "function"
                    ) {
                        window.onRepresentationSwitched(config);
                    }
                },
                () => refreshFromConfig()
            );
        };

        refreshFromConfig();
        actionHandlers["experiment-params-apply"] = apply;
        if (toolbarUI) toolbarUI.refreshExperimentParamsFromConfig = refreshFromConfig;
    };

    const initSettingsPanel = (toolbarUI) => {
        const btn = $("settings-btn");
        const panel = $("settings-panel");
        if (!btn || !panel) return;

        const setOpen = (open) => {
            panel.hidden = !open;
            btn.setAttribute("aria-expanded", String(open));
            btn.setAttribute("title", open ? "Close settings" : "Settings");
            if (open) toolbarUI?.refreshExperimentParamsFromConfig?.();
        };

        actionHandlers["settings-toggle"] = (e) => {
            e?.stopPropagation?.();
            setOpen(panel.hidden);
        };

        DOM.on(document, "keydown", (e) => {
            if (e.key === "Escape") setOpen(false);
        });

        actionHandlers["admin-modal"] = () => window.CommunityUI?.openAdminModal?.();

        initExperimentParamsPanel(toolbarUI);
    };

    const initPopulationSizeControls = (toolbarUI) => {
        const input = $("population-size-input");
        if (!input) return;

        const { minP, maxP, defaultP } = getCfgNumbers();
        const normalize = (v) => clamp(asInt(v), minP, maxP, defaultP);

        const setValue = (v) => {
            input.value = String(normalize(v));
        };

        toolbarUI?.syncToolbarPopulationSizeFromConfig?.();

        actionHandlers["population-size-down"] = () => setValue(asInt(input.value) - 1);
        actionHandlers["population-size-up"] = () => setValue(asInt(input.value) + 1);

        DOM.on(input, "change", () => setValue(input.value));
    };

    function bindToolbarDelegation() {
        const run = (ev, el) => {
            const action = el?.dataset?.action;
            const fn = action ? actionHandlers[action] : null;
            if (fn) {
                ev.preventDefault();
                fn(ev);
            }
        };
        DOM.delegate(document.body, "click", "[data-action]", (ev, el) => run(ev, el));
        DOM.on(document.body, "keydown", (ev) => {
            if (ev.key !== "Enter" && ev.key !== " ") return;
            const el = ev.target?.closest?.("[data-action]");
            if (el) run(ev, el);
        });
    }

    class ToolbarUI {
        constructor() {
            this.refreshExperimentParamsFromConfig = () => {};
        }

        init() {
            initStartFreshDropdown();
            initHelpToggle();
            initSettingsPanel(this);
            initPopulationSizeControls(this);
            bindToolbarDelegation();
        }

        syncToolbarPopulationSizeFromConfig() {
            syncToolbarPopulationSizeFromConfigImpl();
        }
    }

    window.ToolbarUI = new ToolbarUI();
})();
