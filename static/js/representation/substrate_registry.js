/**
 * Substrate registry: routes phenotype.substrate.type to a Substrate instance.
 * Unknown names fall back to ImageSubstrate (static image from backend).
 */
import ImageSubstrate from "./image_substrate.js";
import FieldSubstrate from "./field_substrate.js";
import GridSubstrate from "./grid_substrate.js";

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
    if (!defaultSubstrate) defaultSubstrate = new ImageSubstrate();
    if (!substrates.field) registerSubstrate("field", new FieldSubstrate());
    if (!substrates.grid) registerSubstrate("grid", new GridSubstrate());
    if (!substrates.image) registerSubstrate("image", new ImageSubstrate());
};

const SubstrateRegistry = {
    getSubstrate,
    registerSubstrate,
    setDefaultSubstrate,
    initDefaults,
};

export default SubstrateRegistry;
