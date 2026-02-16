/**
 * CommunitySubmit: modal + POST submit.
 * Exposes: CommunitySubmit.openSubmitCommunityModal / closeSubmitCommunityModal / submitCommunityForm
 */
(() => {
    "use strict";

    const toast = (t, m, type) => window.Toast?.show?.(t, m, type);

    const openSubmitCommunityModal = async (patternId, ctx) => {
        ctx.showLoading?.(true);
        const genome = (await ctx.getGenomeForPattern?.(patternId)) || null;
        ctx.showLoading?.(false);

        if (!genome) return toast("Submit", "Could not get pattern data.", "error");

        ctx.setSubmitGenome?.(genome);
        document.getElementById("community-submit-name")?.setAttribute("value", "");
        const nameEl = document.getElementById("community-submit-name");
        const creatorEl = document.getElementById("community-submit-creator");
        if (nameEl) nameEl.value = "";
        if (creatorEl) creatorEl.value = "";

        document.getElementById("community-submit-modal")?.classList.add("show");
    };

    const closeSubmitCommunityModal = (ctx) => {
        ctx.setSubmitGenome?.(null);
        document.getElementById("community-submit-modal")?.classList.remove("show");
    };

    const submitCommunityForm = async (ctx) => {
        const genome = ctx.getSubmitGenome?.();
        if (!genome) return;

        const name =
            (document.getElementById("community-submit-name")?.value || "").trim() ||
            "Unnamed";
        const creator =
            (document.getElementById("community-submit-creator")?.value || "").trim() ||
            "Anonymous";

        try {
            if (window.ApiClient?.communitySubmit) {
                await window.ApiClient.communitySubmit({
                    individual: genome,
                    name,
                    creator,
                });
            } else {
                // Fallback for older ApiClient
                await fetch(`${ctx.apiUrl || ""}/api/community/submit`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ individual: genome, name, creator }),
                });
            }

            toast(
                "Submitted",
                "It will be reviewed before appearing in Community.",
                "success"
            );
            closeSubmitCommunityModal(ctx);
        } catch (e) {
            const msg = window.Utils?.formatApiError
                ? window.Utils.formatApiError(e, "Request failed")
                : String(e);
            toast("Submit failed", msg, "error");
        }
    };

    window.CommunitySubmit = {
        openSubmitCommunityModal,
        closeSubmitCommunityModal,
        submitCommunityForm,
    };
})();
