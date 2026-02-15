/**
 * Substrate registry: routes phenotype.substrate to a Substrate instance.
 * Unknown substrate names fall back to ImageSubstrate (static image from backend).
 */
(function () {
    "use strict";

    var substrates = {};
    var defaultSubstrate = null;

    function getSubstrate(name) {
        if (!name) return defaultSubstrate;
        return substrates[name] || defaultSubstrate;
    }

    function registerSubstrate(name, substrate) {
        if (substrate) substrates[name] = substrate;
    }

    function setDefaultSubstrate(substrate) {
        defaultSubstrate = substrate;
    }

    function initDefaults() {
        if (window.ImageSubstrate && !defaultSubstrate) {
            defaultSubstrate = new window.ImageSubstrate();
        }
        if (window.FieldSubstrate && !substrates.field) {
            registerSubstrate("field", new window.FieldSubstrate());
        }
        if (window.GridSubstrate && !substrates.grid) {
            registerSubstrate("grid", new window.GridSubstrate());
        }
        if (window.ImageSubstrate && !substrates.image) {
            registerSubstrate("image", new window.ImageSubstrate());
        }
    }

    window.SubstrateRegistry = {
        getSubstrate: getSubstrate,
        registerSubstrate: registerSubstrate,
        setDefaultSubstrate: setDefaultSubstrate,
        initDefaults: initDefaults,
    };
})();
