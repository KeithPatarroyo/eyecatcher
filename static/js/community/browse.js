/**
 * Community browse: fetch list, display data, render list with previews.
 * Used by community.js. Exposes: CommunityBrowse.
 */
(function () {
    "use strict";

    const PREVIEW_CANVAS_SIZE = 80;

    async function fetchDisplayDataForList(list, toItem, getKey) {
        const RepresentationRegistry = window.RepresentationRegistry;
        if (
            !RepresentationRegistry ||
            !RepresentationRegistry.getDisplayData ||
            !RepresentationRegistry.findByGenome
        ) {
            return {};
        }
        const displayByKey = {};
        const promises = list.map(async (item) => {
            const payload = toItem(item);
            const genome =
                payload &&
                (payload.individual !== undefined
                    ? payload.individual
                    : payload.genome !== undefined
                      ? payload.genome
                      : payload);
            const key = getKey(item);
            const representation = RepresentationRegistry.findByGenome(genome);
            if (!representation) return;
            try {
                const result = await RepresentationRegistry.getDisplayData(
                    representation,
                    [genome],
                    {}
                );
                const pop = result && result.population && result.population[0];
                if (pop) displayByKey[key] = pop;
            } catch (e) {
                console.warn("Could not fetch preview for item " + key + ":", e);
            }
        });
        await Promise.all(promises);
        return displayByKey;
    }

    function buildPatternListEntry(
        li,
        item,
        canvas,
        displayItem,
        options,
        patternRenderer
    ) {
        li.className = options.itemClass || "";
        if (options.dataset) {
            Object.keys(options.dataset).forEach((k) => {
                li.dataset[k] = options.dataset[k];
            });
        }
        if (options.prependNodes) options.prependNodes(li, item);
        const previewWrap = canvas.parentElement;
        if (displayItem && displayItem.image) {
            const img = document.createElement("img");
            img.className = "preview-img";
            img.src = displayItem.image;
            img.width = PREVIEW_CANVAS_SIZE;
            img.alt = "";
            previewWrap.innerHTML = "";
            previewWrap.appendChild(img);
        }
        li.appendChild(previewWrap);
        const info = document.createElement("div");
        info.className = "info";
        const content = options.infoContent ? options.infoContent(item) : "";
        if (typeof content === "string") {
            info.textContent = content;
        } else if (content) {
            info.appendChild(content);
        }
        li.appendChild(info);
        if (options.appendNodes) options.appendNodes(li, item);
        if (displayItem && displayItem.shader && window.WebGLUtils) {
            return window.WebGLUtils.setupPattern(canvas, displayItem.shader);
        }
        return null;
    }

    function renderListWithPreviews(
        ul,
        list,
        displayByKey,
        getItemKey,
        buildLiContent,
        patternRenderer,
        viewerControls
    ) {
        const previewPatternData = [];
        list.forEach((item) => {
            const li = document.createElement("li");
            const previewWrap = document.createElement("div");
            previewWrap.className = "preview-wrap";
            const canvas = document.createElement("canvas");
            canvas.width = PREVIEW_CANVAS_SIZE;
            canvas.height = PREVIEW_CANVAS_SIZE;
            previewWrap.appendChild(canvas);
            const displayItem = displayByKey[getItemKey(item)];
            const pd = buildLiContent(li, item, canvas, displayItem);
            if (pd) previewPatternData.push(pd);
            ul.appendChild(li);
        });
        if (
            window.RepresentationRegistry &&
            viewerControls &&
            viewerControls.signalState != null &&
            previewPatternData.length > 0
        ) {
            const signalState = viewerControls.signalState;
            const RA = window.RepresentationRegistry;
            requestAnimationFrame(() => {
                previewPatternData.forEach((pd) =>
                    RA.renderFrameWithSignals(pd, signalState, null)
                );
            });
        }
    }

    window.CommunityBrowse = {
        PREVIEW_CANVAS_SIZE: PREVIEW_CANVAS_SIZE,
        fetchDisplayDataForList: fetchDisplayDataForList,
        buildPatternListEntry: buildPatternListEntry,
        renderListWithPreviews: renderListWithPreviews,
    };
})();
