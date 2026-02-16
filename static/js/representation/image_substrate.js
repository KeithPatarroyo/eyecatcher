/**
 * ImageSubstrate: fallback substrate for static image display.
 * Used when phenotype.substrate has no registered substrate (e.g. "audio" before AudioSubstrate exists).
 * Backend render_to_image() provides the display.
 */
(() => {
    "use strict";

    const Substrate = window.Substrate;

    class ImageSubstrate extends Substrate {
        createDisplayElement(phenotype, patternPayload) {
            const src = patternPayload?.image;
            if (!src) return { element: this._createFallback("No image"), state: null };

            const size = phenotype?.displaySize ?? 256;

            const img = document.createElement("img");
            img.className = "organism-canvas organism-image";
            img.src = src;
            img.width = size;
            img.height = size;
            img.alt = `Pattern ${patternPayload?.id ?? ""}`;

            return { element: img, state: null };
        }
    }

    window.ImageSubstrate = ImageSubstrate;
})();
