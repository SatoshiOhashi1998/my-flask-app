import pytest

from app.modules import media_processor


def test_trim_media_video_uses_correct_ffmpeg_options(
    tmp_path,
    monkeypatch,
):
    input_file = tmp_path / "test_video.mp4"
    output_file = tmp_path / "test_video.tmp.mp4"

    input_file.write_bytes(b"dummy video")

    captured_input = {}
    captured_output = {}
    captured_run = {}

    def dummy_input(filename, ss=None, to=None):
        captured_input["filename"] = filename
        captured_input["ss"] = ss
        captured_input["to"] = to
        return "input_stream"

    def dummy_output(
        stream,
        filename,
        vcodec=None,
        acodec=None,
    ):
        captured_output["stream"] = stream
        captured_output["filename"] = filename
        captured_output["vcodec"] = vcodec
        captured_output["acodec"] = acodec
        return "output_stream"

    def dummy_run(
        stream,
        overwrite_output=False,
        cmd=None,
    ):
        captured_run["stream"] = stream
        captured_run["overwrite_output"] = overwrite_output
        captured_run["cmd"] = cmd

        # FFmpegが生成したファイルを再現
        output_file.write_bytes(b"trimmed video")

    monkeypatch.setattr(
        media_processor.ffmpeg,
        "input",
        dummy_input,
    )

    monkeypatch.setattr(
        media_processor.ffmpeg,
        "output",
        dummy_output,
    )

    monkeypatch.setattr(
        media_processor.ffmpeg,
        "run",
        dummy_run,
    )

    media_processor.trim_media(
        str(input_file),
        str(output_file),
        start_time="01:00",
        end_time="02:00",
        media_type="video",
    )

    assert captured_input == {
        "filename": str(input_file),
        "ss": "01:00",
        "to": "02:00",
    }

    assert captured_output == {
        "stream": "input_stream",
        "filename": str(output_file),
        "vcodec": "libx264",
        "acodec": "aac",
    }

    assert captured_run == {
        "stream": "output_stream",
        "overwrite_output": True,
        "cmd": media_processor.FFMPEG_PATH,
    }


def test_trim_media_audio_uses_correct_ffmpeg_options(
    tmp_path,
    monkeypatch,
):
    input_file = tmp_path / "test_audio.mp3"
    output_file = tmp_path / "test_audio.tmp.mp3"

    input_file.write_bytes(b"dummy audio")

    captured_input = {}
    captured_output = {}
    captured_run = {}

    def dummy_input(filename, ss=None, to=None):
        captured_input["filename"] = filename
        captured_input["ss"] = ss
        captured_input["to"] = to
        return "input_stream"

    def dummy_output(
        stream,
        filename,
        acodec=None,
    ):
        captured_output["stream"] = stream
        captured_output["filename"] = filename
        captured_output["acodec"] = acodec
        return "output_stream"

    def dummy_run(
        stream,
        overwrite_output=False,
        cmd=None,
    ):
        captured_run["stream"] = stream
        captured_run["overwrite_output"] = overwrite_output
        captured_run["cmd"] = cmd

        # FFmpegが生成したファイルを再現
        output_file.write_bytes(b"trimmed audio")

    monkeypatch.setattr(
        media_processor.ffmpeg,
        "input",
        dummy_input,
    )

    monkeypatch.setattr(
        media_processor.ffmpeg,
        "output",
        dummy_output,
    )

    monkeypatch.setattr(
        media_processor.ffmpeg,
        "run",
        dummy_run,
    )

    media_processor.trim_media(
        str(input_file),
        str(output_file),
        start_time="01:00",
        end_time="02:00",
        media_type="audio",
    )

    assert captured_input == {
        "filename": str(input_file),
        "ss": "01:00",
        "to": "02:00",
    }

    assert captured_output == {
        "stream": "input_stream",
        "filename": str(output_file),
        "acodec": "libmp3lame",
    }

    assert captured_run == {
        "stream": "output_stream",
        "overwrite_output": True,
        "cmd": media_processor.FFMPEG_PATH,
    }


def test_trim_media_removes_output_file_when_ffmpeg_fails(
    tmp_path,
    monkeypatch,
):
    input_file = tmp_path / "test_video.mp4"
    output_file = tmp_path / "test_video.tmp.mp4"

    input_file.write_bytes(b"dummy video")

    def dummy_input(filename, ss=None, to=None):
        return "input_stream"

    def dummy_output(
        stream,
        filename,
        vcodec=None,
        acodec=None,
    ):
        # FFmpegが途中までファイルを作った状態を再現
        output_file.write_bytes(b"partial output")
        return "output_stream"

    def dummy_run(
        stream,
        overwrite_output=False,
        cmd=None,
    ):
        raise RuntimeError("FFmpeg error")

    monkeypatch.setattr(
        media_processor.ffmpeg,
        "input",
        dummy_input,
    )

    monkeypatch.setattr(
        media_processor.ffmpeg,
        "output",
        dummy_output,
    )

    monkeypatch.setattr(
        media_processor.ffmpeg,
        "run",
        dummy_run,
    )

    with pytest.raises(
        RuntimeError,
        match="トリミング処理に失敗しました",
    ):
        media_processor.trim_media(
            str(input_file),
            str(output_file),
            start_time="01:00",
            end_time="02:00",
            media_type="video",
        )

    assert not output_file.exists()
