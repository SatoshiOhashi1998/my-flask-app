import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging():
    root_logger = logging.getLogger()

    # すでに設定済みなら何もしない
    if root_logger.handlers:
        return

    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    )

    # ========================================
    # application.log
    # ========================================

    application_handler = RotatingFileHandler(
        os.path.join(log_dir, "application.log"),
        maxBytes=10 * 1024,
        backupCount=10,
        encoding="utf-8"
    )
    application_handler.setLevel(logging.INFO)
    application_handler.setFormatter(formatter)

    # ========================================
    # error.log
    # ========================================

    error_handler = RotatingFileHandler(
        os.path.join(log_dir, "error.log"),
        maxBytes=10 * 1024,
        backupCount=10,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # ========================================
    # console
    # ========================================

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
        )
    )

    # ========================================
    # root logger
    # ========================================

    root_logger.setLevel(logging.INFO)

    root_logger.addHandler(application_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)

    # ========================================
    # HTTP access log
    # ========================================

    werkzeug_logger = logging.getLogger("werkzeug")

    werkzeug_logger.setLevel(logging.INFO)

    access_handler = RotatingFileHandler(
        os.path.join(log_dir, "access.log"),
        maxBytes=10 * 1024,
        backupCount=10,
        encoding="utf-8"
    )
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(formatter)

    werkzeug_logger.addHandler(access_handler)

    # Werkzeugのログをroot loggerへ
    # 流さない
    werkzeug_logger.propagate = False

    # ========================================
    # SQLAlchemy
    # ========================================

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
