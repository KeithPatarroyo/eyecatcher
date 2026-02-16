/**
 * CommunitySubmit: modal + POST submit.
 * Exposes: CommunitySubmit.openSubmitCommunityModal / closeSubmitCommunityModal / submitCommunityForm
 */
import Toast from "../lib/toast.js";
import api from "../lib/api_client.js";
import DOM from "../lib/dom.js";

const toast = (t, m, type) => Toast.show(t, m, type);

const openSubmitCommunityModal = async (patternId, ctx) => {
    ctx.showLoading?.(true);
    const genome = (await ctx.getGenomeForPattern?.(patternId)) || null;
    ctx.showLoading?.(false);

    if (!genome) return toast("Submit", "Could not get pattern data.", "error");

    ctx.setSubmitGenome?.(genome);
    const nameEl = DOM.byId("community-submit-name");
    const creatorEl = DOM.byId("community-submit-creator");
    if (nameEl) nameEl.value = "";
    if (creatorEl) creatorEl.value = "";

    DOM.toggleClass(DOM.byId("community-submit-modal"), "show", true);
};

const closeSubmitCommunityModal = (ctx) => {
    ctx.setSubmitGenome?.(null);
    DOM.toggleClass(DOM.byId("community-submit-modal"), "show", false);
};

const submitCommunityForm = async (ctx) => {
    const genome = ctx.getSubmitGenome?.();
    if (!genome) return;

    const name = (DOM.byId("community-submit-name")?.value || "").trim() || "Unnamed";
    const creator =
        (DOM.byId("community-submit-creator")?.value || "").trim() || "Anonymous";

    const url = `${ctx.apiUrl || ""}/api/community/submit`;
    const result = await api.request(url, {
        method: "POST",
        body: { individual: genome, name, creator },
    });

    if (!result.ok) {
        toast("Submit failed", result.error || "Request failed", "error");
        return;
    }
    toast("Submitted", "It will be reviewed before appearing in Community.", "success");
    closeSubmitCommunityModal(ctx);
};

const CommunitySubmit = {
    openSubmitCommunityModal,
    closeSubmitCommunityModal,
    submitCommunityForm,
};

export default CommunitySubmit;
export { CommunitySubmit };
window.CommunitySubmit = CommunitySubmit;
