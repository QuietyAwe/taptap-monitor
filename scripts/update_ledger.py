import csv
import os
import sys
import argparse

def update_csv():
    parser = argparse.ArgumentParser(description="Update TapTap Monitor Ledger")
    parser.add_argument("--create_time", required=True)
    parser.add_argument("--source_type", default="TapTap")
    parser.add_argument("--content", required=True)
    parser.add_argument("--content_summary", required=True)
    parser.add_argument("--severity", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--ai_suggestion", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--url", required=True)

    args = parser.parse_args()
    
    file_path = 'data/monitor_log.csv'
    header = ['create_time', 'source_type', 'content', 'content_summary', 'severity', 'category', 'ai_suggestion', 'author', 'url']
    
    # 数据预处理：强制去除内容中的换行符，防止破坏 CSV 结构
    def clean_text(text):
        if not text: return ""
        return str(text).replace('\n', ' ').replace('\r', ' ').strip()

    row = [
        args.create_time,
        args.source_type,
        clean_text(args.content),
        clean_text(args.content_summary),
        args.severity,
        args.category,
        clean_text(args.ai_suggestion),
        args.author,
        args.url
    ]

    file_exists = os.path.isfile(file_path)

    # 使用 utf-8-sig 确保 Excel 打开不乱码
    with open(file_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL) # 强制给所有字段加双引号
        if not file_exists:
            writer.writerow(header)
        writer.writerow(row)

if __name__ == "__main__":
    update_csv()