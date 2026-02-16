/**
 * GenealogyExport: export modal + download.
 * Exposes: GenealogyExport.bindExportModalEvents(showToast, apiUrl)
 */
(() => {
    "use strict";

    const fmtBytes = (n) => (window.formatBytes ? window.formatBytes(n) : `${n} B`);

    const fetchJson = async (url, fallback) => {
        const res = await fetch(url);
        const data = await res.json().catch(() => null);
        if (!res.ok) {
            const err = new Error(
                data?.error ||
                    data?.message ||
                    fallback ||
                    `Request failed (${res.status})`
            );
            err.status = res.status;
            err.data = data;
            throw err;
        }
        return data;
    };

    const downloadJson = (obj, filename) => {
        const blob = new Blob([JSON.stringify(obj, null, 2)], {
            type: "application/json",
        });
        window.Toast?.triggerDownload?.(blob, filename);
    };

    const bindExportModalEvents = (showToast, apiUrl = window.API_URL || "") => {
        const Utils = window.Utils;
        if (!Utils?.onId) return;

        const modal = () => document.getElementById("export-genealogy-modal");
        const hide = () => {
            const m = modal();
            if (m) m.hidden = true;
        };
        const show = () => {
            const m = modal();
            if (m) m.hidden = false;
        };

        Utils.onId("download-genealogy-btn", (btn) => {
            btn.onclick = async () => {
                try {
                    const sizes = await fetchJson(
                        `${apiUrl}/api/genealogy/export-sizes`,
                        "Could not load sizes"
                    );

                    document.getElementById("export-full-size").textContent =
                        `${sizes.full.populations} populations, ${sizes.full.individuals} individuals (~${fmtBytes(sizes.full.estimated_bytes)})`;

                    const branches = sizes.branches || [];
                    const branchList = document.getElementById("export-branch-list");
                    const branchesGroup = document.getElementById(
                        "export-branches-group"
                    );
                    if (branchList) branchList.innerHTML = "";
                    if (branchesGroup) branchesGroup.hidden = branches.length === 0;

                    const tpl = document.getElementById("export-branch-option-tpl");
                    branches.forEach((b) => {
                        if (!tpl?.content || !branchList) return;
                        const label = tpl.content
                            .cloneNode(true)
                            .querySelector("label");
                        if (!label) return;

                        const radio = label.querySelector('input[type="radio"]');
                        const titleSpan = label.querySelector(".export-option-title");
                        const sizeSpan = label.querySelector(".export-size");

                        const branchName = b.name || "main";
                        radio.id = `export-branch-${branchName.replace(/\W/g, "_")}`;
                        radio.value = branchName;
                        if (titleSpan) titleSpan.textContent = branchName;
                        if (sizeSpan)
                            sizeSpan.textContent = `${b.populations} pop., ${b.individuals} ind. (~${fmtBytes(b.estimated_bytes)})`;

                        branchList.appendChild(label);
                    });

                    show();
                } catch (e) {
                    showToast(
                        "Could not load sizes",
                        Utils.formatApiError
                            ? Utils.formatApiError(e, "Network error")
                            : String(e),
                        "error"
                    );
                }
            };
        });

        Utils.onId("export-modal-cancel", (btn) => {
            btn.onclick = hide;
        });
        document
            .querySelector(".export-modal-backdrop")
            ?.addEventListener("click", hide);
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && modal() && !modal().hidden) hide();
        });

        Utils.onId("export-modal-download", (btn) => {
            btn.onclick = async () => {
                hide();
                const scope = document.querySelector(
                    'input[name="export-scope"]:checked'
                );
                const branchName = scope && scope.value !== "full" ? scope.value : null;

                try {
                    const url = branchName
                        ? `${apiUrl}/api/genealogy/export?branch_name=${encodeURIComponent(branchName)}`
                        : `${apiUrl}/api/genealogy/export`;

                    const data = await fetchJson(url, "Download failed");
                    const date = new Date().toISOString().slice(0, 10);
                    const filename = branchName
                        ? `genealogy-${branchName}-${date}.json`
                        : `genealogy-export-${date}.json`;

                    downloadJson(data, filename);
                    showToast(
                        "Downloaded",
                        `${branchName ? `Branch "${branchName}"` : "Full tree"} exported as JSON.`,
                        "success"
                    );
                } catch (e) {
                    showToast(
                        "Download failed",
                        Utils.formatApiError
                            ? Utils.formatApiError(e, "Network error")
                            : String(e),
                        "error"
                    );
                }
            };
        });
    };

    window.GenealogyExport = { bindExportModalEvents };
})();
