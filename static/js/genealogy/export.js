/**
 * GenealogyExport: export modal + download.
 * Exposes: GenealogyExport.bindExportModalEvents(showToast, apiUrl)
 */
import Utils from "../lib/utils.js";
import api from "../lib/api_client.js";
import Toast from "../lib/toast.js";
import DOM from "../lib/dom.js";

const fmtBytes = (n) => (Utils.formatBytes ? Utils.formatBytes(n) : `${n} B`);

const apiGet = async (url, fallback) => {
    const result = await api.request(url);
    if (!result.ok) {
        throw new Error(result.error || fallback || "Request failed");
    }
    return result.data;
};

const downloadJson = (obj, filename) => {
    const blob = new Blob([JSON.stringify(obj, null, 2)], {
        type: "application/json",
    });
    Toast.triggerDownload(blob, filename);
};

const bindExportModalEvents = (showToast, apiUrl = window.API_URL || "") => {
    const modal = () => DOM.byId("export-genealogy-modal");
    const hide = () => DOM.setHidden(modal(), true);
    const show = () => DOM.setHidden(modal(), false);

    DOM.on(DOM.byId("download-genealogy-btn"), "click", async () => {
        try {
            const sizes = await apiGet(
                `${apiUrl}/api/genealogy/export-sizes`,
                "Could not load sizes"
            );

            DOM.setText(
                DOM.byId("export-full-size"),
                `${sizes.full.populations} populations, ${sizes.full.individuals} individuals (~${fmtBytes(sizes.full.estimated_bytes)})`
            );

            const branches = sizes.branches || [];
            const branchList = DOM.byId("export-branch-list");
            const branchesGroup = DOM.byId("export-branches-group");
            if (branchList) branchList.innerHTML = "";
            DOM.setHidden(branchesGroup, branches.length === 0);

            const tpl = DOM.byId("export-branch-option-tpl");
            branches.forEach((b) => {
                if (!tpl?.content || !branchList) return;
                const branchName = b.name || "main";
                const sizeText = `${b.populations} pop., ${b.individuals} ind. (~${fmtBytes(b.estimated_bytes)})`;
                const label = DOM.cloneAndFill(tpl, "label", {
                    ".export-option-title": branchName,
                    ".export-size": sizeText,
                });
                if (!label) return;
                const radio = DOM.qs('input[type="radio"]', label);
                if (radio) {
                    radio.id = `export-branch-${branchName.replace(/\W/g, "_")}`;
                    radio.value = branchName;
                }
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
    });

    DOM.on(DOM.byId("export-modal-cancel"), "click", hide);
    DOM.on(DOM.qs(".export-modal-backdrop"), "click", hide);
    DOM.on(document, "keydown", (e) => {
        if (e.key === "Escape" && modal() && !modal().hidden) hide();
    });

    DOM.on(DOM.byId("export-modal-download"), "click", async () => {
        hide();
        const scope = DOM.qs('input[name="export-scope"]:checked');
        const branchName = scope && scope.value !== "full" ? scope.value : null;

        try {
            const url = branchName
                ? `${apiUrl}/api/genealogy/export?branch_name=${encodeURIComponent(branchName)}`
                : `${apiUrl}/api/genealogy/export`;

            const data = await apiGet(url, "Download failed");
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
    });
};

const GenealogyExport = { bindExportModalEvents };
export default GenealogyExport;
export { GenealogyExport };
