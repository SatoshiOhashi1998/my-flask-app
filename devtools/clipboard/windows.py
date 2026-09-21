"""
Windows Clipboard操作
"""

import ctypes
from ctypes import wintypes


def copy_text(text: str) -> None:
    """
    Windows APIを使用してテキストをクリップボードへコピーする。
    """

    user32 = ctypes.WinDLL(
        "user32",
        use_last_error=True,
    )

    kernel32 = ctypes.WinDLL(
        "kernel32",
        use_last_error=True,
    )

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
        len(data),
    )

    if not h_global:
        raise ctypes.WinError(
            ctypes.get_last_error()
        )

    try:
        ptr = kernel32.GlobalLock(h_global)

        if not ptr:
            raise ctypes.WinError(
                ctypes.get_last_error()
            )

        try:
            ctypes.memmove(
                ptr,
                data,
                len(data),
            )

        finally:
            kernel32.GlobalUnlock(h_global)

        if not user32.OpenClipboard(None):
            raise ctypes.WinError(
                ctypes.get_last_error()
            )

        try:
            if not user32.EmptyClipboard():
                raise ctypes.WinError(
                    ctypes.get_last_error()
                )

            if not user32.SetClipboardData(
                CF_UNICODETEXT,
                h_global,
            ):
                raise ctypes.WinError(
                    ctypes.get_last_error()
                )

            # SetClipboardData成功後は
            # Windowsがメモリを所有する
            h_global = None

        finally:
            user32.CloseClipboard()

    finally:
        if h_global:
            kernel32.GlobalFree(h_global)
