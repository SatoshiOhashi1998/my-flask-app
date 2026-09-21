"""
ChatGPT用コードコピー ユーティリティ

指定したファイル・ファイルのリスト・ディレクトリ内の
コードをまとめてクリップボードへコピーする。
"""

from pathlib import Path

from devtools.clipboard import copy_text


# コピー対象にする拡張子
DEFAULT_EXTENSIONS = {
    ".py",
    ".html",
    ".css",
    ".js",
    ".jsx",
    ".sql",
    ".md",
    ".txt",
}


# 除外するディレクトリ
DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".idea",
    ".vscode",
    "log",
    "logs",
}


def _collect_files(
    target,
    extensions=None,
    exclude_dirs=None,
    recursive=True,
):
    """
    指定されたパスから対象ファイルを収集する。
    """

    if extensions is None:
        extensions = DEFAULT_EXTENSIONS

    if exclude_dirs is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS

    if isinstance(target, (str, Path)):
        targets = [target]
    else:
        targets = target

    files = []

    for item in targets:
        path = Path(item)

        if not path.exists():
            print(f"[WARNING] ファイルが存在しません: {path}")
            continue

        if path.is_file():
            if path.suffix.lower() in extensions:
                files.append(path)
            else:
                print(f"[SKIP] 対象外の拡張子: {path}")

        elif path.is_dir():

            if recursive:
                file_paths = path.rglob("*")
            else:
                file_paths = path.iterdir()

            for file_path in file_paths:

                if not file_path.is_file():
                    continue

                if any(
                    excluded in file_path.parts
                    for excluded in exclude_dirs
                ):
                    continue

                if file_path.suffix.lower() in extensions:
                    files.append(file_path)

    return sorted(
        set(files),
        key=lambda p: str(p).lower(),
    )


def _read_file(path):
    """
    ファイルを読み込む。

    UTF-8を基本とし、読み込めない場合は
    UTF-8-SIGで再試行する。
    """

    try:
        return path.read_text(encoding="utf-8")

    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


def _build_text(files):
    """
    ChatGPTに貼り付けやすい形式のテキストを作る。
    """

    sections = []

    for path in files:

        try:
            content = _read_file(path)

        except Exception as e:
            sections.append(
                f"===== {path} =====\n"
                f"[読み込みエラー: {e}]"
            )
            continue

        sections.append(
            f"===== {path} =====\n\n"
            f"{content.rstrip()}\n"
        )

    return "\n\n".join(sections)


def copy_code(
    target,
    extensions=None,
    exclude_dirs=None,
    recursive=True,
):
    """
    ファイル・ファイルリスト・ディレクトリのコードを
    まとめてクリップボードへコピーする。

    Returns
    -------
    list[Path]
        コピーしたファイルの一覧。
    """

    files = _collect_files(
        target,
        extensions=extensions,
        exclude_dirs=exclude_dirs,
        recursive=recursive,
    )

    if not files:
        print("コピー対象のファイルがありません。")
        return []

    text = _build_text(files)

    copy_text(text)

    print()
    print("コピーしたファイル:")

    for path in files:
        print(f"  - {path}")

    print()
    print(f"合計 {len(files)} ファイル")

    return files
