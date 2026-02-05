/**
 * Toast notifications and download helpers.
 * Defines: showToast, dismissToast, base64ToBlob, triggerDownload (global).
 */
(function () {
    'use strict';

    function showToast(title, body, type = 'success', options = {}) {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.style.position = 'relative';

        let html = '<button class="toast-close" aria-label="Close">&times;</button>';
        html += `<div class="toast-title">${title}</div>`;
        if (body) html += `<div class="toast-body">${body}</div>`;
        if (options.linkText && options.linkUrl) {
            html += `<a class="toast-link" href="${options.linkUrl}" target="_blank">${options.linkText}</a>`;
        }
        toast.innerHTML = html;

        toast.querySelector('.toast-close').onclick = () => dismissToast(toast);
        container.appendChild(toast);

        const duration = options.duration || (options.linkUrl ? 10000 : 6000);
        setTimeout(() => dismissToast(toast), duration);

        return toast;
    }

    function dismissToast(toast) {
        if (!toast.parentNode) return;
        toast.style.animation = 'toast-out 0.3s ease-in forwards';
        setTimeout(() => toast.remove(), 300);
    }

    function base64ToBlob(base64, mime) {
        const bin = atob(base64);
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        return new Blob([bytes], { type: mime });
    }

    function triggerDownload(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    window.showToast = showToast;
    window.dismissToast = dismissToast;
    window.base64ToBlob = base64ToBlob;
    window.triggerDownload = triggerDownload;
})();
