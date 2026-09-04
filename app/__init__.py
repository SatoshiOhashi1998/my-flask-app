"""
Flaskアプリケーションモジュール

このモジュールは、Flaskを使用してWebアプリケーションを作成します。アプリケーションは、指定されたテンプレートフォルダと静的ファイルフォルダを使用し、CORSを有効化します。
また、URLスケジューラーとログ機能が統合されています。

使用方法:
1. Flaskアプリケーションを作成するために、`create_app()` 関数を呼び出します。
2. 必要に応じて、アプリケーションの設定を変更します。
3. アプリケーションを実行するには、`flask run` を使用します。

依存関係:
- Flask: Webアプリケーションを構築するためのフレームワーク。
- flask_cors: CORS (Cross-Origin Resource Sharing)を有効にするためのライブラリ。
- app.log: ロギングの設定を行うためのカスタムモジュール。
- app.views.web: 画面描画用ルーティングを定義するためのカスタムモジュール。
- app.views.api: API用ルーティングを定義するためのカスタムモジュール。
- app.scheduler: URLスケジューリングを管理するためのカスタムモジュール。

設定内容:
- セッションの持続時間は5分に設定されています。
- テンプレートフォルダは 'templates' に、静的ファイルフォルダは 'static' に指定されています。

"""

import os
import logging
from pathlib import Path
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
    if 'SQLALCHEMY_DATABASE_URI' not in app.config:
        DB_PATH = Path(__file__).resolve().parent / 'video_data.db'
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
