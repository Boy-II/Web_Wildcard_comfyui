# Wildcard 管理系統 - 使用指南

## 🎯 新功能概覽

### ✨ 多層級分類系統
- **16個主分類**，包含**80+子分類**
- 支援 2-3 層嵌套分類
- 自動智能分類匹配

### 🤖 AI 增強功能
- **自動翻譯**：使用 Ollama qwen2.5:7b 將英文內容翻譯為繁體中文
- **AI 分類協助**：讓 AI 分析內容並建議最佳分類
- **批量處理**：支援大量檔案的自動化處理

### 📊 分類架構

```
1. 人物 (People)
   ├── 藝術家 (9個子分類：動漫、插畫、攝影師、導演等)
   └── 角色/名人 (5個子分類：演員、女演員、虛構角色等)

2. 身體 (Body)
   ├── 姿勢 (8個子分類：基本姿勢、手臂、坐姿、站姿等)
   ├── 身體部位 (4個子分類)
   └── 手勢、表情、體型特徵

3. 服飾 (Clothing)
   ├── 全身服裝 (6個子分類：洋裝、制服、泳裝、婚紗等)
   ├── 配件 (4個子分類：帽子、眼鏡、珠寶、包包)
   └── 上衣、下裝、內衣、襪類、鞋類

4. 生物 (Creatures)
   ├── 動物 (4個子分類：哺乳類、鳥類、爬蟲類、昆蟲)
   ├── 水生生物 (魚類、海洋生物)
   └── 幻想生物 (龍、天使、惡魔、神話生物)

5. 場景/環境 (Scenes)
   ├── 背景 (室內、室外、自然、城市)
   └── 地點、環境設定、時代、天氣

6. 藝術風格 (Art & Style)
   ├── 藝術運動 (5個子分類)
   ├── 美學風格 (5個子分類：動漫、寫實、卡通等)
   └── 主題風格 (科幻、奇幻、恐怖、浪漫)

7. 技術 (Technical)
   ├── 3D 引擎、渲染、燈光
   ├── 鏡頭/構圖 (視角、鏡頭類型、取景)
   └── 後製效果 (濾鏡、色差、品牌預設)

8. 物件/道具 (Objects)
   ├── 自然元素 (植物、花卉、石頭)
   └── 食物、交通工具、日常物品、武器、家具

9-16. 形容詞、顏色、構圖、音樂/音效、文化/地域、
      流行文化、表情符號、其他
```

---

## 🚀 快速開始

### 前置準備

1. **安裝 Ollama** (可選，用於 AI 功能)
   ```bash
   # 下載並安裝 Ollama
   # https://ollama.com/download

   # 拉取 qwen2.5:7b 模型
   ollama pull qwen2.5:7b

   # 啟動 Ollama 服務
   ollama serve
   ```

2. **啟動應用**
   ```bash
   # 使用 Docker Compose (推薦)
   docker-compose up -d

   # 或本地運行
   pip install -r requirements.txt
   python app.py
   ```

3. **訪問應用**
   - Web 介面: http://localhost:9000 (Docker) 或 http://localhost:5000 (本地)

---

## 📥 資料匯入

### 方法 1: 使用批量匯入腳本（推薦）

```bash
# 基本匯入（僅自動分類）
python bulk_import.py "E:\Wildcard"

# 啟用 AI 翻譯
python bulk_import.py "E:\Wildcard" --translate

# 啟用 AI 分類協助
python bulk_import.py "E:\Wildcard" --ai-classify

# 同時啟用翻譯和 AI 分類
python bulk_import.py "E:\Wildcard" --translate --ai-classify

# 測試模式（只顯示會匯入哪些檔案）
python bulk_import.py "E:\Wildcard" --test

# 不遞迴搜尋子目錄
python bulk_import.py "E:\Wildcard" --no-recursive
```

### 方法 2: 使用 Web 介面

1. 訪問 http://localhost:9000/import
2. 輸入目錄路徑：`E:\Wildcard`
3. 選擇選項：
   - ☑️ 遞迴搜尋子目錄
   - ☑️ 使用 AI 翻譯
   - ☑️ 使用 AI 分類
4. 點擊「開始匯入」

### 方法 3: 使用 API

```bash
curl -X POST http://localhost:9000/api/import/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "E:\\Wildcard",
    "recursive": true,
    "use_ollama_translate": true,
    "use_ollama_classify": true
  }'
```

---

## ⚙️ 匯入選項說明

### 🔄 遞迴搜尋 (recursive)
- **啟用**: 搜尋所有子目錄中的 .txt 檔案
- **停用**: 只搜尋指定目錄本身的 .txt 檔案
- 預設：**啟用**

### 🌐 AI 翻譯 (use_ollama_translate)
- 將英文 wildcard 自動翻譯為繁體中文
- 需要 Ollama 服務運行
- 會顯著增加處理時間（每條 ~0.5-2秒）
- 預設：**停用**

