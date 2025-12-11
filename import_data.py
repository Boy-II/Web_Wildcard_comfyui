#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
獨立的資料匯入腳本
可在命令列直接執行，無需啟動 Web 伺服器
"""

import os
import sys
import re
import zipfile
from pathlib import Path
from app import app
from webapp.models import db, Category, Wildcard, ImportHistory


def clean_line(line):
    """清理每一行資料"""
    # 移除行號（格式如 "1→" 或 "  123→"）
    line = re.sub(r'^\s*\d+→', '', line)
    return line.strip()


def categorize_filename(filename):
    """根據檔名判斷類別"""
    filename_lower = filename.lower()
    name_without_ext = os.path.splitext(filename_lower)[0]

    category_keywords = {
        'characters': ['actor', 'actress', 'character', 'person', 'celebrity'],
        'styles': ['style', 'art', 'aesthetic', 'theme'],
        'adjectives': ['adj-', 'adjective'],
        'technical': ['3d', 'render', 'engine', 'camera'],
        'scenes': ['scene', 'background', 'environment', 'location'],
        'objects': ['object', 'item', 'prop'],
        'colors': ['color', 'colour'],
    }

    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in name_without_ext:
                return category

    return 'misc'


def import_txt_file(file_path, category_map):
    """匯入單一 TXT 檔案"""
    filename = os.path.basename(file_path)
    category_name = categorize_filename(filename)

    # 獲取類別
    category = category_map.get(category_name)
    if not category:
        category = category_map.get('misc')

    imported = 0
    skipped = 0

    print(f"  處理: {filename} -> {category.display_name}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                content = clean_line(line)
                if not content:
                    continue

                # 檢查是否已存在
                existing = Wildcard.query.filter_by(
                    category_id=category.id,
                    content=content
                ).first()

                if existing:
                    skipped += 1
                    continue

                # 新增
                wildcard = Wildcard(
                    content=content,
                    category_id=category.id,
                    source_file=filename
                )
                db.session.add(wildcard)
                imported += 1

        db.session.commit()
        print(f"    ✓ 匯入: {imported}, 跳過: {skipped}")
        return imported, skipped, None

    except Exception as e:
        db.session.rollback()
        error_msg = f"錯誤: {str(e)}"
        print(f"    ✗ {error_msg}")
        return 0, 0, error_msg


def import_from_directory(directory_path):
    """從目錄匯入所有 TXT 檔案"""
    dir_path = Path(directory_path)

    if not dir_path.exists():
        print(f"錯誤: 目錄不存在 {directory_path}")
        return

    # 獲取所有類別
    categories = Category.query.all()
    category_map = {cat.name: cat for cat in categories}

    txt_files = list(dir_path.glob('*.txt'))
    print(f"\n找到 {len(txt_files)} 個 TXT 檔案\n")

    total_imported = 0
    total_skipped = 0
    errors = []

    for txt_file in txt_files:
        imported, skipped, error = import_txt_file(str(txt_file), category_map)
        total_imported += imported
        total_skipped += skipped

        if error:
            errors.append(f"{txt_file.name}: {error}")

    # 記錄匯入歷史
    history = ImportHistory(
        filename=directory_path,
        file_type='directory',
        items_imported=total_imported,
        items_skipped=total_skipped,
        status='success' if not errors else 'partial',
        error_message='; '.join(errors) if errors else None
    )
    db.session.add(history)
    db.session.commit()

    print(f"\n{'='*60}")
    print(f"匯入完成!")
    print(f"總計匯入: {total_imported} 個項目")
    print(f"跳過重複: {total_skipped} 個項目")

    if errors:
        print(f"\n發生 {len(errors)} 個錯誤:")
        for error in errors:
            print(f"  - {error}")

    print(f"{'='*60}\n")


def import_from_zip(zip_path):
    """從 ZIP 檔案匯入"""
    if not os.path.exists(zip_path):
        print(f"錯誤: ZIP 檔案不存在 {zip_path}")
        return

    # 獲取所有類別
    categories = Category.query.all()
    category_map = {cat.name: cat for cat in categories}

    total_imported = 0
    total_skipped = 0
    errors = []

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            txt_files = [f for f in zip_ref.namelist() if f.endswith('.txt')]
            print(f"\n在 ZIP 中找到 {len(txt_files)} 個 TXT 檔案\n")

            for txt_file in txt_files:
                filename = os.path.basename(txt_file)
                category_name = categorize_filename(filename)
                category = category_map.get(category_name, category_map.get('misc'))

                print(f"  處理: {filename} -> {category.display_name}")

                imported = 0
                skipped = 0

                try:
                    with zip_ref.open(txt_file) as f:
                        content = f.read().decode('utf-8')
                        for line in content.split('\n'):
                            cleaned = clean_line(line)
                            if not cleaned:
                                continue

                            existing = Wildcard.query.filter_by(
                                category_id=category.id,
                                content=cleaned
                            ).first()

                            if existing:
                                skipped += 1
                                continue

                            wildcard = Wildcard(
                                content=cleaned,
                                category_id=category.id,
                                source_file=filename
                            )
                            db.session.add(wildcard)
                            imported += 1

                    db.session.commit()
                    total_imported += imported
                    total_skipped += skipped
                    print(f"    ✓ 匯入: {imported}, 跳過: {skipped}")

                except Exception as e:
                    db.session.rollback()
                    error_msg = f"{filename}: {str(e)}"
                    errors.append(error_msg)
                    print(f"    ✗ 錯誤: {str(e)}")

    except Exception as e:
        print(f"錯誤: 無法讀取 ZIP 檔案: {str(e)}")
        return

    # 記錄匯入歷史
    history = ImportHistory(
        filename=os.path.basename(zip_path),
        file_type='zip',
        items_imported=total_imported,
        items_skipped=total_skipped,
        status='success' if not errors else 'partial',
        error_message='; '.join(errors[:10]) if errors else None  # 只記錄前10個錯誤
    )
    db.session.add(history)
    db.session.commit()

    print(f"\n{'='*60}")
    print(f"匯入完成!")
    print(f"總計匯入: {total_imported} 個項目")
    print(f"跳過重複: {total_skipped} 個項目")

    if errors:
        print(f"\n發生 {len(errors)} 個錯誤")

    print(f"{'='*60}\n")


def main():
    """主程式"""
    print("\n" + "="*60)
    print("Wildcard 資料匯入工具")
    print("="*60 + "\n")

    if len(sys.argv) < 2:
        print("用法:")
        print(f"  python {sys.argv[0]} <目錄路徑或ZIP檔案>")
        print("\n範例:")
        print(f"  python {sys.argv[0]} sample_file/wildcards")
        print(f"  python {sys.argv[0]} sample_file/ccsWildcards_v11.zip")
        print()
        sys.exit(1)

    source_path = sys.argv[1]

    with app.app_context():
        # 確保資料表已建立
        db.create_all()

        # 檢查類別是否存在，如果不存在則建立
        if Category.query.count() == 0:
            print("初始化類別...")
            from app import init_categories
            init_categories()
            print("類別建立完成\n")

        # 判斷是目錄還是 ZIP 檔案
        if os.path.isdir(source_path):
            import_from_directory(source_path)
        elif source_path.endswith('.zip'):
            import_from_zip(source_path)
        else:
            print(f"錯誤: 不支援的檔案類型: {source_path}")
            sys.exit(1)


if __name__ == '__main__':
    main()
