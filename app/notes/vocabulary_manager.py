import csv
import os
from typing import Any, Dict, List

from myutils.markdown.vault import Note
from myutils.markdown.note_processor import NoteParser
from myutils.markdown.utils import MarkdownUtils


# ==========================================
# 共通内部ヘルパー関数
# ==========================================

def _parse_lines_to_wordholic(
    lines: List[str],
    comment: str,
) -> List[Dict[str, str]]:
    """箇条書きリストの各行を解析し、Wordholic形式の辞書リストに変換"""
    rows = []

    for line in lines:
        parsed = MarkdownUtils.parse_vocabulary_line(line)

        if parsed:
            rows.append({
                "FrontText": parsed["word"],
                "BackText": parsed["meaning"],
                "Comment": comment,
                "FrontTextLanguage": "",
                "BackTextLanguage": "",
            })

    return rows


# ==========================================
# Wordholic / CSV 関連関数
# ==========================================

def convert_single_result_to_wordholic(
    single_result: Dict[str, Any],
) -> List[Dict[str, str]]:
    """単一見出しの解析結果をWordholic形式に変換"""
    comment = single_result.get("file_name", "")
    bullets = single_result.get("lists", {}).get("bullets", [])

    return _parse_lines_to_wordholic(
        bullets,
        comment,
    )


def convert_all_sub_headings_to_wordholic(
    all_results: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """全サブ見出しの解析結果をWordholic形式に変換"""
    all_rows = []

    for res in all_results:
        comment = res.get("heading", "")
        bullets = res.get("lists", {}).get("bullets", [])

        all_rows.extend(
            _parse_lines_to_wordholic(
                bullets,
                comment,
            )
        )

    return all_rows


def export_rows_to_csv(
    wordholic_rows: List[Dict[str, str]],
    output_csv_path: str,
) -> None:
    """Wordholic形式の辞書リストをCSVファイルへ出力"""
    if not wordholic_rows:
        print("⚠️ 出力するデータが見つかりませんでした。")
        return

    fieldnames = [
        "FrontText",
        "BackText",
        "Comment",
        "FrontTextLanguage",
        "BackTextLanguage",
    ]

    try:
        with open(
            output_csv_path,
            mode="w",
            encoding="utf-8",
            newline="",
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
            )
            writer.writeheader()
            writer.writerows(wordholic_rows)

        print(f"✅ CSV出力完了: {output_csv_path}")

    except Exception as e:
        print(f"❌ CSV出力エラー: {e}")


def export_english_vocabulary() -> None:
    """英単語のMarkdownからWordholic CSVを出力"""
    file_path = os.getenv("PATH_ENG")
    target_heading = os.getenv("TARGET_HEAD_ENG")

    if not file_path or not target_heading:
        print(
            "❌ エラー: PATH_ENG または TARGET_HEAD_ENG が設定されていません。"
        )
        return

    parser = NoteParser(Note(file_path))

    all_results = parser.extract_lists_from_all_sub_headings(
        target_heading
    )

    all_rows = convert_all_sub_headings_to_wordholic(
        all_results
    )

    export_rows_to_csv(
        all_rows,
        "output_all.csv",
    )


def export_single_vocabulary() -> None:
    """単一語彙のMarkdownからWordholic CSVを出力"""
    file_path = os.getenv("PATH_VOCAB")
    target_heading = os.getenv("TARGET_HEAD_VOCAB")

    if not file_path or not target_heading:
        print(
            "❌ エラー: PATH_VOCAB または TARGET_HEAD_VOCAB が設定されていません。"
        )
        return

    parser = NoteParser(Note(file_path))

    single_result = parser.extract_lists_from_heading(
        target_heading
    )

    single_rows = convert_single_result_to_wordholic(
        single_result
    )

    export_rows_to_csv(
        single_rows,
        "output_single.csv",
    )
