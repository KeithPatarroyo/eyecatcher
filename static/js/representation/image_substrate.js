/**
 * ImageSubstrate: fallback substrate for static image display.
 * Used when phenotype.substrate has no registered substrate (e.g. "audio" before AudioSubstrate exists).
 * Backend render_to_image() provides the display.
 */
(function () {
    "use strict";

    var Substrate = window.Substrate;

    class ImageSubstrate extends Substrate {
        createDisplayElement(phenotype, patternPayload) {
            if (patternPayload && patternPayload.image) {
                var img = document.createElement("img");
                img.className = "pattern-canvas pattern-image";
                img.src = patternPayload.image;
                img.width = 256;
                img.height = 256;
                img.alt =
                    "Pattern " + (patternPayload.id != null ? patternPayload.id : "");
                return { element: img, state: null };
            }
            var fallback = document.createElement("div");
            fallback.className = "pattern-canvas-fallback";
            fallback.textContent = "No image";
            return { element: fallback, state: null };
        }
    }

    window.ImageSubstrate = ImageSubstrate;
})();
