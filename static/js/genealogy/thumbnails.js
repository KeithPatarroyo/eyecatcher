/**
 * GenealogyThumbnails: renders thumbnails for vis.js nodes.
 * Exposes: GenealogyThumbnails.renderThumbnail / renderAllThumbnails
 */
import api from "../lib/api_client.js";
import DisplayFetcher from "../representation/display_fetcher.js";
import RepresentationRegistry from "../representation/representation_registry.js";

const THUMBNAIL_CANVAS_SIZE = 128;
const MAX_CACHE = 200;
const BATCH = 8;

const cachePut = (cache, key, value) => {
    if (!cache) return;
    if (cache.size >= MAX_CACHE) cache.delete(cache.keys().next().value);
    cache.set(key, value);
};

const loadImg = (src) =>
    new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = src;
    });

const renderThumbnail = async (populationId, cache, apiUrl = window.API_URL || "") => {
    if (cache?.has(populationId)) return cache.get(populationId);

    if (
        !RepresentationRegistry?.findByGenome ||
        typeof DisplayFetcher?.fetchDisplayData !== "function"
    )
        return null;

    try {
        const result = api
            ? await api.request(
                  `${apiUrl}/api/genealogy/population-thumbnail/${populationId}`
              )
            : { ok: false };
        if (!result?.ok) return null;
        const data = result.data;

        const genome = data.individual ?? data.genome;
        if (!genome) return null;

        const rep = RepresentationRegistry.findByGenome(genome);
        if (!rep) return null;

        const pop = (await DisplayFetcher.fetchDisplayData(rep, [genome], {}))
            ?.population?.[0];
        if (!pop) return null;

        const canvas = document.createElement("canvas");
        canvas.width = THUMBNAIL_CANVAS_SIZE;
        canvas.height = THUMBNAIL_CANVAS_SIZE;

        if (pop.image) {
            const img = await loadImg(pop.image);
            canvas
                .getContext("2d")
                ?.drawImage(img, 0, 0, THUMBNAIL_CANVAS_SIZE, THUMBNAIL_CANVAS_SIZE);
        } else if (pop.rule && window.WebGLUtils?.setupPattern) {
            const runtime = window.WebGLUtils.setupPattern(canvas, pop.rule);
            if (!runtime || runtime.error) return null;

            const repId = window.EvolutionConfig?.getCurrentRepresentationId?.() ?? "";
            const signalState =
                window.EvolutionConfig?.getDefaultSignalState?.(repId) ?? {};
            window.AnimationLoop?.renderFrameWithSignals?.(
                runtime,
                signalState,
                canvas
            );
        } else {
            return null;
        }

        const url = canvas.toDataURL("image/png");
        cachePut(cache, populationId, url);
        return url;
    } catch {
        return null;
    }
};

const renderAllThumbnails = async (visNodes, cache, options = {}) => {
    const defaultNodeSize = options.defaultNodeSize || 90;
    const nodeSize = parseInt(
        document.getElementById("node-size")?.value || defaultNodeSize,
        10
    );
    const apiUrl = options.apiUrl || window.API_URL || "";

    const nodes = visNodes.get();
    for (let i = 0; i < nodes.length; i += BATCH) {
        const batch = nodes.slice(i, i + BATCH);

        const results = await Promise.all(
            batch.map(async (node) => ({
                id: node.id,
                color: node.color,
                thumbnail: await renderThumbnail(node.id, cache, apiUrl),
            }))
        );

        results.forEach((r) => {
            if (!r.thumbnail) return;
            visNodes.update({
                id: r.id,
                shape: "circularImage",
                image: r.thumbnail,
                size: nodeSize / 2,
                borderWidth: 3,
                mass: 2,
                color: { border: r.color.border, background: "transparent" },
                shapeProperties: { useBorderWithImage: true },
            });
        });
    }
};

window.GenealogyThumbnails = { renderThumbnail, renderAllThumbnails };
