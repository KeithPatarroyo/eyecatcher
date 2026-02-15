/**
 * Community UI: entry point. Delegates to CommunityBrowse, CommunitySubmit, CommunityAdmin.
 * Handles community pattern submission, browsing, and admin moderation.
 */
(function () {
    "use strict";

    let _apiUrl = "";
    let _loadFromStatelessGenomes = null;
    let _addToGrid = null;
    let _getGenomeForPattern = null;
    let _patternRenderer = null;
    let _viewerControls = null;
    let _communityPatternsList = [];
    let _submitCommunityGenome = null;
    let _adminKey = "";

    function init(options) {
        _apiUrl = options.apiUrl || "";
        _loadFromStatelessGenomes = options.loadFromStatelessGenomes;
        _addToGrid = options.addToGrid;
        _getGenomeForPattern = options.getGenomeForPattern;
        _patternRenderer = options.patternRenderer || null;
        _viewerControls = options.viewerControls || null;
    }

    function delegate(moduleName, methodName, getContext) {
        var M = window[moduleName];
        if (!M) return;
        M[methodName](getContext());
    }

    function showLoading(show) {
        if (typeof window.showLoading === "function") {
            window.showLoading(show);
        }
    }

    // ----- Submit (delegate to CommunitySubmit) -----
    function openSubmitCommunityModal(patternId) {
        var Submit = window.CommunitySubmit;
        if (!Submit) return;
        Submit.openSubmitCommunityModal(patternId, {
            getGenomeForPattern: _getGenomeForPattern,
            setSubmitGenome: function (g) {
                _submitCommunityGenome = g;
            },
            getSubmitGenome: function () {
                return _submitCommunityGenome;
            },
            showLoading: showLoading,
        });
    }

    function closeSubmitCommunityModal() {
        delegate("CommunitySubmit", "closeSubmitCommunityModal", function () {
            return {
                setSubmitGenome: function (g) {
                    _submitCommunityGenome = g;
                },
            };
        });
    }

    function submitCommunityForm() {
        delegate("CommunitySubmit", "submitCommunityForm", function () {
            return {
                getSubmitGenome: function () {
                    return _submitCommunityGenome;
                },
                apiUrl: _apiUrl,
            };
        });
    }

    // ----- Browse (delegate to CommunityBrowse) -----
    async function onNewFromCommunityClick() {
        const Browse = window.CommunityBrowse;
        const Utils = window.Utils;
        if (!Browse) return;
        showLoading(true);
        try {
            const d = await window.ApiClient.apiFetch(
                _apiUrl + "/community",
                {},
                "Failed to load community"
            );
            _communityPatternsList = d.patterns || [];
            const ul = document.getElementById("community-list");
            if (!ul) return;
            ul.innerHTML = "";
            const loadSelectedBtn = document.getElementById(
                "community-load-selected-btn"
            );
            const load12Btn = document.getElementById("community-load-12-btn");
            const selectAllBtn = document.getElementById("community-select-all-btn");
            const deselectAllBtn = document.getElementById(
                "community-deselect-all-btn"
            );
            if (!_communityPatternsList.length) {
                ul.appendChild(
                    Utils.createListEmptyEl("li", "No approved community patterns yet.")
                );
                if (loadSelectedBtn) loadSelectedBtn.classList.add("hidden");
                if (load12Btn) load12Btn.classList.add("hidden");
                if (selectAllBtn) selectAllBtn.classList.add("hidden");
                if (deselectAllBtn) deselectAllBtn.classList.add("hidden");
            } else {
                if (loadSelectedBtn) loadSelectedBtn.classList.remove("hidden");
                if (load12Btn) load12Btn.classList.remove("hidden");
                if (selectAllBtn) selectAllBtn.classList.remove("hidden");
                if (deselectAllBtn) deselectAllBtn.classList.remove("hidden");
                const displayByKey = await Browse.fetchDisplayDataForList(
                    _communityPatternsList,
                    (pat) => ({ ...(pat.individual || pat.genome), key: pat.id }),
                    (pat) => pat.id
                );
                Browse.renderListWithPreviews(
                    ul,
                    _communityPatternsList,
                    displayByKey,
                    (pat) => pat.id,
                    (li, pat, canvas, displayItem) =>
                        Browse.buildPatternListEntry(
                            li,
                            pat,
                            canvas,
                            displayItem,
                            {
                                itemClass: "community-item",
                                dataset: {
                                    idx: String(_communityPatternsList.indexOf(pat)),
                                },
                                prependNodes: (listItem) => {
                                    const checkWrap = document.createElement("div");
                                    checkWrap.className = "check-wrap";
                                    const checkbox = document.createElement("input");
                                    checkbox.type = "checkbox";
                                    checkbox.checked = false;
                                    checkWrap.appendChild(checkbox);
                                    listItem.appendChild(checkWrap);
                                },
                                infoContent: (p) =>
                                    (p.name || "Unnamed") + " by " + (p.creator || "?"),
                            },
                            _patternRenderer
                        ),
                    _patternRenderer,
                    _viewerControls
                );
            }
            document.getElementById("community-list-modal").classList.add("show");
        } catch (e) {
            window.Toast.error("Error: " + Utils.formatApiError(e, "Request failed"));
        } finally {
            showLoading(false);
        }
    }

    function getCommunitySelectedGenomes() {
        const ul = document.getElementById("community-list");
        if (!ul) return [];
        const checked = ul.querySelectorAll(
            '.community-item input[type="checkbox"]:checked'
        );
        const genomes = [];
        checked.forEach((cb) => {
            const li = cb.closest(".community-item");
            const idx = parseInt(li.dataset.idx, 10);
            const pat = _communityPatternsList[idx];
            if (pat) genomes.push({ ...(pat.individual || pat.genome), key: pat.id });
        });
        return genomes;
    }

    function onCommunityLoadSelected() {
        const genomes = getCommunitySelectedGenomes();
        if (!genomes.length) {
            window.Toast.error("No patterns selected.");
            return;
        }
        document.getElementById("community-list-modal").classList.remove("show");
        if (_addToGrid) _addToGrid(genomes);
    }

    function onCommunityLoad12() {
        const n =
            (window.EvolutionConfig &&
                window.EvolutionConfig.DEFAULT_POPULATION_SIZE) ||
            12;
        const first12 = _communityPatternsList
            .slice(0, n)
            .map((p) => ({ ...(p.individual || p.genome), key: p.id }));
        document.getElementById("community-list-modal").classList.remove("show");
        if (_addToGrid) _addToGrid(first12);
    }

    function onCommunitySelectAll() {
        document
            .querySelectorAll('#community-list .community-item input[type="checkbox"]')
            .forEach((cb) => {
                cb.checked = true;
            });
    }

    function onCommunityDeselectAll() {
        document
            .querySelectorAll('#community-list .community-item input[type="checkbox"]')
            .forEach((cb) => {
                cb.checked = false;
            });
    }

    // ----- Admin (delegate to CommunityAdmin) -----
    function openAdminModal() {
        delegate("CommunityAdmin", "openAdminModal", function () {
            return {
                setAdminKey: function (k) {
                    _adminKey = k;
                },
            };
        });
    }

    function closeAdminModal() {
        delegate("CommunityAdmin", "closeAdminModal", function () {
            return {
                setAdminKey: function (k) {
                    _adminKey = k;
                },
            };
        });
    }

    function submitAdminKey() {
        delegate("CommunityAdmin", "submitAdminKey", function () {
            return {
                setAdminKey: function (k) {
                    _adminKey = k;
                },
                getAdminKey: function () {
                    return _adminKey;
                },
                apiUrl: _apiUrl,
                patternRenderer: _patternRenderer,
                viewerControls: _viewerControls,
            };
        });
    }

    window.CommunityUI = {
        init: init,
        openSubmitCommunityModal: openSubmitCommunityModal,
        closeSubmitCommunityModal: closeSubmitCommunityModal,
        submitCommunityForm: submitCommunityForm,
        onNewFromCommunityClick: onNewFromCommunityClick,
        getCommunitySelectedGenomes: getCommunitySelectedGenomes,
        onCommunityLoadSelected: onCommunityLoadSelected,
        onCommunityLoad12: onCommunityLoad12,
        onCommunitySelectAll: onCommunitySelectAll,
        onCommunityDeselectAll: onCommunityDeselectAll,
        openAdminModal: openAdminModal,
        closeAdminModal: closeAdminModal,
        submitAdminKey: submitAdminKey,
    };
})();
