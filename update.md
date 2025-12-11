# Wildcard 數據清理工作流程

## 概述
本文檔記錄了清理和優化 Wildcard 數據的標準流程，適用於移除重複項目和不適合 AI 繪圖的內容。

## 工作流程

### 步驟 1：查看目標分類的所有數據

```python
docker exec wildcard_web python -c "
import sys
sys.path.insert(0, '/app')
from webapp.models import db, Category, Wildcard
from app import app

with app.app_context():
    # 找到目標分類（例如：color）
    category = Category.query.filter_by(name='TARGET_CATEGORY_NAME').first()
    if not category:
        print('找不到分類')
        sys.exit(1)

    # 獲取所有 wildcards
    wildcards = Wildcard.query.filter_by(category_id=category.id).order_by(Wildcard.content).all()

    print(f'總共 {len(wildcards)} 個項目\n')

    # 顯示所有內容
    for w in wildcards:
        print(w.content)
"
```

### 步驟 2：識別需要刪除的項目

識別以下類型的問題項目：

#### 2.1 重複項目
- 大小寫不同但內容相同的項目
- 拼寫變體（如 `Gray` vs `Grey`）
- 保留策略：保留 ID 最小（最早創建）的項目

#### 2.2 容易誤解的項目
根據使用場景判斷，以下是 **不適合** 的內容類型：

**遊戲/軟件特定**：
- 遊戲術語（如 `Light Zerg Purple`）
- 軟件界面（如 `Blue Screen of Death`）
- 虛擬角色（如 `Cortana Blue`）
- 遊戲物品（如 `Lightsaber Blue/Green/Red`）

**品牌/商業特定**：
- 特定品牌（如 `Girl Scout Green`）
- 商業產品（如 `Comic Book Red`）
- 工業用途（如 `Construction Orange`）

**文化/地域特定**：
- 地名相關（如 `French Blue`, `Carolina Blue`）
- 節日特定（如 `Christmas Red`, `Halloween Orange`）
- 文化引用（如 `Dorian Gray`）

**過於具體/生僻**：
- 特定物品（如 `Hair Brown`, `Eye Brown`, `Fire Truck Red`）
- 生僻詞彙（如 `Gainsboro`, `Cetacean Blue`）
- 動植物名（如 `Goldfish Orange`, `Heliconia`）
- 過度描述（如 `Glowing Moon Yellow`, `Fun Yellow`）

**保留標準**：
✅ 通用、廣泛認知的顏色名稱
✅ 標準色彩術語（如 Web 標準色）
✅ 無歧義、易於 AI 理解
✅ 跨文化通用的描述

### 步驟 3：執行分析和刪除

```python
docker exec wildcard_web python -c "
import sys
sys.path.insert(0, '/app')
from webapp.models import db, Category, Wildcard
from app import app
from collections import defaultdict

with app.app_context():
    category = Category.query.filter_by(name='TARGET_CATEGORY_NAME').first()
    wildcards = Wildcard.query.filter_by(category_id=category.id).all()

    # 收集要刪除的項目 ID
    to_delete_ids = set()

    # 1. 檢查重複（不區分大小寫）
    print('=== 重複的項目（大小寫不同） ===')
    content_map = defaultdict(list)
    for w in wildcards:
        content_map[w.content.lower()].append(w)

    duplicates = []
    for lower_content, items in content_map.items():
        if len(items) > 1:
            print(f'{lower_content}: {[w.content for w in items]}')
            # 按 ID 排序，保留最小的
            items.sort(key=lambda x: x.id)
            to_delete_ids.update([w.id for w in items[1:]])

    print(f'\n找到 {len(to_delete_ids)} 個重複項目')

    # 2. 容易誤解的項目
    # 根據實際情況自定義關鍵詞列表
    problematic_keywords = [
        # 在此處添加需要過濾的關鍵詞
        # 'keyword1', 'keyword2', ...
    ]

    print('\n=== 容易誤解/過於具體的項目 ===')
    problematic_count = 0
    for w in wildcards:
        for keyword in problematic_keywords:
            if keyword.lower() in w.content.lower():
                print(f'  - {w.content}')
                to_delete_ids.add(w.id)
                problematic_count += 1
                break

    print(f'\n找到 {problematic_count} 個容易誤解的項目')
    print(f'\n總共需要刪除: {len(to_delete_ids)} 個項目')
    print(f'刪除後剩餘: {len(wildcards) - len(to_delete_ids)} 個項目')

    # 執行刪除（請先確認上述輸出無誤後再執行）
    # 取消下面的註釋以執行刪除
    # deleted_count = 0
    # deleted_names = []
    # for wid in to_delete_ids:
    #     w = db.session.get(Wildcard, wid)
    #     if w:
    #         deleted_names.append(w.content)
    #         db.session.delete(w)
    #         deleted_count += 1
    #
    # db.session.commit()
    # print(f'\n✓ 成功刪除 {deleted_count} 個項目')
"
```

### 步驟 4：更新 ComfyUI 文件

