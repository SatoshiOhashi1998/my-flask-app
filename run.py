from dotenv import load_dotenv

load_dotenv()

import os
import logging
import pythoncom
from app import create_app

app = create_app()


if __name__ == "__main__":
    try:
        pythoncom.CoInitialize()
        # app.run(host="0.0.0.0", port=5000)
        app.run(debug=True)
    except Exception as e:
        logging.error(f'エラー発生: {str(e)}')
