"""
Flaskアプリケーションモジュール
"""

import os
from datetime import timedelta
from flask import Flask
from flask_cors import CORS

from app.log import setup_logging
from app.views.web import web
from app.views.api import api_bp
from app.modules.scheduler import UrlScheduler
from app.models import db


def create_app(test_config=None):
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )

    app.permanent_session_lifetime = timedelta(minutes=5)
    app.config['JSON_AS_ASCII'] = False

    if test_config:
        app.config.update(test_config)

    CORS(app)

    app.register_blueprint(web)
    app.register_blueprint(api_bp)

    setup_logging()

    # DB設定
    DB_PATH = os.getenv('DB_PATH')

    if not DB_PATH:
        raise ValueError('DB_PATHが環境変数に設定されていません。')

    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"

    app.config.setdefault(
        'SQLALCHEMY_TRACK_MODIFICATIONS',
        False
    )

    db.init_app(app)

    with app.app_context():
        db.create_all()

    # テスト時はスケジューラーを起動しない
    if not app.config.get('TESTING'):
        scheduler = UrlScheduler(app=app)

    return app
