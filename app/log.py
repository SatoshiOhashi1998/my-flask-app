# log.py
import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    logger = logging.getLogger()

    # すでに設定済みなら何もしない
    if logger.hasHandlers():
        return

    # ログディレクトリ作成
    log_dir = os.path.dirname(os.getenv('ERROR_LOG', 'logs/error.log'))
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # エラーログ
    error_handler = RotatingFileHandler(
        os.getenv('ERROR_LOG', 'logs/error.log'),
        maxBytes=10 * 1024,
        backupCount=10,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    logger.addHandler(error_handler)

    # アクセスログ
    access_handler = RotatingFileHandler(
        os.getenv('ACCESS_LOG', 'logs/access.log'),
        maxBytes=10 * 1024,
        backupCount=10,
        encoding="utf-8"
    )
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    logger.addHandler(access_handler)

    # コンソール出力
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))
    logger.addHandler(console_handler)

    # ルートロガーのレベル設定
    logger.setLevel(logging.INFO)

    # SQLAlchemy のログレベル
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
