import logging
from pathlib import Path

from flask import Flask, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config


def create_app(overrides=None):
    """Application factory: keeps config and testing clean."""
    root = Path(__file__).resolve().parent.parent
    app = Flask(__name__, static_folder=str(root / "frontend"), static_url_path="")
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)
    if app.config.get("TRUST_PROXY"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
    logging.basicConfig(level=logging.INFO)

    from .routes import api

    app.register_blueprint(api, url_prefix="/api")

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.errorhandler(413)
    def too_large(_):
        return jsonify({"error": "That photo is too large. Try a smaller one.", "code": "FILE_TOO_LARGE"}), 413

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "Not found.", "code": "NOT_FOUND"}), 404

    @app.errorhandler(500)
    def server_error(_):
        return jsonify({"error": "Something went wrong on our side. Please try again.", "code": "INTERNAL"}), 500

    return app
