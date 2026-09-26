"""
ファイル構成を取得・クリップボードへコピーするユーティリティ。
"""

from pathlib import Path

from devtools.clipboard import copy_text


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


def _get_children(path, exclude_dirs):
    """
    ディレクトリ直下の対象を取得する。

    ディレクトリを先に並べ、その後ファイルを並べる。
    """

    children = []

    for child in path.iterdir():

        if child.is_dir():
            if child.name in exclude_dirs:
                continue

            children.append(child)

        elif child.is_file():
            children.append(child)

    return sorted(
        children,
        key=lambda p: (
            not p.is_dir(),
            p.name.lower(),
        ),
    )


def _build_tree(
    path,
    prefix="",
    exclude_dirs=None,
):
    """
    tree形式の文字列を再帰的に生成する。
    """

    if exclude_dirs is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS

    lines = []

    children = _get_children(
        path,
        exclude_dirs,
    )

    for index, child in enumerate(children):

        is_last = index == len(children) - 1

        branch = "└── " if is_last else "├── "

        lines.append(
            f"{prefix}{branch}{child.name}"
        )

        if child.is_dir():

            next_prefix = (
                f"{prefix}    "
                if is_last
                else f"{prefix}│   "
            )

            lines.extend(
                _build_tree(
                    child,
                    prefix=next_prefix,
                    exclude_dirs=exclude_dirs,
                )
            )

    return lines


def generate_file_tree(
    target,
    exclude_dirs=None,
    recursive=True,
):
    """
    指定したディレクトリのファイル構成を
    tree形式の文字列として生成する。

    Parameters
    ----------
    target:
        対象ディレクトリ。

    exclude_dirs:
        除外するディレクトリ名の集合。

    recursive:
        Falseの場合、指定ディレクトリの直下のみ表示する。

    Returns
    -------
    str
        ファイル構成。
    """

    path = Path(target)

    if not path.exists():
        raise FileNotFoundError(
            f"指定されたパスが存在しません: {path}"
        )

    if not path.is_dir():
        raise NotADirectoryError(
            f"指定されたパスはディレクトリではありません: {path}"
        )

    if exclude_dirs is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS

    lines = [f"{path.name}/"]

    children = _get_children(
        path,
        exclude_dirs,
    )

    for index, child in enumerate(children):

        is_last = index == len(children) - 1

        branch = "└── " if is_last else "├── "

        lines.append(
            f"{branch}{child.name}"
            + ("/" if child.is_dir() else "")
        )

        if child.is_dir() and recursive:

            prefix = (
                "    "
                if is_last
                else "│   "
            )

            lines.extend(
                _build_tree(
                    child,
                    prefix=prefix,
                    exclude_dirs=exclude_dirs,
                )
            )

    return "\n".join(lines)


def copy_file_tree(
    target,
    exclude_dirs=None,
    recursive=True,
):
    """
    指定されたディレクトリのファイル構成を
    クリップボードへコピーする。

    Returns
    -------
    str
        コピーしたファイル構成。
    """

    tree = generate_file_tree(
        target,
        exclude_dirs=exclude_dirs,
        recursive=recursive,
    )

    copy_text(tree)

    return tree
