/**
 * DOM helpers: byId, qs, on, setText, toggleClass, setHidden, delegate.
 * Use these instead of repeated getElementById, querySelector, addEventListener, and classList toggles.
 */
const byId = (id) => (id ? document.getElementById(id) : null);

const qs = (sel, root = null) => {
    const el = root ?? document;
    return el.querySelector?.(sel) ?? null;
};

/**
 * Attach event listener; no-op if el is null.
 * @param {Element|null} el
 * @param {string} event
 * @param {EventListener} handler
 * @param {AddEventListenerOptions|boolean} [opts]
 */
const on = (el, event, handler, opts) => {
    if (el) el.addEventListener(event, handler, opts);
};

const setText = (el, text) => {
    if (el) el.textContent = text != null ? String(text) : "";
};

/**
 * Add or remove a class. If `on` is undefined, toggles the class.
 * @param {Element|null} el
 * @param {string} name
 * @param {boolean|undefined} [on]
 */
const toggleClass = (el, name, onVal) => {
    if (!el?.classList) return;
    if (onVal === undefined) el.classList.toggle(name);
    else el.classList.toggle(name, !!onVal);
};

/**
 * Show or hide element. Uses .hidden class if present, else sets element.hidden.
 * @param {Element|null} el
 * @param {boolean} hidden
 */
const setHidden = (el, hidden) => {
    if (!el) return;
    el.classList?.toggle("hidden", !!hidden);
};

/**
 * Event delegation: one listener on root; handler runs when target matches selector.
 * @param {Element} root
 * @param {string} event
 * @param {string} selector
 * @param {(ev: Event, matched: Element) => void} handler
 */
const delegate = (root, event, selector, handler) => {
    if (!root) return;
    root.addEventListener(event, (ev) => {
        const matched = ev.target?.closest?.(selector);
        if (matched) handler(ev, matched);
    });
};

/**
 * Clone a template, pick a root element, and fill text/attrs by selector map.
 * @param {HTMLTemplateElement} tpl
 * @param {string} rootSelector - selector within cloned content (e.g. ".branch-item")
 * @param {Record<string, string|{text?: string, attr?: Record<string, string>}>} fillers - selector -> text or { text, attr }
 * @returns {Element|null} the filled root element, or null
 */
const cloneAndFill = (tpl, rootSelector, fillers) => {
    if (!tpl?.content) return null;
    const clone = tpl.content.cloneNode(true);
    const root = qs(rootSelector, clone);
    if (!root) return null;
    for (const [sel, value] of Object.entries(fillers || {})) {
        const el = qs(sel, root);
        if (!el) continue;
        if (typeof value === "string") {
            setText(el, value);
        } else if (value && typeof value === "object") {
            if (value.text != null) setText(el, value.text);
            if (value.attr)
                for (const [k, v] of Object.entries(value.attr)) el.setAttribute(k, v);
        }
    }
    return root;
};

export { byId, qs, on, setText, toggleClass, setHidden, delegate, cloneAndFill };
const DOM = { byId, qs, on, setText, toggleClass, setHidden, delegate, cloneAndFill };
export default DOM;
