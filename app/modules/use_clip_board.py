"""
ChatGPT用コードコピー ユーティリティ

指定したファイル・ファイルのリスト・ディレクトリ内の
Pythonコードをまとめてクリップボードへコピーする。

使用例:

    # ファイル1つ
    copy_code("app/routes/api.py")

    # 複数ファイル
    copy_code([
        "app/routes/api.py",
        "app/modules/getWeatherData.py",
        "app/modules/use_md_file.py",
    ])

    # ディレクトリ
    copy_code("app/modules")

    # ディレクトリ + ファイル
    copy_code([
        "app/modules",
        "app/routes/api.py",
    ])
"""

from pathlib import Path
import tkinter as tk
import ctypes
from ctypes import wintypes


# コピー対象にする拡張子
DEFAULT_EXTENSIONS = {
    ".py",
    ".html",
    ".css",
    ".js",
    ".json",
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
}


def _collect_files(
    target,
    extensions=None,
    exclude_dirs=None,
):
    """
    指定されたパスから対象ファイルを収集する。

    target:
        ファイル / ディレクトリ / それらのリスト

    戻り値:
        Pathのリスト
    """
    if extensions is None:
        extensions = DEFAULT_EXTENSIONS

    if exclude_dirs is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS

    # 単一パスならリスト化
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

        # ファイルの場合
        if path.is_file():
            if path.suffix.lower() in extensions:
                files.append(path)
            else:
                print(f"[SKIP] 対象外の拡張子: {path}")

        # ディレクトリの場合
        elif path.is_dir():
            for file_path in path.rglob("*"):
                if not file_path.is_file():
                    continue

                # 除外ディレクトリをチェック
                if any(
                    excluded in file_path.parts
                    for excluded in exclude_dirs
                ):
                    continue

                if file_path.suffix.lower() in extensions:
                    files.append(file_path)

    # 重複を削除してパス順に並べる
    files = sorted(set(files), key=lambda p: str(p).lower())

    return files


def _read_file(path):
    """
    ファイルを読み込む。
    UTF-8を基本とし、読み込めない場合はエラーを返す。
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


def _copy_to_clipboard(text):
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    # Windows APIの型を明示
    kernel32.GlobalAlloc.argtypes = [
        wintypes.UINT,
        ctypes.c_size_t,
    ]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL

    kernel32.GlobalLock.argtypes = [
        wintypes.HGLOBAL,
    ]
    kernel32.GlobalLock.restype = ctypes.c_void_p

    kernel32.GlobalUnlock.argtypes = [
        wintypes.HGLOBAL,
    ]
    kernel32.GlobalUnlock.restype = wintypes.BOOL

    kernel32.GlobalFree.argtypes = [
        wintypes.HGLOBAL,
    ]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL

    user32.OpenClipboard.argtypes = [
        wintypes.HWND,
    ]
    user32.OpenClipboard.restype = wintypes.BOOL

    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL

    user32.SetClipboardData.argtypes = [
        wintypes.UINT,
        wintypes.HANDLE,
    ]
    user32.SetClipboardData.restype = wintypes.HANDLE

    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL

    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    # UTF-16LE + 終端NULL
    data = text.encode("utf-16-le") + b"\x00\x00"

    h_global = kernel32.GlobalAlloc(
        GMEM_MOVEABLE,
        len(data)
    )

    if not h_global:
        raise ctypes.WinError(ctypes.get_last_error())

    try:
        ptr = kernel32.GlobalLock(h_global)

        if not ptr:
            raise ctypes.WinError(ctypes.get_last_error())

        try:
            ctypes.memmove(ptr, data, len(data))
        finally:
            kernel32.GlobalUnlock(h_global)

        if not user32.OpenClipboard(None):
            raise ctypes.WinError(ctypes.get_last_error())

        try:
            if not user32.EmptyClipboard():
                raise ctypes.WinError(ctypes.get_last_error())

            if not user32.SetClipboardData(
                CF_UNICODETEXT,
                h_global
            ):
                raise ctypes.WinError(ctypes.get_last_error())

            # SetClipboardData成功後はWindowsがメモリを所有する
            h_global = None

        finally:
            user32.CloseClipboard()

    finally:
        if h_global:
            kernel32.GlobalFree(h_global)


def copy_code(
    target,
    extensions=None,
    exclude_dirs=None,
):
    """
    ファイル・ファイルリスト・ディレクトリのコードを
    まとめてクリップボードへコピーする。

    Parameters
    ----------
    target:
        str / Path / list[str | Path]

        例:
            "app/routes/api.py"

        または:

            [
                "app/routes/api.py",
                "app/modules/getWeatherData.py",
            ]

        または:

            "app/modules"

    extensions:
        対象にする拡張子の集合。
        NoneならDEFAULT_EXTENSIONSを使用。

        例:
            {".py"}

    exclude_dirs:
        ディレクトリ検索時に除外するディレクトリ名の集合。

    Returns
    -------
    list[Path]
        コピーしたファイルの一覧。
    """
    files = _collect_files(
        target,
        extensions=extensions,
        exclude_dirs=exclude_dirs,
    )

    if not files:
        print("コピー対象のファイルがありません。")
        return []

    text = _build_text(files)

    _copy_to_clipboard(text)

    print()
    print("コピーしたファイル:")
    for path in files:
        print(f"  - {path}")

    print()
    print(f"合計 {len(files)} ファイル")

    return files
