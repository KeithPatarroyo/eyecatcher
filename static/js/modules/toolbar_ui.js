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
            item.addEventListener("click", function () {
                if (item.dataset.action === "random")
                    window.PopulationUI.startNewRandomPopulation();
                else if (item.dataset.action === "load")
                    window.PopulationUI.onLoadSavedClick();
                close();
            });
            item.addEventListener("keydown", function (e) {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    item.click();
                }
            });
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
        helpBtn.addEventListener("click", function () {
            instructions.hidden = !instructions.hidden;
            helpBtn.setAttribute(
                "title",
                instructions.hidden ? "Show help" : "Hide help"
            );
        });
        helpBtn.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                helpBtn.click();
            }
        });
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
        downBtn.addEventListener("click", function () {
            update(Number(input.value) - 1);
        });
        upBtn.addEventListener("click", function () {
            update(Number(input.value) + 1);
        });
        downBtn.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                downBtn.click();
            }
        });
        upBtn.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                upBtn.click();
            }
        });
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
