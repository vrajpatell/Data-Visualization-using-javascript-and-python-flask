from __future__ import annotations
import logging
from flask import Flask
from app.config import Config
from app.routes import bp
from app.services.cache import init_db, seed_bootstrap_if_empty, all_records
from app.services.model import train

def create_app(config_class=Config):
    app=Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object(config_class)
    # Re-read environment-backed settings at app creation time so tests and deployments
    # can override values after the Config class has been imported.
    import os
    if os.getenv('SQLITE_DB_PATH'): app.config['SQLITE_DB_PATH']=os.getenv('SQLITE_DB_PATH')
    if os.getenv('ENABLE_BOOTSTRAP_DATA') is not None: app.config['ENABLE_BOOTSTRAP_DATA']=os.getenv('ENABLE_BOOTSTRAP_DATA','false').lower() in {'1','true','yes','on'}
    if os.getenv('ALLOW_BOOTSTRAP_AS_FRESH_CACHE') is not None: app.config['ALLOW_BOOTSTRAP_AS_FRESH_CACHE']=os.getenv('ALLOW_BOOTSTRAP_AS_FRESH_CACHE','false').lower() in {'1','true','yes','on'}
    if os.getenv('ENABLED_SOURCES'): app.config['ENABLED_SOURCES']=os.getenv('ENABLED_SOURCES')
    logging.basicConfig(level=logging.INFO)
    init_db(app.config['SQLITE_DB_PATH'])
    seed_bootstrap_if_empty(app.config['SQLITE_DB_PATH'], app.config['ENABLE_BOOTSTRAP_DATA'])
    if app.config['ENABLE_MODEL_TRAINING_ON_STARTUP']:
        try: train(all_records(app.config['SQLITE_DB_PATH']), app.config['MODEL_PATH'])
        except Exception: app.logger.exception('Startup model training failed')
    app.register_blueprint(bp)
    return app
