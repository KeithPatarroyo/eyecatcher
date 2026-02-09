/**
 * Single source of truth for API base URL and dev port.
 * Load this before app.js, api_client.js, or genealogy_viewer.js.
 * Sets window.API_URL and window.DEFAULT_DEV_PORT.
 */
(function () {
    "use strict";

    var DEFAULT_DEV_PORT = 5001;

    function getApiBaseUrl() {
        if (
            typeof window !== "undefined" &&
            window.location &&
            window.location.origin &&
            window.location.protocol &&
            window.location.protocol.indexOf("http") === 0
        ) {
            return window.location.origin + "/api";
        }
        return "http://localhost:" + DEFAULT_DEV_PORT + "/api";
    }

    window.DEFAULT_DEV_PORT = DEFAULT_DEV_PORT;
    window.API_URL = getApiBaseUrl();
})();
