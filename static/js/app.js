/**
 * Eyecatcher app entry: init and DOM wiring. Core logic lives in app_core.js.
 * Load after: app_core.js and all module scripts. Depends on: ApiClient, AnimationLoop,
 * PatternRenderer, ViewerControls, PopulationUI, CommunityUI, NetworkVisualizer, Toast, initToolbarUI.
 */
(function () {
    "use strict";

    if (typeof vis === "undefined") {
        console.error(
            "ERROR: vis.js library not loaded! Network visualization will not work."
        );
    }

    var API_URL = window.API_URL || "";
    var IDS = {
        grid: "grid",
        fullscreenModal: "fullscreen-modal",
        fullscreenCanvasWrap: "fullscreen-canvas-wrap",
        gridErrorTpl: "grid-error-tpl",
        gridRetryBtn: "grid-retry-btn",
        genNum: "gen-num",
        breedBtn: "breed-btn",
        populationSizeInput: "population-size-input",
        totalClicks: "total-clicks",
        loadListModal: "load-list-modal",
        communityListModal: "community-list-modal",
        fullscreenClose: "fullscreen-close",
        fullscreenBackdrop: "fullscreen-backdrop",
        loadModalClose: "load-modal-close",
        communitySubmitDo: "community-submit-do",
        communitySubmitCancel: "community-submit-cancel",
        communityListClose: "community-list-close",
        communityLoadSelectedBtn: "community-load-selected-btn",
        communityLoad12Btn: "community-load-12-btn",
        communitySelectAllBtn: "community-select-all-btn",
        communityDeselectAllBtn: "community-deselect-all-btn",
        newFromCommunityBtn: "new-from-community-btn",
        adminKeySubmit: "admin-key-submit",
        adminModalCancel: "admin-modal-cancel",
        adminListClose: "admin-list-close",
        adminKeyInput: "admin-key-input",
        saveCurrentBtn: "save-current-btn",
        importBtn: "import-btn",
        importFile: "import-file",
    };

    function onId(id, fn) {
        var el = document.getElementById(id);
        if (el) fn(el);
    }

    function onRoleButtonKeydown(e, onClick) {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onClick();
        }
    }

    AppCore.init(API_URL, IDS);

    window.ApiClient.init(API_URL);

    window.AnimationLoop.init({
        getPatterns: AppCore.getPatterns,
        patternRenderer: window.PatternRenderer || null,
        viewerControls: window.ViewerControls || null,
    });

    window.PopulationUI.init({
        apiUrl: API_URL,
        loadFromStatelessGenomes: AppCore.loadFromStatelessGenomes,
        addToGrid: AppCore.addToGrid,
        getCurrentGenomesForSave: AppCore.getCurrentGenomesForSave,
    });

    window.CommunityUI.init({
        apiUrl: API_URL,
        loadFromStatelessGenomes: AppCore.loadFromStatelessGenomes,
        addToGrid: AppCore.addToGrid,
        getGenomeForPattern: AppCore.getGenomeForPattern,
        patternRenderer: window.PatternRenderer || null,
        viewerControls: window.ViewerControls || null,
    });

    window.NetworkVisualizer.init({
        apiUrl: API_URL,
        getGenomeForPattern: AppCore.getGenomeForPattern,
        updatePatternShader: AppCore.updatePatternShader,
        getCurrentPopulation: AppCore.getCurrentPopulation,
        onGenomeUpdated: AppCore.onGenomeUpdated,
    });

    if (window.initToolbarUI) window.initToolbarUI();

    document.querySelectorAll('input[name="colorMode"]').forEach(function (radio) {
        radio.addEventListener("change", function () {
            if (AppCore.getCurrentGenomesForSave()) {
                var data = AppCore.getCurrentGenomesForSave();
                AppCore.loadFromStatelessGenomes(data.genomes, data.generation, false);
            }
        });
    });

    onId(IDS.fullscreenClose, function (el) {
        el.addEventListener("click", AppCore.closeFullscreen);
    });
    onId(IDS.fullscreenBackdrop, function (el) {
        el.addEventListener("click", AppCore.closeFullscreen);
    });
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") AppCore.closeFullscreen();
    });

    onId(IDS.breedBtn, function (el) {
        el.addEventListener("click", AppCore.breedGeneration);
        el.addEventListener("keydown", function (e) {
            onRoleButtonKeydown(e, AppCore.breedGeneration);
        });
    });

    onId(IDS.loadModalClose, function (el) {
        el.addEventListener("click", function () {
            var modal = document.getElementById(IDS.loadListModal);
            if (modal) modal.classList.remove("show");
        });
    });
    onId(IDS.communitySubmitDo, function (el) {
        el.addEventListener("click", window.CommunityUI.submitCommunityForm);
    });
    onId(IDS.communitySubmitCancel, function (el) {
        el.addEventListener("click", window.CommunityUI.closeSubmitCommunityModal);
    });
    onId(IDS.communityListClose, function (el) {
        el.addEventListener("click", function () {
            var modal = document.getElementById(IDS.communityListModal);
            if (modal) modal.classList.remove("show");
        });
    });
    onId(IDS.communityLoadSelectedBtn, function (el) {
        el.addEventListener("click", window.CommunityUI.onCommunityLoadSelected);
    });
    onId(IDS.communityLoad12Btn, function (el) {
        el.addEventListener("click", window.CommunityUI.onCommunityLoad12);
    });
    onId(IDS.communitySelectAllBtn, function (el) {
        el.addEventListener("click", window.CommunityUI.onCommunitySelectAll);
    });
    onId(IDS.communityDeselectAllBtn, function (el) {
        el.addEventListener("click", window.CommunityUI.onCommunityDeselectAll);
    });
    onId(IDS.newFromCommunityBtn, function (el) {
        el.addEventListener("click", window.CommunityUI.onNewFromCommunityClick);
        el.addEventListener("keydown", function (e) {
            onRoleButtonKeydown(e, window.CommunityUI.onNewFromCommunityClick);
        });
    });
    onId(IDS.adminKeySubmit, function (el) {
        el.addEventListener("click", window.CommunityUI.submitAdminKey);
    });
    onId(IDS.adminModalCancel, function (el) {
        el.addEventListener("click", window.CommunityUI.closeAdminModal);
    });
    onId(IDS.adminListClose, function (el) {
        el.addEventListener("click", window.CommunityUI.closeAdminModal);
    });
    onId(IDS.adminKeyInput, function (el) {
        el.addEventListener("keydown", function (e) {
            if (e.key === "Enter") window.CommunityUI.submitAdminKey();
        });
    });
    onId(IDS.saveCurrentBtn, function (el) {
        el.addEventListener("click", window.PopulationUI.onSaveCurrentClick);
    });
    onId(IDS.importBtn, function (el) {
        el.addEventListener("click", window.PopulationUI.onImportClick);
    });
    onId(IDS.importFile, function (el) {
        el.addEventListener("change", function (e) {
            var file = e.target.files && e.target.files[0];
            e.target.value = "";
            if (file && typeof window.PopulationUI.handleImportFile === "function") {
                window.PopulationUI.handleImportFile(file);
            }
        });
    });

    window.ViewerControls.init();

    if (typeof window.EyecatcherDebug !== "undefined") {
        window.EyecatcherDebug.init({
            apiUrl: API_URL,
            getMouseDistance: window.AnimationLoop.getMouseDistance,
            getPatterns: AppCore.getPatternsMap,
            getSignalState: function () {
                return window.ViewerControls.signalState;
            },
            getGenomeForPattern: AppCore.getGenomeForPattern,
        });
    }

    var genealogyLoad = null;
    var raw = Utils.safeGetItem(
        typeof localStorage !== "undefined" ? localStorage : null,
        "genealogy_load",
        null
    );
    if (raw) {
        try {
            genealogyLoad = JSON.parse(raw);
            try {
                localStorage.removeItem("genealogy_load");
            } catch (_e) {
                /* ignore */
            }
        } catch (e) {
            console.warn("Genealogy load parse failed:", e);
        }
    }
    if (genealogyLoad && genealogyLoad.genomes && genealogyLoad.genomes.length) {
        AppCore.setGenealogyState(
            genealogyLoad.population_id != null ? genealogyLoad.population_id : null,
            genealogyLoad.branch_name || "main"
        );
        var genNum =
            genealogyLoad.generation_num != null ? genealogyLoad.generation_num : 0;
        AppCore.loadFromStatelessGenomes(genealogyLoad.genomes, genNum, false);
    } else {
        window.PopulationUI.startNewRandomPopulation();
    }
    window.AnimationLoop.start();

    console.log("Eyecatcher Interactive Evolution ready!");
})();
