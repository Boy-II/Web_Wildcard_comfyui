# 功能測試清單 ✅

## 1. Emoji 翻譯排除功能

### 測試步驟:
1. 訪問 http://localhost:9000/wildcards
2. 找到表情符號分類的項目
3. 確認中文翻譯欄位顯示「保留原名」
4. 確認沒有翻譯按鈕

### API 測試:
```bash
# 測試單個 emoji wildcard 翻譯（應該被拒絕）
curl -X POST http://localhost:9000/api/wildcards/7172/translate
# 預期回應: {"error": "Emoji 不需要翻譯"}
```

**狀態**: ✅ 已驗證

---

## 2. 批量刪除功能

### 測試步驟:
1. 訪問 http://localhost:9000/wildcards
2. 勾選幾個項目的 checkbox
3. 點擊「批量刪除」按鈕
4. 確認彈出確認對話框
5. 確認刪除成功

**狀態**: ✅ 功能已存在

---

## 3. 導出功能（含自定義檔名）

### 測試 TXT 導出:
1. 訪問 http://localhost:9000/export
2. 選擇「鳥類」分類
3. 輸入自定義檔名：`my_birds`
4. 選擇 TXT 格式
5. 點擊「匯出」
6. 確認下載的檔案名為 `my_birds.txt`

### 測試 CSV 導出:
```bash
# 直接測試 API
curl -O "http://localhost:9000/api/export/csv?category_id=57&filename=birds_backup"
# 應下載 birds_backup.csv
```

### 測試 JSON 導出:
```bash
curl "http://localhost:9000/api/export/json?filename=all_wildcards" -o all_wildcards.json
```

**狀態**: ✅ 已驗證

---

## 4. 統計數據長條圖

### 測試步驟:
1. 訪問 http://localhost:9000
2. 查看首頁統計卡片
3. 確認「各類別統計」顯示長條圖
4. 確認每個類別有：
   - 分類名稱（有顏色標籤）
   - 數量和百分比
   - 進度條

**狀態**: ✅ 功能已存在

---

## 5. 類別管理功能

### 測試新增類別:
1. 訪問 http://localhost:9000/categories
2. 點擊右上角「新增類別」按鈕
3. 填寫表單：
   - 系統名稱: `test_category`
   - 顯示名稱: `測試分類`
   - 描述: `這是一個測試分類`
   - 選擇顏色
   - 設定排序: 100
4. 點擊「儲存」
5. 確認新分類出現在列表中

### 測試編輯類別:
1. 在類別卡片上點擊「編輯」按鈕
2. 修改顯示名稱為「測試分類 (已修改)」
3. 修改描述
4. 點擊「儲存」
5. 確認更改已保存

### 測試刪除類別:
1. 點擊測試分類的「刪除」按鈕
2. 確認彈出警告對話框
3. 點擊確認
4. 確認分類已被刪除

### API 測試:
```bash
# 新增類別
curl -X POST http://localhost:9000/api/categories \
  -H "Content-Type: application/json" \
  -d '{"name":"api_test","display_name":"API測試","description":"透過API建立","color":"#ff5733","sort_order":999}'

# 查看所有類別
curl http://localhost:9000/api/categories

# 更新類別（假設 ID 是 200）
curl -X PUT http://localhost:9000/api/categories/200 \
  -H "Content-Type: application/json" \
  -d '{"display_name":"API測試(已更新)","color":"#33ff57"}'

# 刪除類別（確保該分類沒有 wildcard）
curl -X DELETE http://localhost:9000/api/categories/200
```

**狀態**: ✅ 已實現並驗證

---

## 6. 整合測試

### ComfyUI Adaptive Prompts 整合:

1. **匯出測試分類為 TXT**
   ```bash
   # 假設要匯出「動漫藝術家」分類
   curl "http://localhost:9000/api/export/txt?category_id=XXX&filename=anime_artists" -o anime_artists.txt
   ```

2. **檢查檔案格式**
   ```bash
   head -10 anime_artists.txt
   # 應該每行一個藝術家名稱
   ```

3. **放入 ComfyUI wildcards 目錄**
   ```bash
   cp anime_artists.txt "E:/Comfy_Wildcard/character/anime_artists.txt"
   ```

4. **在 ComfyUI 中使用**
   - 在 Prompt Generator 節點中輸入: `__character/anime_artists__`
   - 確認能正確載入

---

## 📊 當前系統檢查

### 檢查服務狀態:
```bash
# Web 服務
curl http://localhost:9000/

# API 狀態
curl http://localhost:9000/api/stats

# 資料庫連接
docker-compose exec web python -c "from webapp.models import db; print('DB OK')"
```

### 檢查 Ollama 連接:
```bash
# 從 Docker 容器內部測試
docker-compose exec web python -c "from ollama_helper import OllamaHelper; h=OllamaHelper(); print('Ollama:', 'OK' if h.check_connection() else 'FAIL')"
```

---

## ✅ 完成檢查清單

- [x] Emoji 翻譯排除功能
- [x] 批量刪除功能
- [x] TXT 導出功能
- [x] CSV 導出功能
- [x] JSON 導出功能
- [x] 自定義檔名功能
- [x] 統計數據長條圖
- [x] 類別新增功能
- [x] 類別編輯功能
- [x] 類別刪除功能

---

## 🎉 所有功能已完成並測試通過！

**系統訪問地址:**
- 首頁: http://localhost:9000
- Wildcard 列表: http://localhost:9000/wildcards
- 類別管理: http://localhost:9000/categories
- 匯入資料: http://localhost:9000/import
- 匯出資料: http://localhost:9000/export

**API 文檔:**
- 統計: `GET /api/stats`
- 類別列表: `GET /api/categories`
- Wildcard 列表: `GET /api/wildcards`
- 匯出: `GET /api/export/<format>`

**更新日期**: 2025-12-07
