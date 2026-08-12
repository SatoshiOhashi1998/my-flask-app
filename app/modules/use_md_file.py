import csv
from datetime import datetime, timedelta
import os
from myutils.markdown.headings import (
    find_headings_by_tag_in_directory,
    get_content_by_heading,  # 追加: 本文取得用
)
from myutils.markdown.lists import (
    extract_lists_from_all_sub_headings,
    extract_lists_from_heading,
    extract_nested_lists_from_content,  # 追加: ネストリスト抽出用
)
from myutils.markdown.note_generator import (
    batch_create_dailies_from_file,
    create_weekly_note,
)
from myutils.markdown.utils import parse_vocabulary_line

def convert_single_result_to_wordholic(single_result):
    comment = single_result['file_name']
    wordholic_rows = []
    
    for line in single_result['lists'].get('bullets', []):
        parsed = parse_vocabulary_line(line)
        if parsed:
            wordholic_rows.append({
                "FrontText": parsed["word"],
                "BackText": parsed["meaning"],
                "Comment": comment,
                "FrontTextLanguage": "",
                "BackTextLanguage": ""
            })
            
    return wordholic_rows

def convert_all_sub_headings_to_wordholic(all_results):
    all_wordholic_rows = []
    
    for res in all_results:
        comment = res['heading']
        for line in res['lists'].get('bullets', []):
            parsed = parse_vocabulary_line(line)
            if parsed:
                all_wordholic_rows.append({
                    "FrontText": parsed["word"],
                    "BackText": parsed["meaning"],
                    "Comment": comment,
                    "FrontTextLanguage": "",
                    "BackTextLanguage": ""
                })
                
    return all_wordholic_rows

def export_rows_to_csv(wordholic_rows, output_csv_path):
    if not wordholic_rows:
        print("出力するデータが見つかりませんでした。")
        return

    fieldnames = ["FrontText", "BackText", "Comment", "FrontTextLanguage", "BackTextLanguage"]
    
    try:
        with open(output_csv_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(wordholic_rows)
            
        print(f"CSV出力完了: {output_csv_path}")
    except Exception as e:
        print(f"CSV出力エラー: {e}")

def create_dailynote():
    target_path = os.getenv('DAILY_NOTE_DIR')
    template_path = os.getenv('DAILY_NOTE_TEMPLATE')
    start_date = datetime.now()
    batch_create_dailies_from_file(target_path, start_date, 7, template_path)

def create_next_weekly_note():
    output_dir = os.getenv('WEEKLY_NOTE_DIR')
    template_path = os.getenv('WEEKLY_NOTE_TEMPLATE')
    plan_dir = os.getenv('PLAN_NOTE_DIR')
    
    today = datetime.now()
    next_week_date = today + timedelta(days=7)
    
    create_weekly_note(
        output_dir=output_dir,
        target_date=next_week_date,
        template_path=template_path,
        plan_dir=plan_dir,
        start_of_week="monday"
    )

def export_english_vocabulary():
    file_path = os.getenv("PATH_ENG")
    target_heading = os.getenv("TARGET_HEAD_ENG")
    all_results = extract_lists_from_all_sub_headings(file_path, target_heading)
    all_rows = convert_all_sub_headings_to_wordholic(all_results)
    export_rows_to_csv(all_rows, "output_all.csv")

def export_single_vocabulary():
    file_path = os.getenv("PATH_VOCAB")
    target_heading = os.getenv("TARGET_HEAD_VOCAB")
    single_result = extract_lists_from_heading(file_path, target_heading)
    single_rows = convert_single_result_to_wordholic(single_result)
    export_rows_to_csv(single_rows, "output_single.csv")

def test_md():
    # print("================test_md===============")
    # response = find_headings_by_tag_in_directory(r"C:\Users\user\OneDrive\Desktop\Obsidian\Exports", "test")
    # print(response)
    print_nested_lists_from_heading(r"C:\Users\user\OneDrive\Desktop\Obsidian\Daily Notes\2026-08-13.md", "Tasks")

def print_nested_lists_from_heading(
    file_path: str, target_heading: str
) -> dict | None:
    """指定したファイルの見出しから本文を取得し、インデント付きリストを抽出・表示する。

    Args:
        file_path (str): Markdownファイルのパス
        target_heading (str): 対象の見出しテキスト

    Returns:
        dict | None: 抽出されたリスト情報。見出しが存在しない場合は None
    """
    # 1. 見出しから本文を取得
    content = get_content_by_heading(file_path, target_heading)
    if content is None:
        print(f"見出し '{target_heading}' が見つかりませんでした。")
        return None

    # 2. 本文からネストされたリストを抽出
    nested_lists = extract_nested_lists_from_content(content)

    # 3. 画面に表示
    print(f"=== [{target_heading}] のリスト一覧 ===")

    if nested_lists.get("bullets"):
        print("\n【箇条書き】")
        for item in nested_lists["bullets"]:
            indent_str = " " * item["indent"]
            print(f"{indent_str}- {item['text']}")

    if nested_lists.get("tasks"):
        print("\n【タスク】")
        # 表示用のループ処理部分
        for item in nested_lists["tasks"]:
            # indentの数だけそのままスペースを出力
            indent_str = " " * item["indent"]
            status = "[x]" if item["completed"] else "[ ]"
            print(f"{indent_str}- {status} {item['text']}")

    return nested_lists

