#!/usr/bin/env python3
"""
清理 environment 分類中不適合作為背景/地點的項目
"""
import os
import sys

# 添加父目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Wildcard, Category

# 要刪除的非地點項目（不適合作為一般背景/地點）
NON_LOCATION_ITEMS = [
    # 運動設施（太具體）
    'wrestling ring',
    'skating rink',
    'soccer field',

    # 特定商店（以物品為導向）
    'weapon shop',
    'flower shop',
    'bakery',
    'ramen shop',

    # 過於具體的房間功能
    'changing room',
    'storage room',
    'infirmary',

    # 娛樂設備（太具體）
    'roller coaster',
    'ferris wheel',

    # 基礎設施細節（太具體）
    'crosswalk',
    'sidewalk',
    'phone booth',

    # 農業/園藝具體項目
    'rose garden',
    'flower field',
    'wheat field',
    'rice paddy',

    # 其他過於具體的項目
    'rope bridge',
    'wooden bridge',
    'stilt house',
    'gazebo',
    'well',
]

def cleanup_environment_nonlocations():
    """清理 environment 中的非地點項目"""

    with app.app_context():
        # 找到 environment 分類
        env_category = Category.query.filter_by(name='environment').first()
        if not env_category:
            print("錯誤：找不到 environment 分類")
            return

        print(f"正在清理分類：{env_category.name} (ID: {env_category.id})")
        print(f"目標：移除不適合作為背景/地點的項目")
        print("=" * 80)

        deleted_count = 0
        not_found = []

        for item_name in NON_LOCATION_ITEMS:
            # 查找項目（只在 environment 分類中，且為 active）
            wildcard = Wildcard.query.filter(
                Wildcard.category_id == env_category.id,
                Wildcard.content == item_name,
                Wildcard.is_active == True
            ).first()

            if wildcard:
                print(f"✓ 刪除: {wildcard.content}")
                db.session.delete(wildcard)
                deleted_count += 1
            else:
                not_found.append(item_name)

        # 提交更改
        db.session.commit()

        print("=" * 80)
        print(f"\n清理完成！")
        print(f"成功刪除: {deleted_count} 個項目")

        if not_found:
            print(f"\n未找到的項目 ({len(not_found)}):")
            for item in not_found:
                print(f"  - {item}")

        # 顯示當前狀態
        remaining = Wildcard.query.filter(
            Wildcard.category_id == env_category.id,
            Wildcard.is_active == True
        ).count()
        print(f"\n剩餘活躍項目: {remaining}")

if __name__ == '__main__':
    cleanup_environment_nonlocations()
