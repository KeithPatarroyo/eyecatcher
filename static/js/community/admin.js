/**
 * CommunityAdmin: key step + pending list + approve/reject.
 * Exposes: CommunityAdmin.openAdminModal / closeAdminModal / submitAdminKey / renderAdminPendingList
 */
(() => {
    "use strict";

    const toast = (t, m, type) => window.Toast?.show?.(t, m, type);

    const showKeyError = (msg) => {
        const el = document.getElementById("admin-key-error");
        if (!el) return;
        el.textContent = msg;
        el.classList.toggle("hidden", !msg);
    };

    const openAdminModal = (ctx) => {
        ctx.setAdminKey?.("");
        const keyInput = document.getElementById("admin-key-input");
        if (keyInput) keyInput.value = "";
        showKeyError("");

        document.getElementById("admin-step-key")?.classList.remove("hidden");
        document.getElementById("admin-step-list")?.classList.add("hidden");
        document.getElementById("admin-modal")?.classList.add("show");
    };

    const closeAdminModal = (ctx) => {
        ctx.setAdminKey?.("");
        document.getElementById("admin-modal")?.classList.remove("show");
    };

    const adminModerate = async (id, action, rowEl, ctx) => {
        const key = ctx.getAdminKey?.() || "";
        try {
            if (window.ApiClient?.communityAdminDelete && action === "reject") {
                // If your backend has a single delete endpoint, you can map reject->delete here.
            }

            if (window.ApiClient?.communityAdminDelete && action === "delete") {
                await window.ApiClient.communityAdminDelete(key, [id]);
            } else {
                // Preserve existing endpoints for approve/reject
                const endpoint =
                    action === "approve" ? "/api/admin/approve" : "/api/admin/reject";
                const res = await fetch(
                    `${ctx.apiUrl || ""}${endpoint}?admin_key=${encodeURIComponent(key)}`,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-Admin-Key": key,
                        },
                        body: JSON.stringify({ id }),
                    }
                );
                if (!res.ok) throw new Error(`Moderation failed (${res.status})`);
            }

            rowEl.remove();
        } catch (e) {
            const msg =
                e?.status === 403 ? "Invalid API key." : e?.message || String(e);
            toast("Admin", msg, "error");
        }
    };

    const renderAdminPendingList = async (submissions, ctx) => {
        const ul = document.getElementById("admin-pending-list");
        if (!ul) return;

        const Utils = window.Utils;
        const Browse = window.CommunityBrowse;

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
                        const actions = document.createElement("div");
                        actions.className = "actions";

                        const mkBtn = (cls, label, action) => {
                            const b = document.createElement("button");
                            b.type = "button";
                            b.className = cls;
                            b.textContent = label;
                            b.addEventListener("click", () =>
                                adminModerate(s.id, action, row, ctx)
                            );
                            return b;
                        };

                        actions.appendChild(mkBtn("approve-btn", "Approve", "approve"));
                        actions.appendChild(mkBtn("reject-btn", "Reject", "reject"));
                        row.appendChild(actions);
                    },
                }),
            ctx.patternRenderer,
            ctx.viewerControls
        );
    };

    const submitAdminKey = async (ctx) => {
        const key = (document.getElementById("admin-key-input")?.value || "").trim();
        if (!key) return showKeyError("Please enter the API key.");

        try {
            let d = null;
            if (window.ApiClient?.communityAdminList) {
                d = await window.ApiClient.communityAdminList(key);
            } else {
                const res = await fetch(
                    `${ctx.apiUrl || ""}/api/admin/submissions?admin_key=${encodeURIComponent(key)}`,
                    {
                        headers: { "X-Admin-Key": key },
                    }
                );
                d = await res.json();
                if (!res.ok)
                    throw Object.assign(new Error("Load submissions failed"), {
                        status: res.status,
                        data: d,
                    });
            }

            ctx.setAdminKey?.(key);
            showKeyError("");

            document.getElementById("admin-step-key")?.classList.add("hidden");
            document.getElementById("admin-step-list")?.classList.remove("hidden");

            await renderAdminPendingList(d?.submissions || [], ctx);
        } catch (e) {
            showKeyError(
                e?.status === 403
                    ? "Invalid API key."
                    : window.Utils?.formatApiError
                      ? window.Utils.formatApiError(e, "Request failed")
                      : String(e)
            );
        }
    };

    window.CommunityAdmin = {
        openAdminModal,
        closeAdminModal,
        submitAdminKey,
        renderAdminPendingList,
    };
})();
