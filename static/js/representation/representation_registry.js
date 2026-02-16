/**
 * Representation registry. Bootstraps from EyecatcherConfig; stores plain representation records:
 * { id, isGenomeFormat, hasSignalControls, capabilities, phenotype, substrate }.
 *
 * Use RepresentationHelpers for display/meta; call rep.substrate directly for render.
 */
import SubstrateRegistry from "./substrate_registry.js";
import { getConfig } from "../evolution/experiment_config.js";
import populationState from "../population/population_state.js";

const DEFAULT_REPRESENTATION_ID = "nca";

const defaultCapabilities = Object.freeze({
    save: true,
    network: true,
    timeOutput: false,
    adjustWeight: false,
});

const getConfigRepresentations = () => window.EyecatcherConfig?.representations ?? [];

const mergeCapabilities = (entry) => {
    const caps = entry?.capabilities;
    if (!caps) return { ...defaultCapabilities };
    return {
        save: caps.save !== false,
        network: caps.network !== false,
        timeOutput: caps.timeOutput === true,
        adjustWeight: caps.adjustWeight !== false,
    };
};

const buildIsGenomeFormatFromConfig = (entry) => {
    const genomeKeys = entry?.genomeKeys ?? [];
    const excludeKeys = entry?.excludeKeys ?? [];

    return (obj) => {
        if (!obj) return false;

        for (const k of genomeKeys) {
            if (k === "rule") {
                if (typeof obj.rule !== "number") return false;
            } else if (!obj[k]) {
                return false;
            }
        }

        for (const k of excludeKeys) {
            if (obj[k]) return false;
        }

        return true;
    };
};

const interpolateMetaTemplate = (template, data) =>
    (template || "").replace(/\{(\w+)\}/g, (_, key) =>
        data[key] !== undefined ? String(data[key]) : ""
    );

// ---- RepresentationHelpers (kept as window global to minimise churn elsewhere) ----
const getMetaLabel = (phenotype, pattern) => {
    const template = phenotype?.metaTemplate || "";
    const data = pattern || {};
    return interpolateMetaTemplate(template, {
        nodes: data.nodes,
        connections: data.connections,
        fingerprint: data.fingerprint,
        density: data.density,
        live_count: data.live_count,
    });
};

const prepareRuntime = (runtime, pattern) => {
    if (!pattern || !runtime) return;
    runtime.patternPayload = runtime.patternPayload || {};
    runtime.patternPayload.grid = pattern.grid;
    runtime.patternId = pattern.id;
};

const supportsCellInteraction = (substrate, phenotype) => {
    if (!phenotype || typeof substrate?.handleInteraction !== "function") return false;
    const interactions = phenotype.interactions || phenotype.behaviour?.interactions;
    return Array.isArray(interactions) && interactions.includes("toggle");
};

const hasCapability = (capabilities, name) =>
    capabilities ? capabilities[name] !== false : false;

const getMetaIdPrefix = () => "ID: ";

const createDisplayElement = (rep, pattern, options) => {
    const substrate = rep?.substrate ?? SubstrateRegistry.getSubstrate();
    const phenotype = rep?.phenotype || {};
    if (!substrate?.createDisplayElement) {
        const fallback = document.createElement("div");
        fallback.className = "organism-canvas-fallback";
        fallback.textContent = "No display";
        return { element: fallback, runtime: null };
    }
    const result = substrate.createDisplayElement(phenotype, pattern, options);

    // If a substrate returns runtime state, give it a chance to finalise setup.
    if (result?.state) {
        result.state.patternPayload = result.state.patternPayload || {};
        result.state.patternPayload.grid = pattern?.grid;
        result.state.patternId = pattern?.id;

        if (typeof substrate.setup === "function")
            substrate.setup(result.state, phenotype);
    }

    return {
        element: result?.element ?? null,
        runtime: result?.state ?? null,
    };
};

const RepresentationHelpers = {
    getMetaLabel,
    prepareRuntime,
    supportsCellInteraction,
    hasCapability,
    getMetaIdPrefix,
    createDisplayElement,
};

export { RepresentationHelpers };
window.RepresentationHelpers = RepresentationHelpers;

const createRepresentation = (entry, substrate, phenotype) => ({
    id: entry.id,
    isGenomeFormat: buildIsGenomeFormatFromConfig(entry),
    hasSignalControls: entry.hasSignalControls !== false,
    capabilities: mergeCapabilities(entry),
    phenotype: phenotype || {},
    substrate,
});

class RepresentationRegistry {
    constructor() {
        this._representationsById = {};
        window.__eyecatcherDefaultResolution = {
            representationId: DEFAULT_REPRESENTATION_ID,
            representation: null,
        };
        this._bootstrapFromConfig();
    }

    _bootstrapFromConfig() {
        // Ensure substrates exist before we bind phenotypes to them.
        SubstrateRegistry?.initDefaults?.();

        const config = getConfigRepresentations();
        if (!Array.isArray(config) || config.length === 0) return;

        for (const entry of config) {
            if (!entry?.id) continue;
            const phenotype = entry.phenotype || {};
            const substrateType = phenotype?.substrate?.type || phenotype?.substrate;
            const substrate = SubstrateRegistry.getSubstrate(substrateType);

            // If substrate is missing, we still register, but the UI will fall back to ImageSubstrate.
            this._representationsById[entry.id] = createRepresentation(
                entry,
                substrate,
                phenotype
            );

            if (entry.id === DEFAULT_REPRESENTATION_ID) {
                window.__eyecatcherDefaultResolution = {
                    representationId: entry.id,
                    representation: this._representationsById[entry.id],
                };
            }
        }
    }

    get(representationId) {
        if (!representationId) return null;
        return this._representationsById[representationId] || null;
    }

    findByGenome(genome) {
        const config = getConfigRepresentations();
        const order =
            Array.isArray(config) && config.length
                ? config.map((e) => e.id)
                : [DEFAULT_REPRESENTATION_ID, "single_cppn", "ca"];

        for (const id of order) {
            const rep = this._representationsById[id];
            if (rep?.isGenomeFormat?.(genome)) return rep;
        }
        return null;
    }

    getDefault() {
        const def = window.__eyecatcherDefaultResolution;
        const evo = getConfig();
        const representationId =
            evo?.DEFAULT_REPRESENTATION_ID ||
            def?.representationId ||
            DEFAULT_REPRESENTATION_ID;

        return { representationId, representation: this.get(representationId) };
    }

    getDefaultResolution() {
        return getConfig()?.getDefaultResolution
            ? getConfig().getDefaultResolution()
            : { representationId: this.getDefault().representationId };
    }

    getDefaultRepresentationId() {
        return this.getDefault().representationId;
    }

    resolve(opts = {}) {
        let representation = null;

        if (opts.representationId) representation = this.get(opts.representationId);
        if (!representation && opts.genomes?.length)
            representation = this.findByGenome(opts.genomes[0]);
        if (!representation) representation = this.getDefault().representation;

        return {
            representationId: representation?.id || this.getDefault().representationId,
            representation,
        };
    }

    currentRepresentation() {
        const state = populationState?.getState?.();
        const repId = state?.representationId;
        return this.resolve({ representationId: repId }).representation;
    }
}

const representationRegistry = new RepresentationRegistry();
export default representationRegistry;
window.RepresentationRegistry = representationRegistry;
