from unittest.mock import patch


@patch("app.views.clipboard_api.copy_code")
def test_copy_code_get(
    mock_copy,
    client,
):
    mock_copy.return_value = [
        "file1.py",
        "file2.py",
    ]

    response = client.get(
        "/api/clipboard/copy-code"
        "?target=test.py"
        "&extension=.py"
        "&extension=.js"
        "&exclude_dir=.git"
        "&recursive=false"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "success"
    assert data["files"] == [
        "file1.py",
        "file2.py",
    ]
    assert "2 ファイル" in data["message"]

    mock_copy.assert_called_once_with(
        target="test.py",
        extensions=[".py", ".js"],
        exclude_dirs=[".git"],
        recursive=False,
    )
