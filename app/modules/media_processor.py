import os

import ffmpeg


FFMPEG_PATH = os.getenv("FFMPEG_PATH")


def trim_media(
    input_file: str,
    output_file: str,
    start_time: str | None = None,
    end_time: str | None = None,
    media_type: str = "video",
) -> None:
    """メディアファイルを指定時間範囲でトリミングする。"""

    try:
        stream = ffmpeg.input(
            input_file,
            ss=start_time,
            to=end_time,
        )

        if media_type == "audio":
            stream = ffmpeg.output(
                stream,
                output_file,
                acodec="libmp3lame",
            )
        else:
            stream = ffmpeg.output(
                stream,
                output_file,
                vcodec="libx264",
                acodec="aac",
            )

        ffmpeg.run(
            stream,
            overwrite_output=True,
            cmd=FFMPEG_PATH,
        )

    except Exception as e:
        if os.path.exists(output_file):
            os.remove(output_file)

        raise RuntimeError(
            f"トリミング処理に失敗しました: {str(e)}"
        )