```python
docker exec wildcard_web python -c "
import sys
sys.path.insert(0, '/app')
from webapp.models import db, Category, Wildcard
from app import app, get_comfy_wildcard_path, get_comfy_filepath_for_category
from pathlib import Path

with app.app_context():
    # 獲取目標分類
    category = Category.query.filter_by(name='TARGET_CATEGORY_NAME').first()

    # 獲取 ComfyUI 路徑
    comfy_path_str = get_comfy_wildcard_path()
    if not comfy_path_str:
        print('ComfyUI wildcard 路徑未設定')
        sys.exit(1)

    # 獲取所有啟用的 wildcards
    wildcards = Wildcard.query.filter_by(
        category_id=category.id,
        is_active=True
    ).order_by(Wildcard.content).all()

    # 計算檔案路徑
    dir_path, filename = get_comfy_filepath_for_category(category, comfy_path_str)
    filepath = dir_path / filename

    print(f'更新檔案: {filepath}')
    print(f'項目數量: {len(wildcards)}')

    # 寫入檔案
    dir_path.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        for wildcard in wildcards:
            f.write(wildcard.content + '\n')

    print(f'✓ 成功更新 {filename}')
"
```

### 步驟 5：驗證結果

```bash
# 檢查文件行數
wc -l "D:/ComfyUI-aki-v1.6/ComfyUI/custom_nodes/comfyui-adaptiveprompts/wildcards/CATEGORY_FILE.txt"

# 查看前幾行確認內容
head -30 "D:/ComfyUI-aki-v1.6/ComfyUI/custom_nodes/comfyui-adaptiveprompts/wildcards/CATEGORY_FILE.txt"
```

## 實際案例：Universal-color 清理

### 執行日期
2025-12-08

### 清理結果
- **原始數量**：286 個顏色
- **刪除數量**：48 個項目
  - 重複項目：2 個
  - 遊戲/科技特定：8 個
  - 品牌/商業特定：5 個
  - 過於具體/生僻：33 個
- **最終保留**：238 個顏色（資料庫），224 個啟用顏色（ComfyUI）

### 刪除的項目列表
```
Advent Purple, Agreeable Gray, Asphalt Gray, Bear Brown, Birch,
Blue Screen of Death, Burlap Brown, Carolina Blue, Cement Gray,
Cetacean Blue, Christmas Green, Christmas Red, Cloud Burst Blue,
Columbia Green, Comic Book Red, Comic Book Yellow, Construction Orange,
Cortana Blue, Coyote Brown, Dark orange (重複), Dorian Gray,
Eucalyptus, Eye Brown, Fire Truck Red, French Blue, French Gray,
Fun Yellow, Gainsboro, Gainsboro Gray, Girl Scout Green,
Glowing Moon Yellow, Goldfish Orange, Green Screen Color,
Gun Smoke Gray, Hair Brown, Halloween Orange, Harvest Gold,
Heliconia, Ice Gray, King Blue, Knockout Pink, Legal Pad Yellow,
Legendary Gray, Light Zerg Purple, Light blue (重複),
Lightsaber Blue, Lightsaber Green, Lightsaber Red
```

### 保留的顏色特徵
- 標準色彩術語（如 `Azure`, `Crimson`, `Emerald Green`）
- 通用描述（如 `Baby Blue`, `Coral Pink`, `Sky Blue`）
- 材質顏色（如 `Gold`, `Silver`, `Bronze`, `Brass`）
- 自然顏色（如 `Lavender`, `Peach`, `Mint`）

## 注意事項

1. **執行前備份**：雖然可以從 ComfyUI 文件重新導入，但建議先備份資料庫
   ```bash
   docker exec wildcard_db pg_dump -U wildcard_user wildcard_db > backup_$(date +%Y%m%d).sql
   ```

2. **分步執行**：先執行分析步驟查看結果，確認無誤後再執行刪除

3. **檢查依賴**：確認沒有已保存的提示詞模板依賴這些要刪除的項目

4. **文檔更新**：每次清理後更新本文檔的「實際案例」部分

## 其他可能需要清理的分類

根據經驗，以下分類可能也需要類似的清理工作：

- **hairstyle**：可能包含過於具體的髮型名稱或角色特定髮型
- **clothing**：可能包含品牌特定服裝
- **artists**：可能包含重複或不適合的藝術家名稱
- **environment**：可能包含過於具體的地點描述

## 工具化建議

可以考慮創建一個通用的清理腳本 `clean_wildcards.py`：

```python
#!/usr/bin/env python3
"""
Wildcard 清理工具
用法: python clean_wildcards.py --category color --keywords keywords.txt
"""

import sys
import argparse
from collections import defaultdict
sys.path.insert(0, '/app')
from webapp.models import db, Category, Wildcard
from app import app, get_comfy_wildcard_path, get_comfy_filepath_for_category

def clean_category(category_name, problematic_keywords, dry_run=True):
    """清理指定分類的 wildcards"""
    with app.app_context():
        # ... 實現清理邏輯
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='清理 Wildcard 數據')
    parser.add_argument('--category', required=True, help='分類名稱')
    parser.add_argument('--keywords', help='問題關鍵詞文件路徑')
    parser.add_argument('--no-dry-run', action='store_true', help='實際執行刪除')

    args = parser.parse_args()
    # ... 執行清理
```

## 參考資料

- Web 標準顏色列表：https://www.w3.org/TR/css-color-3/
- AI 繪圖提示詞最佳實踐：使用通用、描述性的詞彙
- 分類路徑格式：使用連字符 `-` 分隔（如 `Universal-color.txt`）

---

最後更新：2025-12-08
維護者：Claude Code (AI Assistant)
