import csv
import os
from datetime import datetime
from myutils.markdown.parser_api import (
    extract_lists_from_heading,
    extract_lists_from_all_sub_headings,
    parse_vocabulary_line
)
from myutils.markdown.note_generator import batch_create_dailies_from_file

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
