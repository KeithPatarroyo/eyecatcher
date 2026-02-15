/**
 * Thumbnail rendering for genealogy tree nodes. Extracted from genealogy_viewer.js.
 * Exposes: GenealogyThumbnails.renderThumbnail, GenealogyThumbnails.renderAllThumbnails.
 */
(function () {
    "use strict";

    const THUMBNAIL_CANVAS_SIZE = 128;
    const MAX_THUMBNAIL_CACHE = 200;
    const THUMBNAIL_BATCH_SIZE = 8;

    async function renderThumbnail(populationId, cache, apiUrl) {
        apiUrl = apiUrl || window.API_URL || "";
        if (cache && cache.has(populationId)) {
            return cache.get(populationId);
        }

        const RepresentationRegistry = window.RepresentationRegistry;
        const ApiClient = window.ApiClient;
        if (
            !RepresentationRegistry ||
            !RepresentationRegistry.getDisplayData ||
            !RepresentationRegistry.findAdapterByGenome ||
            !ApiClient
        ) {
            return null;
        }

        try {
            const data = await ApiClient.apiFetch(
                `${apiUrl}/genealogy/population-thumbnail/${populationId}`,
                {},
                "No thumbnail"
            );
            const genome = data.individual != null ? data.individual : data.genome;
            if (!genome) return null;

            const adapter = RepresentationRegistry.findAdapterByGenome(genome);
            if (!adapter) return null;

            const result = await RepresentationRegistry.getDisplayData(
                adapter,
                [genome],
                {}
            );
            const pop = result && result.population && result.population[0];
            if (!pop) return null;

            const canvas = document.createElement("canvas");
            canvas.width = THUMBNAIL_CANVAS_SIZE;
            canvas.height = THUMBNAIL_CANVAS_SIZE;

            if (pop.image) {
                const img = new Image();
                await new Promise((resolve, reject) => {
                    img.onload = resolve;
                    img.onerror = reject;
                    img.src = pop.image;
                });
                const ctx = canvas.getContext("2d");
                if (ctx) {
                    ctx.drawImage(
                        img,
                        0,
                        0,
                        THUMBNAIL_CANVAS_SIZE,
                        THUMBNAIL_CANVAS_SIZE
                    );
                }
            } else if (pop.shader && window.WebGLUtils) {
                const runtime = window.WebGLUtils.setupPattern(canvas, pop.shader);
                if (!runtime || runtime.error) return null;
                if (genome && typeof genome.rule === "number") {
                    runtime.caRule = genome.rule;
                }
                const signalState =
                    window.EvolutionConfig &&
                    window.EvolutionConfig.getDefaultSignalState
                        ? window.EvolutionConfig.getDefaultSignalState()
                        : { time: {}, visual: {} };
                if (window.RepresentationRegistry) {
                    window.RepresentationRegistry.renderFrameWithSignals(
                        runtime,
                        signalState,
                        canvas
                    );
                }
            } else {
                return null;
            }

            const dataUrl = canvas.toDataURL("image/png");
            if (cache) {
                if (cache.size >= MAX_THUMBNAIL_CACHE) {
                    const firstKey = cache.keys().next().value;
                    if (firstKey !== undefined) cache.delete(firstKey);
                }
                cache.set(populationId, dataUrl);
            }
            return dataUrl;
        } catch (error) {
            console.warn(
                "Thumbnail failed for population " + populationId + ":",
                error
            );
            return null;
        }
    }

    async function renderAllThumbnails(visNodes, cache, options) {
        options = options || {};
        const defaultNodeSize = options.defaultNodeSize || 90;
        const nodeSize = parseInt(
            document.getElementById("node-size")?.value || defaultNodeSize,
            10
        );
        const nodes = visNodes.get();

        for (let i = 0; i < nodes.length; i += THUMBNAIL_BATCH_SIZE) {
            const batch = nodes.slice(i, i + THUMBNAIL_BATCH_SIZE);
            const apiUrl = options.apiUrl || window.API_URL || "";
            const results = await Promise.all(
                batch.map(async (node) => ({
                    id: node.id,
                    color: node.color,
                    thumbnail: await renderThumbnail(node.id, cache, apiUrl),
                }))
            );
            results.forEach((r) => {
                if (r.thumbnail) {
                    visNodes.update({
                        id: r.id,
                        shape: "circularImage",
                        image: r.thumbnail,
                        size: nodeSize / 2,
                        borderWidth: 3,
                        mass: 2,
                        color: {
                            border: r.color.border,
                            background: "transparent",
                        },
                        shapeProperties: {
                            useBorderWithImage: true,
                        },
                    });
                }
            });
        }
    }

    window.GenealogyThumbnails = {
        renderThumbnail: renderThumbnail,
        renderAllThumbnails: renderAllThumbnails,
    };
})();
