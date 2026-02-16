/**
 * Toast notifications + small download helpers.
 * Exposes: Toast.show(title, message, type, opts), Toast.triggerDownload(blob, filename),
 * Toast.base64ToBlob(base64, mime).
 */
const DEFAULT_DURATION = 3500;

const getContainer = () => {
    let el = document.getElementById("toast-container");
    if (!el) {
        el = document.createElement("div");
        el.id = "toast-container";
        document.body.appendChild(el);
    }
    return el;
};

const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = String(text);
    return node;
};

const normalizeType = (type) => {
    if (type === "success" || type === "error" || type === "info") return type;
    return "info";
};

const removeLater = (node, duration) => {
    const ms = typeof duration === "number" ? duration : DEFAULT_DURATION;
    if (ms <= 0) return;

    const id = setTimeout(() => {
        node.classList.add("toast-hide");
        // Allow CSS transition to run
        setTimeout(() => node.remove(), 200);
    }, ms);

    // allow manual cancel if caller needs it later
    return () => clearTimeout(id);
};

const base64ToBlob = (base64, mime = "application/octet-stream") => {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new Blob([bytes], { type: mime });
};

const triggerDownload = (blob, filename = "download.bin") => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
};

/**
 * Show a toast message.
 * @param {string} title
 * @param {string} message
 * @param {"success"|"error"|"info"} type
 * @param {{ duration?: number, onClick?: function, dismissible?: boolean }} opts
 */
const show = (title, message, type = "info", opts = {}) => {
    const t = normalizeType(type);
    const container = getContainer();

    const toast = el("div", `toast toast-${t}`);
    const header = el("div", "toast-header");
    const body = el("div", "toast-body");

    header.appendChild(el("div", "toast-title", title || ""));
    body.appendChild(el("div", "toast-message", message || ""));

    if (opts.dismissible !== false) {
        const closeBtn = el("button", "toast-close", "×");
        closeBtn.type = "button";
        closeBtn.setAttribute("aria-label", "Close");
        closeBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            toast.classList.add("toast-hide");
            setTimeout(() => toast.remove(), 150);
        });
        header.appendChild(closeBtn);
    }

    toast.appendChild(header);
    toast.appendChild(body);

    if (typeof opts.onClick === "function") {
        toast.classList.add("toast-clickable");
        toast.addEventListener("click", () => opts.onClick());
    }

    container.appendChild(toast);

    // Trigger CSS entrance animations if defined
    requestAnimationFrame(() => toast.classList.add("toast-show"));

    removeLater(toast, opts.duration);

    return toast;
};

/**
 * Convenience shorthand for error toasts.
 * @param {string} message
 * @param {{ duration?: number }} opts
 */
const error = (message, opts) => show("Error", message, "error", opts);

/**
 * Convenience shorthand for info toasts.
 * @param {string} message
 * @param {{ duration?: number }} opts
 */
const info = (message, opts) => show("Info", message, "info", opts);

/**
 * Convenience shorthand for success toasts.
 * @param {string} message
 * @param {{ duration?: number }} opts
 */
const success = (message, opts) => show("Success", message, "success", opts);

const Toast = { show, error, info, success, triggerDownload, base64ToBlob };
export { show, error, info, success, triggerDownload, base64ToBlob };
export default Toast;
window.Toast = Toast;
