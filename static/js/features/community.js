/**
 * Community UI Module for Eyecatcher
 *
 * Handles community pattern submission, browsing, and admin moderation.
 * Thumbnails use SubstrateAdapters.getDisplayData so shader and grid substrates both work.
 *
 * Dependencies:
 * - API_URL global, SubstrateAdapters (getDisplayData, findAdapterByGenome)
 * - patternRenderer, viewerControls for previews
 * - loadFromStatelessGenomes, addToGrid
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
     * Fetch display data for a list of items using substrate adapters (compile or evaluate).
     * Returns map key -> display item { id, shader?, image?, outputType, ... }.
     * @param {Array} list
     * @param {Function} toItem - (item) => { genome, key } e.g. (pat) => ({ ...pat.genome, key: pat.id })
     * @param {Function} getKey - (item) => key e.g. (pat) => pat.id
     * @returns {Promise<Object>} displayByKey
     */
    async function fetchDisplayDataForList(list, toItem, getKey) {
        const SubstrateAdapters = window.SubstrateAdapters;
        if (
            !SubstrateAdapters ||
            !SubstrateAdapters.getDisplayData ||
            !SubstrateAdapters.findAdapterByGenome
        ) {
            return {};
        }
        const displayByKey = {};
        const promises = list.map(async (item) => {
            const payload = toItem(item);
            const genome =
                payload && (payload.genome !== undefined ? payload.genome : payload);
            const key = getKey(item);
            const adapter = SubstrateAdapters.findAdapterByGenome(genome);
            if (!adapter) return;
            try {
                const result = await SubstrateAdapters.getDisplayData(
                    adapter,
                    [genome],
                    {}
                );
                const pop = result && result.population && result.population[0];
                if (pop) displayByKey[key] = pop;
            } catch (e) {
                console.warn("Could not fetch preview for item " + key + ":", e);
            }
        });
        await Promise.all(promises);
        return displayByKey;
    }

    /**
     * Build one list entry: li + preview (canvas or img) + info. Uses displayItem from getDisplayData (shader or image).
     * @param {HTMLLIElement} li
     * @param {*} item
     * @param {HTMLCanvasElement} canvas
     * @param {Object|null} displayItem - { shader?, image?, outputType } from SubstrateAdapters.getDisplayData
     * @param {Object} options - itemClass, dataset, prependNodes, infoContent, appendNodes
     * @returns {Object|null} patternData for renderWithSignals (shader only) or null
     */
    function buildPatternListEntry(li, item, canvas, displayItem, options) {
        li.className = options.itemClass || "";
        if (options.dataset) {
            Object.keys(options.dataset).forEach((k) => {
                li.dataset[k] = options.dataset[k];
            });
        }
        if (options.prependNodes) options.prependNodes(li, item);
        const previewWrap = canvas.parentElement;
        if (displayItem && displayItem.image) {
            const img = document.createElement("img");
            img.className = "preview-img";
            img.src = displayItem.image;
            img.width = PREVIEW_CANVAS_SIZE;
            img.alt = "";
            previewWrap.innerHTML = "";
            previewWrap.appendChild(img);
        }
        li.appendChild(previewWrap);
        const info = document.createElement("div");
        info.className = "info";
        const content = options.infoContent ? options.infoContent(item) : "";
        if (typeof content === "string") {
            info.textContent = content;
        } else if (content) {
            info.appendChild(content);
        }
        li.appendChild(info);
        if (options.appendNodes) options.appendNodes(li, item);
        if (displayItem && displayItem.shader && _patternRenderer) {
            return _patternRenderer.setupPattern(canvas, displayItem.shader);
        }
        return null;
    }

    /**
     * Render a list into ul with previews (canvas for shader, img for grid); buildLiContent adds content and returns patternData or null.
     * @param {HTMLUListElement} ul
     * @param {Array} list
     * @param {Object} displayByKey - key -> display item from getDisplayData
     * @param {Function} getItemKey - (item) => id
     * @param {Function} buildLiContent - (li, item, canvas, displayItem) => patternData|null
     */
    function renderListWithPreviews(
        ul,
        list,
        displayByKey,
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
            const displayItem = displayByKey[getItemKey(item)];
            const pd = buildLiContent(li, item, canvas, displayItem);
            if (pd) previewPatternData.push(pd);
            ul.appendChild(li);
        });
        if (
            _patternRenderer &&
            _viewerControls &&
            _viewerControls.signalState != null &&
            previewPatternData.length > 0
        ) {
            const signalState = _viewerControls.signalState;
            requestAnimationFrame(() => {
                previewPatternData.forEach((pd) =>
                    _patternRenderer.renderWithSignals(
                        pd,
                        _patternRenderer,
                        signalState,
                        null
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
                const displayByKey = await fetchDisplayDataForList(
                    _communityPatternsList,
                    (pat) => ({ ...pat.genome, key: pat.id }),
                    (pat) => pat.id
                );
                renderListWithPreviews(
                    ul,
                    _communityPatternsList,
                    displayByKey,
                    (pat) => pat.id,
                    (li, pat, canvas, displayItem) =>
                        buildPatternListEntry(li, pat, canvas, displayItem, {
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
                        })
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
            const d = await window.ApiClient.apiFetch(
                _apiUrl + "/admin/submissions?admin_key=" + encodeURIComponent(key),
                { headers: { "X-Admin-Key": key } },
                "Load submissions failed"
            );
            _adminKey = key;
            const list = d.submissions || [];
            document.getElementById("admin-step-key").classList.add("hidden");
            document.getElementById("admin-step-list").classList.remove("hidden");
            await renderAdminPendingList(list);
        } catch (e) {
            errEl.textContent =
                e.status === 403
                    ? "Invalid API key."
                    : "Error: " + Utils.formatApiError(e, "Request failed");
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
        const displayByKey = await fetchDisplayDataForList(
            submissions,
            (s) => ({ ...s.genome, key: s.id }),
            (sub) => sub.id
        );
        renderListWithPreviews(
            ul,
            submissions,
            displayByKey,
            (sub) => sub.id,
            (li, sub, canvas, displayItem) =>
                buildPatternListEntry(li, sub, canvas, displayItem, {
                    itemClass: "pending-item",
                    infoContent: (s) => {
                        const frag = document.createDocumentFragment();
                        const strong = document.createElement("strong");
                        strong.textContent = s.name || "Unnamed";
                        frag.appendChild(strong);
                        frag.appendChild(document.createTextNode(" by "));
                        frag.appendChild(document.createTextNode(s.creator || "?"));
                        return frag;
                    },
                    appendNodes: (listItem, s) => {
                        const actions = document.createElement("div");
                        actions.className = "actions";
                        const approveBtn = document.createElement("button");
                        approveBtn.type = "button";
                        approveBtn.className = "approve-btn";
                        approveBtn.textContent = "Approve";
                        approveBtn.addEventListener("click", () =>
                            adminModerate(s.id, "approve", listItem)
                        );
                        const rejectBtn = document.createElement("button");
                        rejectBtn.type = "button";
                        rejectBtn.className = "reject-btn";
                        rejectBtn.textContent = "Reject";
                        rejectBtn.addEventListener("click", () =>
                            adminModerate(s.id, "reject", listItem)
                        );
                        actions.appendChild(approveBtn);
                        actions.appendChild(rejectBtn);
                        listItem.appendChild(actions);
                    },
                })
        );
    }

    async function adminModerate(id, action, rowEl) {
        const endpoint = action === "approve" ? "/admin/approve" : "/admin/reject";
        const errorLabel = action === "approve" ? "Approve failed" : "Reject failed";
        try {
            await window.ApiClient.apiFetch(
                _apiUrl + endpoint + "?admin_key=" + encodeURIComponent(_adminKey),
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Admin-Key": _adminKey,
                    },
                    body: JSON.stringify({ id }),
                },
                errorLabel
            );
            rowEl.remove();
        } catch (e) {
            Toast.error(
                e.status === 403
                    ? "Invalid API key."
                    : "Error: " + (e.message || String(e))
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
