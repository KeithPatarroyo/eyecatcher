/**
 * CommunityAdmin: key step + pending list + approve/reject.
 * Exposes: CommunityAdmin.openAdminModal / closeAdminModal / submitAdminKey / renderAdminPendingList
 * Uses one delegated click handler on #admin-pending-list for .approve-btn and .reject-btn.
 */
import Toast from "../lib/toast.js";
import Utils from "../lib/utils.js";
import api from "../lib/api_client.js";
import DOM from "../lib/dom.js";
import CommunityBrowse from "./browse.js";

let _adminCtx = null;

const toast = (t, m, type) => Toast.show(t, m, type);

const showKeyError = (msg) => {
    const el = DOM.byId("admin-key-error");
    if (!el) return;
    DOM.setText(el, msg);
    DOM.toggleClass(el, "hidden", !msg);
};

const openAdminModal = (ctx) => {
    ctx.setAdminKey?.("");
    const keyInput = DOM.byId("admin-key-input");
    if (keyInput) keyInput.value = "";
    showKeyError("");

    DOM.toggleClass(DOM.byId("admin-step-key"), "hidden", false);
    DOM.toggleClass(DOM.byId("admin-step-list"), "hidden", true);
    DOM.toggleClass(DOM.byId("admin-modal"), "show", true);
};

const closeAdminModal = (ctx) => {
    ctx.setAdminKey?.("");
    DOM.toggleClass(DOM.byId("admin-modal"), "show", false);
};

const adminModerate = async (id, action, rowEl, ctx) => {
    const key = ctx.getAdminKey?.() || "";
    try {
        if (api?.communityAdminDelete && action === "delete") {
            await api.communityAdminDelete(key, [id]);
        } else {
            const endpoint =
                action === "approve" ? "/api/admin/approve" : "/api/admin/reject";
            const url = `${ctx.apiUrl || ""}${endpoint}`;
            const result = await api?.request?.(url, {
                method: "POST",
                headers: { "X-Admin-Key": key },
                body: { id },
            });
            if (!result?.ok)
                throw new Error(
                    result?.error || `Moderation failed (${result?.status})`
                );
        }

        rowEl.remove();
    } catch (e) {
        const msg = e?.status === 403 ? "Invalid API key." : e?.message || String(e);
        toast("Admin", msg, "error");
    }
};

const renderAdminPendingList = async (submissions, ctx) => {
    const ul = DOM.byId("admin-pending-list");
    if (!ul) return;

    _adminCtx = ctx;

    if (ul.dataset.delegationBound !== "true") {
        ul.dataset.delegationBound = "true";
        DOM.delegate(ul, "click", ".approve-btn, .reject-btn", (ev, btn) => {
            const row = btn.closest?.("li") || btn.closest?.(".pending-item");
            if (!row) return;
            const id = row.dataset?.submissionId;
            const action = btn.classList.contains("approve-btn") ? "approve" : "reject";
            if (id) adminModerate(id, action, row, _adminCtx || {});
        });
    }

    const Browse = CommunityBrowse;

    ul.innerHTML = "";
    if (!Browse || !submissions?.length) {
        ul.appendChild(
            Utils?.createListEmptyEl
                ? Utils.createListEmptyEl("li", "No pending submissions.")
                : document.createElement("li")
        );
        if (!Utils?.createListEmptyEl)
            ul.firstChild.textContent = "No pending submissions.";
        return;
    }

    const displayByKey = await Browse.fetchDisplayDataForList(
        submissions,
        (s) => ({ ...(s.individual || s.genome), key: s.id }),
        (s) => s.id
    );

    Browse.renderListWithPreviews(
        ul,
        submissions,
        displayByKey,
        (s) => s.id,
        (li, sub, canvas, displayItem) =>
            Browse.buildPatternListEntry(li, sub, canvas, displayItem, {
                itemClass: "pending-item",
                infoContent: (s) => {
                    const frag = document.createDocumentFragment();
                    const strong = document.createElement("strong");
                    strong.textContent = s.name || "Unnamed";
                    frag.appendChild(strong);
                    frag.appendChild(
                        document.createTextNode(` by ${s.creator || "?"}`)
                    );
                    return frag;
                },
                appendNodes: (row, s) => {
                    row.dataset.submissionId = s.id;
                    const actions = document.createElement("div");
                    actions.className = "actions";

                    const approveBtn = document.createElement("button");
                    approveBtn.type = "button";
                    approveBtn.className = "approve-btn";
                    approveBtn.textContent = "Approve";
                    const rejectBtn = document.createElement("button");
                    rejectBtn.type = "button";
                    rejectBtn.className = "reject-btn";
                    rejectBtn.textContent = "Reject";

                    actions.appendChild(approveBtn);
                    actions.appendChild(rejectBtn);
                    row.appendChild(actions);
                },
            }),
        ctx.patternRenderer,
        ctx.viewerControls
    );
};

const submitAdminKey = async (ctx) => {
    const key = (DOM.byId("admin-key-input")?.value || "").trim();
    if (!key) return showKeyError("Please enter the API key.");

    const result = api
        ? await api.request(`${ctx.apiUrl || ""}/api/admin/submissions`, {
              method: "GET",
              headers: { "X-Admin-Key": key },
          })
        : { ok: false, error: "No API client", status: 0 };

    if (!result.ok) {
        showKeyError(
            result.status === 403
                ? "Invalid API key."
                : result.error || "Request failed"
        );
        return;
    }

    ctx.setAdminKey?.(key);
    showKeyError("");
    DOM.toggleClass(DOM.byId("admin-step-key"), "hidden", true);
    DOM.toggleClass(DOM.byId("admin-step-list"), "hidden", false);
    await renderAdminPendingList(result.data?.submissions || [], ctx);
};

const CommunityAdmin = {
    openAdminModal,
    closeAdminModal,
    submitAdminKey,
    renderAdminPendingList,
};

export default CommunityAdmin;
export { CommunityAdmin };
