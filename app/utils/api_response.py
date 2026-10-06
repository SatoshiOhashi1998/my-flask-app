from flask import jsonify


def success(data=None, message=None, status_code=200):
    """成功レスポンスを生成する。"""
    response = {}

    if data is not None:
        response["data"] = data

    if message is not None:
        response["message"] = message

    return jsonify(response), status_code


def error(message, status_code=500):
    """エラーレスポンスを生成する。"""
    return jsonify({"error": message}), status_code
