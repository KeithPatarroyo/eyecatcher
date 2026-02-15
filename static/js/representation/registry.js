/**
 * Representation registry. Bootstraps from Phenotype + Substrate registry.
 * Each representation has a phenotype (from config) and a substrate (ShaderSubstrate, GridSubstrate, ImageSubstrate).
 * Representations are facades that delegate to substrate + phenotype for display and render.
 */
(function () {
    "use strict";

    var DEFAULT_REPRESENTATION_ID = "dual_cppn";
    var DEFAULT_RESOLUTION = {
        representationId: DEFAULT_REPRESENTATION_ID,
    };

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

    function createRepresentation(entry, substrate, phenotype) {
        var isGenomeFormat = buildIsGenomeFormatFromConfig(entry);
        var capabilities = mergeCapabilities(entry);
        var substrateName = (phenotype && phenotype.substrate) || "image";

        return {
            id: entry.id,
            isGenomeFormat: isGenomeFormat,
            hasSignalControls: entry.hasSignalControls !== false,
            capabilities: capabilities,
            phenotype: phenotype || {},
            substrate: substrate,

            getDisplayData: function (genomes, options) {
                if (substrateName === "shader") {
                    return window.RepresentationRegistry.fetchViaDevelop(
                        genomes,
                        options
                    );
                }
                return window.RepresentationRegistry.fetchViaExpress(genomes, options);
            },

            createDisplayElement: function (pattern, options) {
                var result = substrate.createDisplayElement(phenotype, pattern);
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
            },

            prepareRuntime: function (runtime, pattern) {
                if (pattern && runtime) {
                    runtime.patternPayload = runtime.patternPayload || {};
                    runtime.patternPayload.grid = pattern.grid;
                    runtime.patternId = pattern.id;
                }
            },

            buildParams: function (signalValues, context) {
                return substrate.buildParams
                    ? substrate.buildParams(phenotype, signalValues)
                    : {};
            },

            render: function (runtime, uniformValues, signalState) {
                var params = uniformValues || {};
                substrate.render(runtime, params, signalState || {});
            },

            getMetaLabel: function (pattern) {
                var template = (phenotype && phenotype.metaTemplate) || "";
                var data = pattern || {};
                return interpolateMetaTemplate(template, {
                    nodes: data.nodes,
                    connections: data.connections,
                    fingerprint: data.fingerprint,
                    density: data.density,
                    live_count: data.live_count,
                });
            },

            getMetaIdPrefix: function () {
                return "ID: ";
            },

            hasCapability: function (name) {
                return capabilities[name] !== false;
            },

            supportsCellInteraction: function () {
                return (
                    typeof substrate.handleInteraction === "function" &&
                    phenotype.interactions &&
                    phenotype.interactions.indexOf("toggle") >= 0
                );
            },

            onCellInteraction: function (runtime, x, y, interactionType) {
                if (substrate.handleInteraction) {
                    substrate.handleInteraction(runtime, x, y, interactionType);
                }
            },
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
            var config = window.RepresentationConfig;
            var reg = window.SubstrateRegistry;
            if (!config || !Array.isArray(config)) return;
            if (reg && reg.initDefaults) reg.initDefaults();

            var self = this;
            config.forEach(function (entry) {
                var phenotype = entry.phenotype || { substrate: "image" };
                var substrate = (reg && reg.getSubstrate(phenotype.substrate)) || null;
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
            var config = window.RepresentationConfig;
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

        async fetchViaDevelop(genomes, options) {
            var ApiClient = window.ApiClient;
            if (!ApiClient) throw new Error("ApiClient not available");
            var compData = await ApiClient.develop(
                genomes,
                options && options.colorMode
            );
            return { population: compData.shaders || [] };
        }

        async fetchViaExpress(genomes, _options) {
            var ApiClient = window.ApiClient;
            if (!ApiClient) throw new Error("ApiClient not available");
            var evalData = await ApiClient.express(genomes);
            var results = evalData.results || [];
            if (typeof performance !== "undefined") {
                window.CA_ANIMATION_START_TIME = performance.now();
            }
            return {
                population: results.map(function (r) {
                    return {
                        id: r.id,
                        image: r.image,
                        shader: r.shader,
                        grid: r.grid,
                        nodes: r.nodes !== undefined ? r.nodes : 0,
                        connections: r.connections !== undefined ? r.connections : 0,
                        fitness: r.fitness !== undefined ? r.fitness : 0,
                    };
                }),
            };
        }

        async getDisplayData(representation, genomes, options) {
            return representation.getDisplayData(genomes, options);
        }

        /**
         * Get signal values from the active source (or defaults), build params via current adapter, and render one frame.
         * Use from animation loop, genealogy thumbnails, and community previews.
         * @param {Object} runtime - From WebGLUtils.setupPattern (gl, program, positionBuffer, canvas)
         * @param {Object} signalState - Flat { signal_id: boolean } for CPPN toggles
         * @param {HTMLCanvasElement} [contextCanvas]
         * @param {Object} [context] - Optional { canvas, gridPosition, neighbors, patternId }
         */
        renderFrameWithSignals(runtime, signalState, contextCanvas, context) {
            var getSource = window.getSignalSource;
            var signalContext = context
                ? { canvas: contextCanvas || (context && context.canvas), ...context }
                : contextCanvas != null
                  ? { canvas: contextCanvas }
                  : {};
            var signalValues =
                getSource &&
                getSource().getValues &&
                getSource().getValues(signalContext);
            if (!signalValues || !Object.keys(signalValues).length) {
                var ids =
                    (window.EvolutionConfig && window.EvolutionConfig.SIGNAL_IDS) || [];
                signalValues = {};
                ids.forEach(function (id) {
                    signalValues[id] = id === "raw_time" ? 0.5 : 0;
                });
                if (!Object.keys(signalValues).length) signalValues = { raw_time: 0.5 };
            }
            var representation = this.currentRepresentation();
            var params =
                representation && representation.buildParams
                    ? representation.buildParams(signalValues, context)
                    : {};
            if (representation)
                representation.render(runtime, params, signalState || {});
        }
    }

    var registry = new RepresentationRegistry();
    window.RepresentationRegistry = registry;
    window.RepresentationAdapters = registry; // backward-compat alias
    registry.getAdapter = registry.get.bind(registry);
    registry.findAdapterByGenome = registry.findByGenome.bind(registry);
})();
