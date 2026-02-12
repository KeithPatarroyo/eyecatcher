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

    function initSettingsPanel() {
        const btn = document.getElementById("settings-btn");
        const panel = document.getElementById("settings-panel");
        if (!btn || !panel) return;
        function toggle() {
            panel.hidden = !panel.hidden;
            const open = !panel.hidden;
            btn.setAttribute("aria-expanded", String(open));
            btn.setAttribute("title", open ? "Close settings" : "Settings");
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
