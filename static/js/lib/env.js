/**
 * Server-injected or global env; single place that reads from window.
 * API_URL and API_BASE_PATH are set by the server/template before app loads.
 * getVis / getGenealogyBridge are externals (vis.js script, optional bridge from main app).
 */
export const API_URL = typeof window !== "undefined" ? window.API_URL || "" : "";
export const API_BASE_PATH =
    typeof window !== "undefined" && window.API_BASE_PATH != null
        ? window.API_BASE_PATH
        : "/";

export const getVis = () => (typeof window !== "undefined" ? window.vis : null);
export const getGenealogyBridge = () =>
    typeof window !== "undefined" ? window.GenealogyBridge : null;
