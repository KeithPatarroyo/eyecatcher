/**
 * GenealogySync: tiny storage helpers + saveCurrentPopulationToGenealogy.
 * Exposes: GenealogySync.getGenealogyBranchCounter / setGenealogyBranchCounter /
 *          syncCurrentPopulationIdToStorage / getStoredPopulationId / saveCurrentPopulationToGenealogy
 */
import Utils from "../lib/utils.js";
import api from "../lib/api_client.js";

const BRANCH_COUNTER_KEY = "genealogy_branch_counter";
const POPULATION_ID_KEY = "current_population_id";

const safeLS = () => (typeof localStorage !== "undefined" ? localStorage : null);
const safeSS = () => (typeof sessionStorage !== "undefined" ? sessionStorage : null);

const getGenealogyBranchCounter = () =>
    parseInt(Utils.safeGetItem(safeLS(), BRANCH_COUNTER_KEY, "1"), 10) || 1;

const setGenealogyBranchCounter = (n) =>
    Utils.safeSetItem(safeLS(), BRANCH_COUNTER_KEY, String(n));

const syncCurrentPopulationIdToStorage = (populationId) => {
    const s = safeSS();
    if (!s) return;
    if (populationId != null)
        Utils.safeSetItem(s, POPULATION_ID_KEY, String(populationId));
    else {
        try {
            s.removeItem(POPULATION_ID_KEY);
        } catch {
            /* ignore */
        }
    }
};

const getStoredPopulationId = () => {
    const s = safeSS();
    if (!s) return null;
    const v = Utils.safeGetItem(s, POPULATION_ID_KEY, null);
    const n = v == null || v === "" ? NaN : parseInt(v, 10);
    return Number.isFinite(n) ? n : null;
};

const saveCurrentPopulationToGenealogy = async (
    apiUrl,
    genomes,
    generationNum,
    branchName,
    parentId,
    fitnessData,
    representationId
) => {
    const body = {
        individuals: genomes,
        parent_id: parentId,
        generation_num: generationNum,
        branch_name: branchName,
        description:
            generationNum === 0
                ? "Random initial population"
                : `Generation ${generationNum}`,
        user_id: "user",
        fitness_data: fitnessData || [],
        ...(representationId != null ? { representation_id: representationId } : {}),
    };

    const result = await api.request(`${apiUrl}/api/genealogy/save-population`, {
        method: "POST",
        body,
    });
    if (!result.ok) throw new Error(result.error || "Save failed");
    return result.data;
};

window.GenealogySync = {
    getGenealogyBranchCounter,
    setGenealogyBranchCounter,
    syncCurrentPopulationIdToStorage,
    getStoredPopulationId,
    saveCurrentPopulationToGenealogy,
};
