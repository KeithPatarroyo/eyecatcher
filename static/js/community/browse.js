/**
 * CommunityBrowse: preview helpers for community/admin lists.
 * Exposes: CommunityBrowse.fetchDisplayDataForList, buildPatternListEntry, renderListWithPreviews.
 */
import DisplayFetcher from "../representation/display_fetcher.js";
import RepresentationRegistry from "../representation/representation_registry.js";

const PREVIEW_CANVAS_SIZE = 80;

const getGenome = (payload) => {
    if (!payload) return null;
    if (payload.individual !== undefined) return payload.individual;
    if (payload.genome !== undefined) return payload.genome;
    return payload;
};

const fetchDisplayDataForList = async (list, toPayload, getKey) => {
    if (
        !RepresentationRegistry?.findByGenome ||
        typeof DisplayFetcher?.fetchDisplayData !== "function"
    )
        return {};

    const entries = await Promise.all(
        (list || []).map(async (item) => {
            const payload = toPayload(item);
            const genome = getGenome(payload);
            const key = getKey(item);
            const rep = genome ? RepresentationRegistry.findByGenome(genome) : null;
            if (!rep) return [key, null];

            try {
                const r = await DisplayFetcher.fetchDisplayData(rep, [genome], {});
                return [key, r?.population?.[0] || null];
            } catch {
                return [key, null];
            }
        })
    );

    const byKey = Object.create(null);
    for (const [k, v] of entries) if (v) byKey[k] = v;
    return byKey;
};

const buildPatternListEntry = (li, item, canvas, displayItem, options = {}) => {
    li.className = options.itemClass || "";
    if (options.dataset) Object.assign(li.dataset, options.dataset);

    options.prependNodes?.(li, item);

    const previewWrap = canvas.parentElement;
    previewWrap.innerHTML = "";

    if (displayItem?.image) {
        const img = document.createElement("img");
        img.className = "preview-img";
        img.src = displayItem.image;
        img.width = PREVIEW_CANVAS_SIZE;
        img.height = PREVIEW_CANVAS_SIZE;
        img.alt = "";
        previewWrap.appendChild(img);
    } else if (displayItem?.rule) {
        const placeholder = document.createElement("div");
        placeholder.className = "preview-placeholder";
        placeholder.textContent = "Preview";
        previewWrap.appendChild(placeholder);
    } else {
        previewWrap.appendChild(canvas);
    }

    li.appendChild(previewWrap);

    const info = document.createElement("div");
    info.className = "info";
    const content = options.infoContent?.(item) ?? "";
    if (typeof content === "string") info.textContent = content;
    else if (content) info.appendChild(content);
    li.appendChild(info);

    options.appendNodes?.(li, item);
    return null;
};

const renderListWithPreviews = (
    ul,
    list,
    displayByKey,
    getItemKey,
    buildLiContent,
    _patternRenderer,
    viewerControls
) => {
    const previewPatternData = [];
    ul.innerHTML = "";

    (list || []).forEach((item) => {
        const li = document.createElement("li");
        const wrap = document.createElement("div");
        wrap.className = "preview-wrap";

        const canvas = document.createElement("canvas");
        canvas.width = PREVIEW_CANVAS_SIZE;
        canvas.height = PREVIEW_CANVAS_SIZE;
        wrap.appendChild(canvas);

        const displayItem = displayByKey?.[getItemKey(item)];
        const pd = buildLiContent(li, item, canvas, displayItem);
        if (pd) previewPatternData.push(pd);

        ul.appendChild(li);
    });

    const signalState = viewerControls?.signalState;
    const renderFrame = window.AnimationLoop?.renderFrameWithSignals;
    if (!signalState || typeof renderFrame !== "function" || !previewPatternData.length)
        return;

    requestAnimationFrame(() =>
        previewPatternData.forEach((pd) => renderFrame(pd, signalState, null))
    );
};

const CommunityBrowse = {
    PREVIEW_CANVAS_SIZE,
    fetchDisplayDataForList,
    buildPatternListEntry,
    renderListWithPreviews,
};

export default CommunityBrowse;
export { CommunityBrowse };
window.CommunityBrowse = CommunityBrowse;
