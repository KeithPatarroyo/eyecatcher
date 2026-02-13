/**
 * Export modal and download logic for genealogy. Extracted from genealogy_viewer.js.
 * Exposes: GenealogyExport.bindExportModalEvents(showToast, apiUrl).
 */
(function () {
    "use strict";

    function bindExportModalEvents(showToast, apiUrl) {
        apiUrl = apiUrl || window.API_URL || "";
        const Utils = window.Utils;
        const ApiClient = window.ApiClient;
        if (!Utils || !Utils.onId || !ApiClient) return;

        Utils.onId("download-genealogy-btn", (el) => {
            el.onclick = async () => {
                const modal = document.getElementById("export-genealogy-modal");
                try {
                    const sizes = await ApiClient.apiFetch(
                        `${apiUrl}/genealogy/export-sizes`,
                        {},
                        "Could not load sizes"
                    );
                    document.getElementById("export-full-size").textContent =
                        sizes.full.populations +
                        " populations, " +
                        sizes.full.individuals +
                        " individuals (~" +
                        (window.formatBytes
                            ? window.formatBytes(sizes.full.estimated_bytes)
                            : sizes.full.estimated_bytes + " B") +
                        ")";

                    const branchList = document.getElementById("export-branch-list");
                    const branchesGroup = document.getElementById(
                        "export-branches-group"
                    );
                    branchList.innerHTML = "";
                    const branches = sizes.branches || [];
                    if (branchesGroup) branchesGroup.hidden = branches.length === 0;
                    const tpl = document.getElementById("export-branch-option-tpl");
                    branches.forEach((b) => {
                        if (!tpl || !tpl.content) return;
                        const label = tpl.content
                            .cloneNode(true)
                            .querySelector("label");
                        if (!label) return;
                        const radio = label.querySelector('input[type="radio"]');
                        const titleSpan = label.querySelector(".export-option-title");
                        const sizeSpan = label.querySelector(".export-size");
                        const branchName = b.name || "main";
                        const safeId =
                            "export-branch-" + branchName.replace(/\W/g, "_");
                        radio.id = safeId;
                        radio.value = branchName;
                        if (titleSpan) titleSpan.textContent = branchName;
                        if (sizeSpan)
                            sizeSpan.textContent =
                                b.populations +
                                " pop., " +
                                b.individuals +
                                " ind. (~" +
                                (window.formatBytes
                                    ? window.formatBytes(b.estimated_bytes)
                                    : b.estimated_bytes + " B") +
                                ")";
                        branchList.appendChild(label);
                    });
                    if (modal) modal.hidden = false;
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

        Utils.onId("export-modal-cancel", (el) => {
            el.onclick = () => {
                const modal = document.getElementById("export-genealogy-modal");
                if (modal) modal.hidden = true;
            };
        });
        const backdrop = document.querySelector(".export-modal-backdrop");
        if (backdrop) {
            backdrop.onclick = () => {
                const m = document.getElementById("export-genealogy-modal");
                if (m) m.hidden = true;
            };
        }
        document.addEventListener("keydown", (e) => {
            const modal = document.getElementById("export-genealogy-modal");
            if (e.key === "Escape" && modal && !modal.hidden) modal.hidden = true;
        });
        Utils.onId("export-modal-download", (el) => {
            el.onclick = async () => {
                const scope = document.querySelector(
                    'input[name="export-scope"]:checked'
                );
                const branchName = scope && scope.value !== "full" ? scope.value : null;
                const modal = document.getElementById("export-genealogy-modal");
                if (modal) modal.hidden = true;
                try {
                    const url = branchName
                        ? `${apiUrl}/genealogy/export?branch_name=${encodeURIComponent(branchName)}`
                        : `${apiUrl}/genealogy/export`;
                    const data = await ApiClient.apiFetch(url, {}, "Download failed");
                    const blob = new Blob([JSON.stringify(data, null, 2)], {
                        type: "application/json",
                    });
                    const urlObj = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = urlObj;
                    a.download = branchName
                        ? `genealogy-${branchName}-${new Date().toISOString().slice(0, 10)}.json`
                        : `genealogy-export-${new Date().toISOString().slice(0, 10)}.json`;
                    a.click();
                    URL.revokeObjectURL(urlObj);
                    showToast(
                        "Downloaded",
                        (branchName ? 'Branch "' + branchName + '"' : "Full tree") +
                            " exported as JSON.",
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
    }

    window.GenealogyExport = {
        bindExportModalEvents: bindExportModalEvents,
    };
})();
