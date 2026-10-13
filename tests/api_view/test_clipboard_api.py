from unittest.mock import patch
import pytest


def assert_error(response, status_code, fragment=None):
    assert response.status_code == status_code
    payload = response.get_json()
    assert isinstance(payload.get("error"), str)
    if fragment:
        assert fragment.lower() in payload["error"].lower()


def test_copy_code_get(client, tmp_path):
    target = tmp_path / "source"
    target.mkdir()
    (target / "sample.py").write_text("print('hello')\n", encoding="utf-8")

    response = client.get(
        "/api/clipboard/copy-code",
        query_string={"target": str(target), "extensions": ".py"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload["data"]["files"], list)
    assert "message" in payload
    assert "status" not in payload


def test_copy_code_post(client, tmp_path):
    target = tmp_path / "source"
    target.mkdir()
    (target / "sample.py").write_text("print('hello')\n", encoding="utf-8")

    response = client.post(
        "/api/clipboard/copy-code",
        json={"target": str(target), "extensions": [".py"], "recursive": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload["data"]["files"], list)
    assert "message" in payload


@pytest.mark.parametrize("method", ["get", "post"])
def test_copy_code_missing_target(client, method):
    response = getattr(client, method)("/api/clipboard/copy-code", json={} if method == "post" else None)
    assert_error(response, 400)


def test_copy_file_tree_get(client, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "main.py").write_text("print('ok')", encoding="utf-8")

    response = client.get(
        "/api/clipboard/copy-file-tree",
        query_string={"target": str(root)},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert "tree" in payload["data"]
    assert "message" in payload


def test_copy_file_tree_post(client, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "main.py").write_text("print('ok')", encoding="utf-8")

    response = client.post(
        "/api/clipboard/copy-file-tree",
        json={"target": str(root)},
    )
    assert response.status_code == 200
    assert "tree" in response.get_json()["data"]


def test_copy_file_tree_missing_target(client):
    assert_error(client.get("/api/clipboard/copy-file-tree"), 400)
