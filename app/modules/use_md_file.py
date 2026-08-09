import csv
import os
from datetime import datetime
from myutils.markdown.api import (
    extract_lists_from_heading,
    extract_lists_from_all_sub_headings,
    parse_vocabulary_line
)
from myutils.markdown.create_dailynote import batch_create_dailies_from_file

def convert_single_result_to_wordholic(single_result):
    """
    extract_lists_from_heading のデータ用:
    single_result['file_name'] を Comment に挿入する
    """
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
    """
    extract_lists_from_all_sub_headings のデータ用:
    各結果の res['heading'] を Comment に挿入する
    """
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
    """
    変換済みの行データをWordHolic用のCSVとして保存する
    """
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
