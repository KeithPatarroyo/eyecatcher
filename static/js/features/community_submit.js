/**
 * Community submit: modal and form for submitting a pattern.
 * Used by community.js. Exposes: CommunitySubmit.
 */
(function () {
    "use strict";

    async function openSubmitCommunityModal(patternId, ctx) {
        if (ctx.showLoading) ctx.showLoading(true);
        const genome = ctx.getGenomeForPattern
            ? await ctx.getGenomeForPattern(patternId)
            : null;
        if (ctx.showLoading) ctx.showLoading(false);
        if (!genome) {
            if (window.Toast) window.Toast.error("Could not get pattern data.");
            return;
        }
        if (ctx.setSubmitGenome) ctx.setSubmitGenome(genome);
        const nameEl = document.getElementById("community-submit-name");
        const creatorEl = document.getElementById("community-submit-creator");
        if (nameEl) nameEl.value = "";
        if (creatorEl) creatorEl.value = "";
        const modal = document.getElementById("community-submit-modal");
        if (modal) modal.classList.add("show");
    }

    function closeSubmitCommunityModal(ctx) {
        if (ctx.setSubmitGenome) ctx.setSubmitGenome(null);
        const modal = document.getElementById("community-submit-modal");
        if (modal) modal.classList.remove("show");
    }

    async function submitCommunityForm(ctx) {
        const genome = ctx.getSubmitGenome ? ctx.getSubmitGenome() : null;
        if (!genome) return;
        const name =
            (document.getElementById("community-submit-name")?.value || "").trim() ||
            "Unnamed";
        const creator =
            (document.getElementById("community-submit-creator")?.value || "").trim() ||
            "Anonymous";
        const Utils = window.Utils;
        const ApiClient = window.ApiClient;
        try {
            await ApiClient.apiFetch(
                (ctx.apiUrl || "") + "/community/submit",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ genome, name, creator }),
                },
                "Submit failed"
            );
            if (window.Toast && window.Toast.show) {
                window.Toast.show(
                    "Submitted",
                    "It will be reviewed before appearing in Community.",
                    "success"
                );
            }
            closeSubmitCommunityModal(ctx);
        } catch (e) {
            if (window.Toast) {
                window.Toast.error(
                    "Error: " +
                        (Utils && Utils.formatApiError
                            ? Utils.formatApiError(e, "Request failed")
                            : String(e))
                );
            }
        }
    }

    window.CommunitySubmit = {
        openSubmitCommunityModal: openSubmitCommunityModal,
        closeSubmitCommunityModal: closeSubmitCommunityModal,
        submitCommunityForm: submitCommunityForm,
    };
})();
