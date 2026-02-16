/**
 * Community UI: entry point. Delegates to CommunityBrowse, CommunitySubmit, CommunityAdmin.
 * Exposes: CommunityUI.init + handler functions used by HTML onclick.
 */
(() => {
    "use strict";

    let apiUrl = "";
    let addToGrid = null;
    let getGenomeForPattern = null;
    let patternRenderer = null;
    let viewerControls = null;

    let communityPatterns = [];
    let submitGenome = null;
    let adminKey = "";

    const showLoading = (show) => window.showLoading?.(Boolean(show));
    const toast = (t, m, type) => window.Toast?.show?.(t, m, type);

    const init = (options) => {
        apiUrl = options.apiUrl || "";
        addToGrid = options.addToGrid || null;
        getGenomeForPattern = options.getGenomeForPattern || null;
        patternRenderer = options.patternRenderer || null;
        viewerControls = options.viewerControls || null;
    };

    // ----- Submit -----
    const openSubmitCommunityModal = (patternId) =>
        window.CommunitySubmit?.openSubmitCommunityModal?.(patternId, {
            getGenomeForPattern,
            setSubmitGenome: (g) => (submitGenome = g),
            getSubmitGenome: () => submitGenome,
            showLoading,
        });

    const closeSubmitCommunityModal = () =>
        window.CommunitySubmit?.closeSubmitCommunityModal?.({
            setSubmitGenome: (g) => (submitGenome = g),
        });

    const submitCommunityForm = () =>
        window.CommunitySubmit?.submitCommunityForm?.({
            apiUrl,
            getSubmitGenome: () => submitGenome,
        });

    // ----- Browse -----
    const selectedGenomes = () => {
        const ul = document.getElementById("community-list");
        if (!ul) return [];
        return Array.from(
            ul.querySelectorAll('.community-item input[type="checkbox"]:checked')
        )
            .map((cb) => cb.closest(".community-item"))
            .map((li) => communityPatterns[parseInt(li.dataset.idx, 10)])
            .filter(Boolean)
            .map((p) => ({ ...(p.individual || p.genome), key: p.id }));
    };

    const onCommunityLoadSelected = () => {
        const genomes = selectedGenomes();
        if (!genomes.length)
            return toast("Community", "No patterns selected.", "error");
        document.getElementById("community-list-modal")?.classList.remove("show");
        addToGrid?.(genomes);
    };

    const onCommunityLoad12 = () => {
        const n = window.EvolutionConfig?.DEFAULT_POPULATION_SIZE || 12;
        const genomes = (communityPatterns || [])
            .slice(0, n)
            .map((p) => ({ ...(p.individual || p.genome), key: p.id }));
        document.getElementById("community-list-modal")?.classList.remove("show");
        addToGrid?.(genomes);
    };

    const setAllChecks = (checked) => {
        document
            .querySelectorAll('#community-list .community-item input[type="checkbox"]')
            .forEach((cb) => (cb.checked = checked));
    };

    const onCommunitySelectAll = () => setAllChecks(true);
    const onCommunityDeselectAll = () => setAllChecks(false);

    const onNewFromCommunityClick = async () => {
        const Browse = window.CommunityBrowse;
        const Utils = window.Utils;
        if (!Browse) return;

        showLoading(true);
        try {
            const d = window.ApiClient?.communityList
                ? await window.ApiClient.communityList()
                : await (await fetch(`${apiUrl}/api/community`)).json();

            communityPatterns = d.patterns || [];
            const ul = document.getElementById("community-list");
            if (!ul) return;

            const toggle = (id, show) =>
                document.getElementById(id)?.classList.toggle("hidden", !show);

            const hasAny = communityPatterns.length > 0;
            toggle("community-load-selected-btn", hasAny);
            toggle("community-load-12-btn", hasAny);
            toggle("community-select-all-btn", hasAny);
            toggle("community-deselect-all-btn", hasAny);

            ul.innerHTML = "";
            if (!hasAny) {
                ul.appendChild(
                    Utils?.createListEmptyEl
                        ? Utils.createListEmptyEl(
                              "li",
                              "No approved community patterns yet."
                          )
                        : document.createElement("li")
                );
                if (!Utils?.createListEmptyEl)
                    ul.firstChild.textContent = "No approved community patterns yet.";
            } else {
                const displayByKey = await Browse.fetchDisplayDataForList(
                    communityPatterns,
                    (pat) => ({ ...(pat.individual || pat.genome), key: pat.id }),
                    (pat) => pat.id
                );

                Browse.renderListWithPreviews(
                    ul,
                    communityPatterns,
                    displayByKey,
                    (pat) => pat.id,
                    (li, pat, canvas, displayItem) =>
                        Browse.buildPatternListEntry(li, pat, canvas, displayItem, {
                            itemClass: "community-item",
                            dataset: { idx: String(communityPatterns.indexOf(pat)) },
                            prependNodes: (row) => {
                                const w = document.createElement("div");
                                w.className = "check-wrap";
                                const cb = document.createElement("input");
                                cb.type = "checkbox";
                                cb.checked = false;
                                w.appendChild(cb);
                                row.appendChild(w);
                            },
                            infoContent: (p) =>
                                `${p.name || "Unnamed"} by ${p.creator || "?"}`,
                        }),
                    patternRenderer,
                    viewerControls
                );
            }

            document.getElementById("community-list-modal")?.classList.add("show");
        } catch (e) {
            const msg = Utils?.formatApiError
                ? Utils.formatApiError(e, "Request failed")
                : String(e);
            toast("Community load failed", msg, "error");
        } finally {
            showLoading(false);
        }
    };

    // ----- Admin -----
    const openAdminModal = () =>
        window.CommunityAdmin?.openAdminModal?.({
            setAdminKey: (k) => (adminKey = k),
        });

    const closeAdminModal = () =>
        window.CommunityAdmin?.closeAdminModal?.({
            setAdminKey: (k) => (adminKey = k),
        });

    const submitAdminKey = () =>
        window.CommunityAdmin?.submitAdminKey?.({
            apiUrl,
            getAdminKey: () => adminKey,
            setAdminKey: (k) => (adminKey = k),
            patternRenderer,
            viewerControls,
        });

    // Expose for HTML onclick
    window.CommunityUI = {
        init,
        openSubmitCommunityModal,
        closeSubmitCommunityModal,
        submitCommunityForm,
        onNewFromCommunityClick,
        onCommunityLoadSelected,
        onCommunityLoad12,
        onCommunitySelectAll,
        onCommunityDeselectAll,
        openAdminModal,
        closeAdminModal,
        submitAdminKey,
    };
})();