### 🤖 AI 分類 (use_ollama_classify)
- 使用 AI 分析內容並建議最佳分類
- 比規則式分類更智能、更準確
- 需要 Ollama 服務運行
- 會顯著增加處理時間（每條 ~0.5-2秒）
- 預設：**停用**

---

## 📊 處理時間估算

基於 3,245 個檔案的數據：

| 模式 | 預估時間 | 說明 |
|-----|---------|------|
| 僅自動分類 | ~5-10 分鐘 | 最快，使用規則式分類 |
| + AI 分類 | ~30-60 分鐘 | AI 分析每個檔案 |
| + AI 翻譯 | ~1-2 小時 | 翻譯每條 wildcard |
| AI 分類 + 翻譯 | ~2-3 小時 | 完整 AI 處理 |

💡 **建議**：
- 首次匯入：使用「僅自動分類」快速建立資料庫
- 後續優化：針對特定分類使用 AI 功能精修

---

## 🔍 查看和管理資料

### Web 介面

1. **首頁 Dashboard** - `/`
   - 查看統計資訊
   - 各分類數據分布

2. **分類管理** - `/categories`
   - 查看完整分類樹
   - 新增/編輯/刪除分類

3. **Wildcard 瀏覽** - `/wildcards`
   - 瀏覽所有 wildcard
   - 按分類篩選
   - 搜尋內容
   - 查看中文翻譯

4. **匯出資料** - `/export`
   - 匯出為 TXT/JSON/CSV
   - 按分類匯出

### API 端點

```bash
# 獲取統計資訊
GET /api/stats

# 獲取分類樹
GET /api/categories?tree=true

# 獲取扁平分類列表
GET /api/categories

# 獲取 wildcards (分頁)
GET /api/wildcards?page=1&per_page=50

# 按分類篩選
GET /api/wildcards?category_id=123

# 搜尋
GET /api/wildcards?search=anime

# 匯出
GET /api/export/json?category_id=123
```

---

## 🎨 自動分類規則

系統使用智能關鍵字匹配，從最具體到最一般：

### 檔案名稱模式範例

```
artist-anime.txt        → People > Artists > Anime Artists
pose.txt                → Body > Poses
legwear.txt             → Clothing > Legwear
dragon.txt              → Creatures > Fantasy > Dragons
background-indoor.txt   → Scenes > Backgrounds > Indoor
color.txt               → Colors > Basic Colors
3dengines.txt           → Technical > 3D Engines
food.txt                → Objects > Food
adjectives.txt          → Adjectives > Descriptive
```

---

## ❓ 常見問題

### Q: 如何確認 Ollama 是否正常運行？

```bash
# 檢查 Ollama 服務
curl http://localhost:11434/api/tags

# 測試翻譯
python ollama_helper.py
```

### Q: 匯入時出現「無法連接到 Ollama」怎麼辦？

1. 確認 Ollama 服務已啟動：`ollama serve`
2. 確認模型已下載：`ollama list`
3. 如未下載：`ollama pull qwen2.5:7b`
4. 或選擇不使用 AI 功能繼續匯入

### Q: 如何修改某個 wildcard 的分類？

方法 1: Web 介面
- 訪問 `/wildcards`
- 找到要修改的項目
- 點擊「編輯」
- 選擇新分類

方法 2: API
```bash
curl -X PUT http://localhost:9000/api/wildcards/123 \
  -H "Content-Type: application/json" \
  -d '{"category_id": 456}'
```

### Q: 如何批量重新分類？

目前需要刪除後重新匯入，或使用 API 批量更新。

### Q: 資料庫在哪裡？

- Docker: PostgreSQL 容器內
- 本地: `data/wildcard.db` (SQLite)

### Q: 如何備份資料？

```bash
# 使用匯出功能
curl http://localhost:9000/api/export/json > backup.json

# PostgreSQL 備份
docker-compose exec db pg_dump -U wildcard_user wildcard_db > backup.sql
```

---

## 🔧 進階設定

### 修改 Ollama 模型

編輯 `ollama_helper.py`:

```python
ollama_helper = OllamaHelper(model="qwen2.5:14b")  # 使用更大的模型
```

### 調整翻譯溫度

編輯 `ollama_helper.py` 中的 `generate` 方法：

```python
"temperature": 0.1,  # 更一致但較死板
"temperature": 0.5,  # 更有創意但可能不一致
```

### 添加自定義分類

1. 編輯 `init_categories.py` 中的 `CATEGORY_TREE`
2. 運行 `python init_categories.py` 重建分類
3. 更新 `auto_categorizer.py` 中的 `CATEGORY_PATTERNS`

---

## 📝 授權

MIT License

## 💬 回饋

如有問題或建議，請提交 Issue 或 Pull Request
