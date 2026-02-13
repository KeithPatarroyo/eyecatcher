"""
Entry point for the Flask app (eyecatcher.server:app).

The app is defined in web.app; this module re-exports it so run commands
and tests can keep using ``from eyecatcher.server import app``.
"""

import os

from .web.app import app

__all__ = ["app"]

if __name__ == "__main__":
    from .web.app import DEFAULT_PORT, app, logger, representation

    port = int(os.environ.get("PORT", DEFAULT_PORT))
    debug = os.environ.get("FLASK_ENV") == "development"
    logger.info("=" * 60)
    logger.info("EYECATCHER - Interactive Evolution Server")
    logger.info("Representation: %s", representation.id)
    logger.info("=" * 60)
    logger.info("Starting server... Open http://localhost:%s in your browser", port)
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)
    app.run(debug=debug, port=port, host="0.0.0.0")
