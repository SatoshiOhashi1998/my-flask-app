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
- app.routes: ルーティングを定義するためのカスタムモジュール。
- app.scheduler: URLスケジューリングを管理するためのカスタムモジュール。

設定内容:
- セッションの持続時間は5分に設定されています。
- テンプレートフォルダは 'templates' に、静的ファイルフォルダは 'static' に指定されています。

"""

import logging
from datetime import timedelta
from flask import Flask
from flask_cors import CORS
from app.log import setup_logging
from app.routes import main
from app.modules.scheduler import UrlScheduler


def create_app():
    app = Flask(__name__, 
                template_folder='templates', 
                static_folder='static')
    app.permanent_session_lifetime = timedelta(minutes=5)
    CORS(app)  # CORS有効化

    # Blueprintを登録
    app.register_blueprint(main)

    setup_logging()

    scheduler = UrlScheduler()

    return app
