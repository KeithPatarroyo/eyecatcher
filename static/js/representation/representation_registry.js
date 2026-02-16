/**
 * Representation registry. Bootstraps from config; stores plain representation records
 * { id, isGenomeFormat, hasSignalControls, capabilities, phenotype, substrate }.
 * Use RepresentationHelpers for display/meta; call rep.substrate directly for render.
 */
(function () {
    "use strict";

    var DEFAULT_REPRESENTATION_ID = "dual_cppn";

    function buildIsGenomeFormatFromConfig(entry) {
        var genomeKeys = entry.genomeKeys || [];
        var excludeKeys = entry.excludeKeys || [];
        return function (obj) {
            if (!obj) return false;
            for (var i = 0; i < genomeKeys.length; i++) {
                var k = genomeKeys[i];
                if (k === "rule") {
                    if (typeof obj.rule !== "number") return false;
                } else if (!obj[k]) return false;
            }
            for (var j = 0; j < excludeKeys.length; j++) {
                if (obj[excludeKeys[j]]) return false;
            }
            return true;
        };
    }

    var defaultCapabilities = {
        save: true,
        network: true,
        timeOutput: false,
        adjustWeight: false,
    };

    function mergeCapabilities(entry) {
        var caps = entry && entry.capabilities;
        if (!caps) return defaultCapabilities;
        return {
            save: caps.save !== false,
            network: caps.network !== false,
            timeOutput: caps.timeOutput === true,
            adjustWeight: caps.adjustWeight !== false,
        };
    }

    function interpolateMetaTemplate(template, data) {
        if (!template) return "";
        return template.replace(/\{(\w+)\}/g, function (_, key) {
            return data[key] !== undefined ? String(data[key]) : "";
        });
    }

    // --- Standalone helpers (use rep.phenotype, rep.substrate, rep.capabilities) ---
    function getMetaLabel(phenotype, pattern) {
        var template = (phenotype && phenotype.metaTemplate) || "";
        var data = pattern || {};
        return interpolateMetaTemplate(template, {
            nodes: data.nodes,
            connections: data.connections,
            fingerprint: data.fingerprint,
            density: data.density,
            live_count: data.live_count,
        });
    }

    function prepareRuntime(runtime, pattern) {
        if (pattern && runtime) {
            runtime.patternPayload = runtime.patternPayload || {};
            runtime.patternPayload.grid = pattern.grid;
            runtime.patternId = pattern.id;
        }
    }

    function supportsCellInteraction(substrate, phenotype) {
        return (
            typeof substrate.handleInteraction === "function" &&
            phenotype &&
            phenotype.interactions &&
            phenotype.interactions.indexOf("toggle") >= 0
        );
    }

    function hasCapability(capabilities, name) {
        return capabilities && capabilities[name] !== false;
    }

    function getMetaIdPrefix() {
        return "ID: ";
    }

    function createDisplayElement(rep, pattern, options) {
        var substrate = rep.substrate;
        var phenotype = rep.phenotype || {};
        var result = substrate.createDisplayElement(phenotype, pattern, options);
        if (result && result.state) {
            result.state.patternPayload = result.state.patternPayload || {};
            result.state.patternPayload.grid = pattern && pattern.grid;
            result.state.patternId = pattern && pattern.id;
            if (typeof substrate.setup === "function") {
                substrate.setup(result.state, phenotype);
            }
        }
        return {
            element: result ? result.element : null,
            runtime: result ? result.state : null,
        };
    }

    window.RepresentationHelpers = {
        getMetaLabel: getMetaLabel,
        prepareRuntime: prepareRuntime,
        supportsCellInteraction: supportsCellInteraction,
        hasCapability: hasCapability,
        getMetaIdPrefix: getMetaIdPrefix,
        createDisplayElement: createDisplayElement,
    };

    function createRepresentation(entry, substrate, phenotype) {
        var isGenomeFormat = buildIsGenomeFormatFromConfig(entry);
        var capabilities = mergeCapabilities(entry);
        return {
            id: entry.id,
            isGenomeFormat: isGenomeFormat,
            hasSignalControls: entry.hasSignalControls !== false,
            capabilities: capabilities,
            phenotype: phenotype || {},
            substrate: substrate,
        };
    }

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
            var config =
                window.EyecatcherConfig && window.EyecatcherConfig.representations;
            var reg = window.SubstrateRegistry;
            if (!config || !Array.isArray(config)) return;
            if (reg && reg.initDefaults) reg.initDefaults();

            var self = this;
            config.forEach(function (entry) {
                var phenotype = entry.phenotype || { substrate: "image" };
                var substrateKey =
                    typeof phenotype.substrate === "string"
                        ? phenotype.substrate
                        : (phenotype.substrate && phenotype.substrate.type) || "image";
                var substrate = (reg && reg.getSubstrate(substrateKey)) || null;
                if (!substrate) return;
                var representation = createRepresentation(entry, substrate, phenotype);
                self._representationsById[entry.id] = representation;
            });
        }

        get(representationId) {
            if (!representationId) return null;
            return this._representationsById[representationId] || null;
        }

        findByGenome(genome) {
            var config =
                window.EyecatcherConfig && window.EyecatcherConfig.representations;
            var order =
                config && Array.isArray(config)
                    ? config.map(function (e) {
                          return e.id;
                      })
                    : [DEFAULT_REPRESENTATION_ID, "single_cppn", "ca"];
            for (var i = 0; i < order.length; i++) {
                var rep = this._representationsById[order[i]];
                if (rep && rep.isGenomeFormat && rep.isGenomeFormat(genome)) {
                    return rep;
                }
            }
            return null;
        }

        getDefault() {
            var def = window.__eyecatcherDefaultResolution;
            var evo = window.EvolutionConfig;
            var representationId =
                (evo && evo.DEFAULT_REPRESENTATION_ID) ||
                (def && def.representationId) ||
                DEFAULT_REPRESENTATION_ID;
            return {
                representationId: representationId,
                representation: this.get(representationId),
            };
        }

        getDefaultResolution() {
            return window.EvolutionConfig && window.EvolutionConfig.getDefaultResolution
                ? window.EvolutionConfig.getDefaultResolution()
                : { representationId: this.getDefault().representationId };
        }

        getDefaultRepresentationId() {
            return this.getDefault().representationId;
        }

        resolve(opts) {
            opts = opts || {};
            var representation = null;
            if (opts.representationId) {
                representation = this.get(opts.representationId);
            }
            if (!representation && opts.genomes && opts.genomes.length) {
                representation = this.findByGenome(opts.genomes[0]);
            }
            if (!representation) {
                representation = this.getDefault().representation;
            }
            return {
                representationId:
                    (representation && representation.id) ||
                    this.getDefault().representationId,
                representation: representation,
            };
        }

        currentRepresentation() {
            var state =
                window.PopulationState &&
                window.PopulationState.getState &&
                window.PopulationState.getState();
            var repId = state && state.representationId;
            return this.resolve({ representationId: repId }).representation;
        }
    }

    var registry = new RepresentationRegistry();
    window.RepresentationRegistry = registry;
})();
