/**
 * Community UI Module for Eyecatcher
 *
 * Handles community pattern submission, browsing, and admin moderation.
 *
 * Dependencies:
 * - API_URL global
 * - patternRenderer, viewerControls for previews (PatternRenderer.setupPattern, .renderPattern + signalState)
 * - loadFromStatelessGenomes function
 * - addToGrid function (append patterns to current grid)
 */

(function () {
    "use strict";

    // Module state
    let _apiUrl = "";
    let _loadFromStatelessGenomes = null;
    let _addToGrid = null;
    let _getGenomeForPattern = null;
    let _patternRenderer = null;
    let _viewerControls = null;
    let _communityPatternsList = [];
    let _submitCommunityGenome = null;
    let _adminKey = "";

    const PREVIEW_CANVAS_SIZE = 80;

    /**
     * Compile a list of items to shaders; returns map id -> shader info.
     * @param {Array} list
     * @param {Function} toCompileItem - (item) => { genome, key, clicks }
     * @returns {Promise<Object>} shadersByKey
     */
    async function compileListToShaders(list, toCompileItem) {
        const shadersByKey = {};
        try {
            const compilePayload = list.map(toCompileItem);
            const compData = await window.ApiClient.compile(compilePayload);
            (compData.shaders || []).forEach((sh) => {
                shadersByKey[sh.id] = sh;
            });
        } catch (e) {
            console.warn("Could not compile previews:", e);
        }
        return shadersByKey;
    }

    /**
     * Render a list into ul with canvas previews; buildLiContent(li, item, canvas, shaderInfo) adds content and returns patternData or null.
     * @param {HTMLUListElement} ul
     * @param {Array} list
     * @param {Object} shadersByKey
     * @param {Function} getItemKey - (item) => id
     * @param {Function} buildLiContent - (li, item, canvas, shaderInfo) => patternData|null
     */
    function renderListWithPreviews(
        ul,
        list,
        shadersByKey,
        getItemKey,
        buildLiContent
    ) {
        const previewPatternData = [];
        list.forEach((item) => {
            const li = document.createElement("li");
            const previewWrap = document.createElement("div");
            previewWrap.className = "preview-wrap";
            const canvas = document.createElement("canvas");
            canvas.width = PREVIEW_CANVAS_SIZE;
            canvas.height = PREVIEW_CANVAS_SIZE;
            previewWrap.appendChild(canvas);
            const shaderInfo = shadersByKey[getItemKey(item)];
            const pd = buildLiContent(li, item, canvas, shaderInfo);
            if (pd) previewPatternData.push(pd);
            ul.appendChild(li);
        });
        if (
            _patternRenderer &&
            _viewerControls &&
            _viewerControls.signalState != null
        ) {
            const signalState = _viewerControls.signalState;
            var getSource = typeof window !== "undefined" && window.getSignalSource;
            var signalValues = (getSource &&
                getSource().getValues &&
                getSource().getValues({})) || { raw_time: 0.5 };
            var uniformValues =
                _patternRenderer.buildUniformValues &&
                _patternRenderer.buildUniformValues(signalValues);
            requestAnimationFrame(() => {
                previewPatternData.forEach((pd) =>
                    _patternRenderer.renderPattern(
                        pd,
                        uniformValues || signalValues,
                        signalState
                    )
                );
            });
        }
    }

    /**
     * Initialize the community UI module.
     * @param {Object} options
     * @param {string} options.apiUrl - Base API URL
     * @param {Function} options.loadFromStatelessGenomes - Function to load genomes into the grid (replace)
     * @param {Function} options.addToGrid - Function to append genomes to the current grid
     * @param {Function} options.getGenomeForPattern - Function to get genome for a pattern ID
     * @param {Object} options.patternRenderer - PatternRenderer module (setupPattern, renderPattern)
     * @param {Object} options.viewerControls - ViewerControls module (signalState for renderPattern)
     */
    function init(options) {
        _apiUrl = options.apiUrl || "";
        _loadFromStatelessGenomes = options.loadFromStatelessGenomes;
        _addToGrid = options.addToGrid;
        _getGenomeForPattern = options.getGenomeForPattern;
        _patternRenderer = options.patternRenderer || null;
        _viewerControls = options.viewerControls || null;
    }

    // -------------------------------------------------------------------------
    // Submit to Community
    // -------------------------------------------------------------------------

    async function openSubmitCommunityModal(patternId) {
        showLoading(true);
        const genome = _getGenomeForPattern
            ? await _getGenomeForPattern(patternId)
            : null;
        showLoading(false);
        if (!genome) {
            Toast.error("Could not get pattern data.");
            return;
        }
        _submitCommunityGenome = genome;
        document.getElementById("community-submit-name").value = "";
        document.getElementById("community-submit-creator").value = "";
        document.getElementById("community-submit-modal").classList.add("show");
    }

    function closeSubmitCommunityModal() {
        _submitCommunityGenome = null;
        document.getElementById("community-submit-modal").classList.remove("show");
    }

    async function submitCommunityForm() {
        if (!_submitCommunityGenome) return;
        const name =
            (document.getElementById("community-submit-name").value || "").trim() ||
            "Unnamed";
        const creator =
            (document.getElementById("community-submit-creator").value || "").trim() ||
            "Anonymous";
        try {
            await window.ApiClient.apiFetch(
                _apiUrl + "/community/submit",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        genome: _submitCommunityGenome,
                        name,
                        creator,
                    }),
                },
                "Submit failed"
            );
            Toast.show(
                "Submitted",
                "It will be reviewed before appearing in Community.",
                "success"
            );
            closeSubmitCommunityModal();
        } catch (e) {
            Toast.error("Error: " + Utils.formatApiError(e, "Request failed"));
        }
    }

    // -------------------------------------------------------------------------
    // Browse Community
    // -------------------------------------------------------------------------

    async function onNewFromCommunityClick() {
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
                const shadersByKey = await compileListToShaders(
                    _communityPatternsList,
                    (pat) => ({ ...pat.genome, key: pat.id, clicks: 0 })
                );
                renderListWithPreviews(
                    ul,
                    _communityPatternsList,
                    shadersByKey,
                    (pat) => pat.id,
                    (li, pat, canvas, shaderInfo) => {
                        li.className = "community-item";
                        li.dataset.idx = String(_communityPatternsList.indexOf(pat));
                        const checkWrap = document.createElement("div");
                        checkWrap.className = "check-wrap";
                        const checkbox = document.createElement("input");
                        checkbox.type = "checkbox";
                        checkbox.checked = false;
                        checkWrap.appendChild(checkbox);
                        li.appendChild(checkWrap);
                        li.appendChild(canvas.parentElement);
                        const info = document.createElement("div");
                        info.className = "info";
                        info.textContent =
                            (pat.name || "Unnamed") + " by " + (pat.creator || "?");
                        li.appendChild(info);
                        if (shaderInfo && shaderInfo.shader && _patternRenderer) {
                            return _patternRenderer.setupPattern(
                                canvas,
                                shaderInfo.shader
                            );
                        }
                        return null;
                    }
                );
            }
            document.getElementById("community-list-modal").classList.add("show");
        } catch (e) {
            Toast.error("Error: " + Utils.formatApiError(e, "Request failed"));
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
            if (pat) {
                genomes.push({ ...pat.genome, key: pat.id });
            }
        });
        return genomes;
    }

    function onCommunityLoadSelected() {
        const genomes = getCommunitySelectedGenomes();
        if (!genomes.length) {
            Toast.error("No patterns selected.");
            return;
        }
        document.getElementById("community-list-modal").classList.remove("show");
        if (_addToGrid) {
            _addToGrid(genomes);
        }
    }

    function onCommunityLoad12() {
        // Fallback must match EvolutionConfig; see evolution_config.js
        const n =
            (window.EvolutionConfig &&
                window.EvolutionConfig.DEFAULT_POPULATION_SIZE) ||
            12;
        const first12 = _communityPatternsList
            .slice(0, n)
            .map((p) => ({ ...p.genome, key: p.id }));
        document.getElementById("community-list-modal").classList.remove("show");
        if (_addToGrid) {
            _addToGrid(first12);
        }
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

    // -------------------------------------------------------------------------
    // Admin Moderation
    // -------------------------------------------------------------------------

    function openAdminModal() {
        _adminKey = "";
        document.getElementById("admin-key-input").value = "";
        const errEl = document.getElementById("admin-key-error");
        errEl.classList.add("hidden");
        errEl.textContent = "";
        document.getElementById("admin-step-key").classList.remove("hidden");
        document.getElementById("admin-step-list").classList.add("hidden");
        document.getElementById("admin-modal").classList.add("show");
    }

    function closeAdminModal() {
        _adminKey = "";
        document.getElementById("admin-modal").classList.remove("show");
    }

    async function submitAdminKey() {
        const key = (document.getElementById("admin-key-input").value || "").trim();
        const errEl = document.getElementById("admin-key-error");
        if (!key) {
            errEl.textContent = "Please enter the API key.";
            errEl.classList.remove("hidden");
            return;
        }
        try {
            const r = await fetch(
                _apiUrl + "/admin/submissions?admin_key=" + encodeURIComponent(key),
                {
                    headers: { "X-Admin-Key": key },
                }
            );
            if (r.status === 403) {
                errEl.textContent = "Invalid API key.";
                errEl.classList.remove("hidden");
                return;
            }
            if (!r.ok) {
                errEl.textContent = "Request failed (status " + r.status + ").";
                errEl.classList.remove("hidden");
                return;
            }
            _adminKey = key;
            const d = await r.json();
            const list = d.submissions || [];
            document.getElementById("admin-step-key").classList.add("hidden");
            document.getElementById("admin-step-list").classList.remove("hidden");
            await renderAdminPendingList(list);
        } catch (e) {
            if (e.status === 403) {
                errEl.textContent = "Invalid API key.";
            } else {
                errEl.textContent =
                    "Error: " + Utils.formatApiError(e, "Request failed");
            }
            errEl.classList.remove("hidden");
        }
    }

    async function renderAdminPendingList(submissions) {
        const ul = document.getElementById("admin-pending-list");
        ul.innerHTML = "";
        if (!submissions.length) {
            ul.appendChild(Utils.createListEmptyEl("li", "No pending submissions."));
            return;
        }
        const shadersByKey = await compileListToShaders(submissions, (s) => ({
            ...s.genome,
            key: s.id,
            clicks: 0,
        }));
        renderListWithPreviews(
            ul,
            submissions,
            shadersByKey,
            (sub) => sub.id,
            (li, sub, canvas, shaderInfo) => {
                li.className = "pending-item";
                li.appendChild(canvas.parentElement);
                const info = document.createElement("div");
                info.className = "info";
                const strong = document.createElement("strong");
                strong.textContent = sub.name || "Unnamed";
                info.appendChild(strong);
                info.appendChild(document.createTextNode(" by "));
                info.appendChild(document.createTextNode(sub.creator || "?"));
                li.appendChild(info);
                const actions = document.createElement("div");
                actions.className = "actions";
                const approveBtn = document.createElement("button");
                approveBtn.type = "button";
                approveBtn.className = "approve-btn";
                approveBtn.textContent = "Approve";
                approveBtn.addEventListener("click", () => adminApprove(sub.id, li));
                const rejectBtn = document.createElement("button");
                rejectBtn.type = "button";
                rejectBtn.className = "reject-btn";
                rejectBtn.textContent = "Reject";
                rejectBtn.addEventListener("click", () => adminReject(sub.id, li));
                actions.appendChild(approveBtn);
                actions.appendChild(rejectBtn);
                li.appendChild(actions);
                if (shaderInfo && shaderInfo.shader && _patternRenderer) {
                    return _patternRenderer.setupPattern(canvas, shaderInfo.shader);
                }
                return null;
            }
        );
    }

    async function adminApprove(id, rowEl) {
        try {
            await window.ApiClient.apiFetch(
                _apiUrl + "/admin/approve?admin_key=" + encodeURIComponent(_adminKey),
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Admin-Key": _adminKey,
                    },
                    body: JSON.stringify({ id }),
                },
                "Approve failed"
            );
            rowEl.remove();
        } catch (e) {
            Toast.error(
                e.status === 403 ? "Invalid API key." : "Error: " + (e.message || e)
            );
        }
    }

    async function adminReject(id, rowEl) {
        try {
            await window.ApiClient.apiFetch(
                _apiUrl + "/admin/reject?admin_key=" + encodeURIComponent(_adminKey),
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Admin-Key": _adminKey,
                    },
                    body: JSON.stringify({ id }),
                },
                "Reject failed"
            );
            rowEl.remove();
        } catch (e) {
            Toast.error(
                e.status === 403
                    ? "Invalid API key."
                    : "Error: " + Utils.formatApiError(e, "Request failed")
            );
        }
    }

    // Export to global namespace
    window.CommunityUI = {
        init: init,
        // Submit
        openSubmitCommunityModal: openSubmitCommunityModal,
        closeSubmitCommunityModal: closeSubmitCommunityModal,
        submitCommunityForm: submitCommunityForm,
        // Browse
        onNewFromCommunityClick: onNewFromCommunityClick,
        getCommunitySelectedGenomes: getCommunitySelectedGenomes,
        onCommunityLoadSelected: onCommunityLoadSelected,
        onCommunityLoad12: onCommunityLoad12,
        onCommunitySelectAll: onCommunitySelectAll,
        onCommunityDeselectAll: onCommunityDeselectAll,
        // Admin
        openAdminModal: openAdminModal,
        closeAdminModal: closeAdminModal,
        submitAdminKey: submitAdminKey,
    };
})();
