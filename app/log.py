import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # エラーログの設定
    error_handler = RotatingFileHandler(os.getenv('ERROR_LOG'), maxBytes=10240, backupCount=10)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    logging.getLogger().addHandler(error_handler)

    # アクセスログの設定
    access_handler = RotatingFileHandler(os.getenv('ACCESS_LOG'), maxBytes=10240, backupCount=10)
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    logging.getLogger().addHandler(access_handler)

    logging.getLogger().setLevel(logging.INFO)

    # コンソールへのログ出力
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    logging.getLogger().addHandler(console_handler)
