/**
 * Substrate registry: routes phenotype.substrate.type to a Substrate instance.
 * Unknown names fall back to ImageSubstrate (static image from backend).
 */
(() => {
    "use strict";

    const substrates = Object.create(null);
    let defaultSubstrate = null;

    const getSubstrate = (name) => (name ? substrates[name] : null) || defaultSubstrate;

    const registerSubstrate = (name, substrate) => {
        if (name && substrate) substrates[name] = substrate;
    };

    const setDefaultSubstrate = (substrate) => {
        defaultSubstrate = substrate || defaultSubstrate;
    };

    const initDefaults = () => {
        if (window.ImageSubstrate && !defaultSubstrate)
            defaultSubstrate = new window.ImageSubstrate();
        if (window.FieldSubstrate && !substrates.field)
            registerSubstrate("field", new window.FieldSubstrate());
        if (window.GridSubstrate && !substrates.grid)
            registerSubstrate("grid", new window.GridSubstrate());
        if (window.ImageSubstrate && !substrates.image)
            registerSubstrate("image", new window.ImageSubstrate());
    };

    window.SubstrateRegistry = {
        getSubstrate,
        registerSubstrate,
        setDefaultSubstrate,
        initDefaults,
    };
})();
