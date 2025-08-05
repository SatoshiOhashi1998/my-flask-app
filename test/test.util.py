import os
import pytest
from unittest import mock
from unittest.mock import patch, MagicMock

from app.modules.video_utils import (
    get_video_paths,
    rename_files,
    get_video_datas,
    add_video_data,
    change_directory
)

# ---------- テスト: get_video_paths ----------
def test_get_video_paths(tmp_path):
    (tmp_path / "test1.mp4").write_text("dummy1")
    (tmp_path / "test2.mkv").write_text("dummy2")
    (tmp_path / "skip.txt").write_text("should not be found")

    result = get_video_paths(str(tmp_path))
    assert sorted(result) == ["test1.mp4", "test2.mkv"]


# ---------- テスト: rename_files ----------
def test_rename_files(monkeypatch, tmp_path):
    bad_name = tmp_path / "[ABC] Video #1.mp4"
    bad_name.write_text("content")

    logs = []
    monkeypatch.setattr("app.modules.video_utils.logging.info", lambda msg: logs.append(msg))

    rename_files(str(tmp_path))

    expected_name = tmp_path / "Video 1.mp4"
    assert expected_name.exists()
    assert not bad_name.exists()
    assert any("Renamed" in log for log in logs)


# ---------- テスト: get_video_datas ----------
@patch("app.modules.video_utils.Session")
def test_get_video_datas(mock_session_class):
    mock_session = MagicMock()
    mock_record = MagicMock(last_time=123, memo="Test memo")

    mock_session.query().filter_by().first.return_value = mock_record
    mock_session_class.return_value = mock_session

    result = get_video_datas("/dummy/dir")
    assert isinstance(result, list)
    assert result[0]["last_time"] == 123
    assert result[0]["memo"] == "Test memo"


# ---------- テスト: add_video_data ----------
@patch("app.modules.video_utils.Session")
def test_add_video_data(mock_session_class):
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session

    from app.modules.video_utils import VideoData

    video_data = VideoData(dirpath="/dummy", filename="file.mp4", last_time=1, memo="note")
    add_video_data(video_data)

    mock_session.add.assert_called()
    mock_session.commit.assert_called()
    mock_session.close.assert_called()


# ---------- テスト: change_directory ----------
def test_change_directory(tmp_path):
    original = os.getcwd()
    with change_directory(str(tmp_path)):
        assert os.getcwd() == str(tmp_path)
    assert os.getcwd() == original
