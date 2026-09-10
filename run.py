from dotenv import load_dotenv
load_dotenv()

import logging
import os

from app import create_app


if os.name == "nt":
    import pythoncom


app = create_app()


if __name__ == "__main__":
    try:
        if os.name == "nt":
            pythoncom.CoInitialize()

        app.run(host="0.0.0.0", port=5000)

    except Exception as e:
        logging.error(f"エラー発生: {str(e)}")
