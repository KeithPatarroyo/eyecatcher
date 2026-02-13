/**
 * Event binding definitions and application for the main app.
 * Bindings map element IDs to handlers; app.js supplies IDS and handler functions.
 */
(function () {
    "use strict";

    /**
     * Each entry: [IDS key, handler key, optional true for role keydown].
     * app.js passes handlers object with these keys.
     */
    var BINDINGS = [
        ["fullscreenClose", "closeFullscreen"],
        ["fullscreenBackdrop", "closeFullscreen"],
        ["evolveBtn", "evolveGeneration", true],
        ["loadModalClose", "closeLoadModal"],
        ["communitySubmitDo", "submitCommunityForm"],
        ["communitySubmitCancel", "closeSubmitCommunityModal"],
        ["communityListClose", "closeCommunityListModal"],
        ["communityLoadSelectedBtn", "onCommunityLoadSelected"],
        ["communityLoad12Btn", "onCommunityLoad12"],
        ["communitySelectAllBtn", "onCommunitySelectAll"],
        ["communityDeselectAllBtn", "onCommunityDeselectAll"],
        ["newFromCommunityBtn", "onNewFromCommunityClick", true],
        ["adminKeySubmit", "submitAdminKey"],
        ["adminModalCancel", "closeAdminModal"],
        ["adminListClose", "closeAdminModal"],
        ["saveCurrentBtn", "onSaveCurrentClick"],
        ["importBtn", "onImportClick"],
    ];

    function onRoleButtonKeydown(e, onClick) {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onClick();
        }
    }

    /**
     * Apply click (and optional keydown) bindings.
     * @param {Object} IDS - map of binding key to element id string
     * @param {Object} handlers - map of handler key to function
     * @param {function(string, function)} onId - called with element id and callback(el)
     */
    function applyEventBindings(IDS, handlers, onId) {
        BINDINGS.forEach(function (b) {
            var idKey = b[0];
            var handlerKey = b[1];
            var withRoleKeydown = b[2];
            var id = IDS[idKey];
            var handler = handlers[handlerKey];
            if (!id || !handler) return;
            onId(id, function (el) {
                el.addEventListener("click", handler);
                if (withRoleKeydown) {
                    el.addEventListener("keydown", function (e) {
                        onRoleButtonKeydown(e, handler);
                    });
                }
            });
        });
    }

    window.AppEventBindings = {
        applyEventBindings: applyEventBindings,
        BINDINGS: BINDINGS,
    };
})();
