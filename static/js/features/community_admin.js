/**
 * Community admin: key step, pending list, approve/reject.
 * Used by community.js. Exposes: CommunityAdmin.
 */
(function () {
    "use strict";

    function openAdminModal(ctx) {
        if (ctx.setAdminKey) ctx.setAdminKey("");
        const keyInput = document.getElementById("admin-key-input");
        if (keyInput) keyInput.value = "";
        const errEl = document.getElementById("admin-key-error");
        if (errEl) {
            errEl.classList.add("hidden");
            errEl.textContent = "";
        }
        const stepKey = document.getElementById("admin-step-key");
        const stepList = document.getElementById("admin-step-list");
        if (stepKey) stepKey.classList.remove("hidden");
        if (stepList) stepList.classList.add("hidden");
        const modal = document.getElementById("admin-modal");
        if (modal) modal.classList.add("show");
    }

    function closeAdminModal(ctx) {
        if (ctx.setAdminKey) ctx.setAdminKey("");
        const modal = document.getElementById("admin-modal");
        if (modal) modal.classList.remove("show");
    }

    async function submitAdminKey(ctx) {
        const key = (document.getElementById("admin-key-input")?.value || "").trim();
        const errEl = document.getElementById("admin-key-error");
        if (!key) {
            if (errEl) {
                errEl.textContent = "Please enter the API key.";
                errEl.classList.remove("hidden");
            }
            return;
        }
        const Utils = window.Utils;
        const ApiClient = window.ApiClient;
        try {
            const d = await ApiClient.apiFetch(
                (ctx.apiUrl || "") +
                    "/admin/submissions?admin_key=" +
                    encodeURIComponent(key),
                { headers: { "X-Admin-Key": key } },
                "Load submissions failed"
            );
            if (ctx.setAdminKey) ctx.setAdminKey(key);
            const list = d.submissions || [];
            const stepKey = document.getElementById("admin-step-key");
            const stepList = document.getElementById("admin-step-list");
            if (stepKey) stepKey.classList.add("hidden");
            if (stepList) stepList.classList.remove("hidden");
            await renderAdminPendingList(list, ctx);
        } catch (e) {
            if (errEl) {
                errEl.textContent =
                    e.status === 403
                        ? "Invalid API key."
                        : "Error: " +
                          (Utils && Utils.formatApiError
                              ? Utils.formatApiError(e, "Request failed")
                              : String(e));
                errEl.classList.remove("hidden");
            }
        }
    }

    async function renderAdminPendingList(submissions, ctx) {
        const ul = document.getElementById("admin-pending-list");
        if (!ul) return;
        ul.innerHTML = "";
        const Utils = window.Utils;
        const Browse = window.CommunityBrowse;
        if (!Browse || !submissions.length) {
            ul.appendChild(
                Utils && Utils.createListEmptyEl
                    ? Utils.createListEmptyEl("li", "No pending submissions.")
                    : (() => {
                          const li = document.createElement("li");
                          li.textContent = "No pending submissions.";
                          return li;
                      })()
            );
            return;
        }
        const displayByKey = await Browse.fetchDisplayDataForList(
            submissions,
            (s) => ({ ...s.genome, key: s.id }),
            (sub) => sub.id
        );
        Browse.renderListWithPreviews(
            ul,
            submissions,
            displayByKey,
            (sub) => sub.id,
            (li, sub, canvas, displayItem) =>
                Browse.buildPatternListEntry(
                    li,
                    sub,
                    canvas,
                    displayItem,
                    {
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
                                adminModerate(s.id, "approve", listItem, ctx)
                            );
                            const rejectBtn = document.createElement("button");
                            rejectBtn.type = "button";
                            rejectBtn.className = "reject-btn";
                            rejectBtn.textContent = "Reject";
                            rejectBtn.addEventListener("click", () =>
                                adminModerate(s.id, "reject", listItem, ctx)
                            );
                            actions.appendChild(approveBtn);
                            actions.appendChild(rejectBtn);
                            listItem.appendChild(actions);
                        },
                    },
                    ctx.patternRenderer
                ),
            ctx.patternRenderer,
            ctx.viewerControls
        );
    }

    async function adminModerate(id, action, rowEl, ctx) {
        const endpoint = action === "approve" ? "/admin/approve" : "/admin/reject";
        const errorLabel = action === "approve" ? "Approve failed" : "Reject failed";
        const adminKey = ctx.getAdminKey ? ctx.getAdminKey() : "";
        const ApiClient = window.ApiClient;
        try {
            await ApiClient.apiFetch(
                (ctx.apiUrl || "") +
                    endpoint +
                    "?admin_key=" +
                    encodeURIComponent(adminKey),
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Admin-Key": adminKey,
                    },
                    body: JSON.stringify({ id }),
                },
                errorLabel
            );
            rowEl.remove();
        } catch (e) {
            if (window.Toast) {
                window.Toast.error(
                    e.status === 403
                        ? "Invalid API key."
                        : "Error: " + (e.message || String(e))
                );
            }
        }
    }

    window.CommunityAdmin = {
        openAdminModal: openAdminModal,
        closeAdminModal: closeAdminModal,
        submitAdminKey: submitAdminKey,
        renderAdminPendingList: renderAdminPendingList,
    };
})();
