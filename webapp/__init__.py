# -*- coding: utf-8 -*-
"""Flask Application Factory."""

from flask import Flask
from webapp.models import db
from sqlalchemy import text
import os


def create_app():
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    # --- Configuration ---
    # app.root_path is webapp/, so data/ lives one level up (project root)
    _project_root = os.path.dirname(app.root_path)
    _data_dir = os.path.join(_project_root, 'data')
    _default_db_url = f'sqlite:///{os.path.join(_data_dir, "wildcard.db")}'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', _default_db_url)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['OLLAMA_MODEL'] = os.getenv('OLLAMA_MODEL', 'qwen3:8b')

    _in_docker = os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv')
    _default_ollama = 'http://host.docker.internal:11434' if _in_docker else 'http://localhost:11434'
    app.config['OLLAMA_BASE_URL'] = os.getenv('OLLAMA_BASE_URL', _default_ollama)

    # --- Database ---
    db.init_app(app)

    with app.app_context():
        os.makedirs(_data_dir, exist_ok=True)
        db.create_all()
        _migrate_schema()
        from webapp.init_data import init_all
        init_all()

    # --- Blueprints ---
    _register_blueprints(app)
    return app


def _migrate_schema():
    """Add columns that db.create_all() won't add to existing tables."""
    statements = [
        "ALTER TABLE translation_settings ADD COLUMN IF NOT EXISTS base_url VARCHAR(500)",
    ]
    for sql in statements:
        try:
            db.session.execute(text(sql))
            db.session.commit()
        except Exception:
            db.session.rollback()
            # SQLite fallback (no IF NOT EXISTS)
            try:
                db.session.execute(text(sql.replace(' IF NOT EXISTS', '')))
                db.session.commit()
            except Exception:
                db.session.rollback()


def _register_blueprints(app):
    from webapp.routes.pages import pages_bp
    from webapp.routes.api.categories import categories_bp
    from webapp.routes.api.wildcards import wildcards_bp
    from webapp.routes.api.import_export import import_export_bp
    from webapp.routes.api.comfy_sync import comfy_bp
    from webapp.routes.api.settings import settings_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(categories_bp, url_prefix='/api/categories')
    app.register_blueprint(wildcards_bp, url_prefix='/api/wildcards')
    app.register_blueprint(import_export_bp, url_prefix='/api')
    app.register_blueprint(comfy_bp, url_prefix='/api/comfy-wildcard')
    app.register_blueprint(settings_bp, url_prefix='/api')
