/**
 * Toast notifications and download helpers.
 * Exposes: window.Toast (show, dismiss, error, base64ToBlob, triggerDownload).
 */
(function () {
    "use strict";

    function show(title, body, type, options) {
        type = type || "success";
        options = options || {};
        const container = document.getElementById("toast-container");
        const toast = document.createElement("div");
        toast.className = "toast " + type;

        const closeBtn = document.createElement("button");
        closeBtn.className = "toast-close";
        closeBtn.setAttribute("aria-label", "Close");
        closeBtn.textContent = "\u00D7";
        closeBtn.onclick = function () {
            dismiss(toast);
        };
        toast.appendChild(closeBtn);

        const titleEl = document.createElement("div");
        titleEl.className = "toast-title";
        titleEl.textContent = title;
        toast.appendChild(titleEl);

        if (body) {
            const bodyEl = document.createElement("div");
            bodyEl.className = "toast-body";
            bodyEl.textContent = body;
            toast.appendChild(bodyEl);
        }
        if (options.linkText && options.linkUrl) {
            const link = document.createElement("a");
            link.className = "toast-link";
            link.href = options.linkUrl;
            link.target = "_blank";
            link.rel = "noopener";
            link.textContent = options.linkText;
            toast.appendChild(link);
        }

        container.appendChild(toast);

        const duration = options.duration || (options.linkUrl ? 10000 : 6000);
        setTimeout(function () {
            dismiss(toast);
        }, duration);

        return toast;
    }

    function dismiss(toast) {
        if (!toast.parentNode) return;
        toast.classList.add("dismissing");
        setTimeout(function () {
            toast.remove();
        }, 300);
    }

    function error(message) {
        return show("Error", message, "error");
    }

    function base64ToBlob(base64, mime) {
        const bin = atob(base64);
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        return new Blob([bytes], { type: mime });
    }

    function triggerDownload(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.classList.add("hidden");
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    var Toast = {
        show: show,
        dismiss: dismiss,
        error: error,
        base64ToBlob: base64ToBlob,
        triggerDownload: triggerDownload,
    };

    window.Toast = Toast;
})();
