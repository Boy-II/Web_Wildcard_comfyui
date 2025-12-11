# Wildcard 管理系統 - 完整技術文件

> 專為 AI 圖像生成設計的 Wildcard 提示詞管理系統
> 本文件為 LLM 閱讀優化，包含完整的架構說明和修改指南

---

## 目錄
- [專案概述](#專案概述)
- [核心功能](#核心功能)
- [系統架構](#系統架構)
- [資料庫架構](#資料庫架構)
- [重要檔案說明](#重要檔案說明)
- [API 端點完整列表](#api-端點完整列表)
- [工作流程](#工作流程)
- [LLM 修改注意事項](#llm-修改注意事項)
- [環境設定](#環境設定)
- [快速開始](#快速開始)
- [常見操作](#常見操作)

---

## 專案概述

這是一個基於 Flask 的 Web 應用程式，用於管理 AI 圖像生成的 Wildcard 提示詞。系統支援：
- 多層級樹狀分類結構
- AI 驅動的自動翻譯（Ollama/Gemini）
- 智慧自動分類
- 與 ComfyUI Wildcard 目錄的雙向同步
- 批量匯入/匯出功能
- Web UI 管理介面

### 技術棧
- **後端**: Python 3.11, Flask 3.x, SQLAlchemy 2.x
- **資料庫**: PostgreSQL 15 (主要) / SQLite (備用)
- **前端**: HTML5, Bootstrap 5.3, Vanilla JavaScript
- **AI 整合**: Ollama (本地), Google Gemini API (雲端)
- **容器化**: Docker Compose

---

## 核心功能

### 1. Wildcard 管理
- **CRUD 操作**: 建立、讀取、更新、刪除 wildcard 項目
- **批量操作**: 批量刪除、批量更新分類、批量啟用/停用
- **去重機制**: 同一分類下自動去除重複內容
- **狀態管理**: `is_active` 欄位控制啟用狀態
- **優先級**: `priority` 欄位支援排序

### 2. 多層級分類系統
- **樹狀結構**: 支援無限層級的父子分類 (實際建議 ≤3 層)
- **自動層級計算**: `level` 欄位自動維護 (0=根, 1=第一層子分類...)
- **完整路徑**: `get_full_path()` 方法產生如 "People > Artists > Anime Artists"
- **分類關聯**: 每個 wildcard 必須屬於一個分類
- **級聯刪除**: 刪除分類時可選是否刪除子分類

### 3. AI 驅動翻譯
- **雙引擎支援**:
  - Ollama: 本地運行，支援 qwen3:8b 等模型
  - Gemini: Google Cloud API，需要 API Key
- **批量翻譯**: 使用 ThreadPoolExecutor 並行處理
- **翻譯狀態追蹤**: `translation_status` (pending/translated/failed)
- **可設定參數**: system_prompt, temperature, model_name
- **資料庫儲存設定**: `TranslationSetting` 表管理多個翻譯提供者

### 4. 智慧自動分類
- **檔名模式匹配**: `auto_categorizer.py` 內建 169+ 條分類規則
- **AI 輔助分類**: 可選使用 Ollama 根據內容智慧分類
- **分類建議**: `get_category_suggestions()` 提供多個可能分類
- **後備機制**: 找不到匹配則歸類到 "misc" (其他)

### 5. ComfyUI 整合
- **扁平化檔案結構**: 所有 wildcard .txt 檔案存放在同一目錄（不使用子資料夾）
- **檔案命名規則**: 使用 `__` (雙底線) 編碼分類層級路徑
  - 範例: `people__artists__anime_artists.txt`
  - 資料庫保持多層級分類樹結構
- **目錄掃描**: 掃描單一目錄中的所有 .txt 檔案
- **雙向同步**:
  - **匯入同步**: 從 ComfyUI 目錄匯入到資料庫（自動解析扁平檔案名）
  - **狀態同步**: 根據檔案系統更新資料庫 `is_active` 狀態
  - **匯出同步**: 啟用/停用時自動寫入/移除檔案內容
- **路徑映射**: 分類層級結構 ↔ 扁平化檔案名稱
- **動態路徑**: 透過 `AppSetting` 表儲存 ComfyUI 路徑

### 6. 匯入/匯出系統
- **支援格式**:
  - 匯入: `.txt`, `.zip` (包含多個 .txt)
  - 匯出: `.txt`, `.json`, `.csv`
- **匯入選項**:
  - 手動指定分類 (`target_category_id`)
  - AI 自動分類 (`use_ollama_classify`)
  - AI 自動翻譯 (`use_ollama_translate`)
  - 遞迴搜尋子目錄 (`recursive`)
- **匯入歷史**: `ImportHistory` 表記錄每次匯入結果

### 7. Web UI 功能
- **頁面**:
  - `/` - 儀表板（統計資訊）
  - `/categories` - 分類管理
  - `/wildcards` - Wildcard 瀏覽
  - `/prompt-builder` - 提示詞構建器
  - `/import` - 匯入資料
  - `/export` - 匯出資料
  - `/comfy-monitor` - ComfyUI 監控
  - `/translation-settings` - 翻譯設定
- **互動功能**: 搜尋、分頁、篩選、拖拉排序（分類）

### 8. 提示詞構建器（Prompt Builder）
- **視覺化界面**：拖拉式選擇和組合 wildcards
- **語法支援**：
  - `__category__` - 從分類中隨機選擇（如 `__anime_artists__`）
  - `{option1|option2|option3}` - 從選項中隨機選擇
  - `{$varname=value}` - 定義變數（可包含 wildcard 或選項）
  - `$varname` - 引用變數（確保多處使用相同值）
  - 支援巢狀和組合使用
- **變數系統**：定義變數並在提示詞中重複引用，確保一致性
- **即時預覽**：隨機化提示詞並即時顯示結果及使用的變數
- **多次生成**：一次生成多個隨機變體
- **便捷功能**：
  - 點擊分類快速插入語法
  - 語法輔助按鈕（包含變數定義和引用）
  - 字數統計
  - 複製到剪貼簿
  - 搜尋分類

---

## 系統架構

### 目錄結構
```
wildcard/
├── app.py                      # 主應用程式 (Flask app, 路由, API)
├── webapp/
│   ├── models.py               # SQLAlchemy 資料庫模型
│   ├── templates/              # Jinja2 HTML 模板
│   │   ├── index.html          # 儀表板
│   │   ├── categories.html     # 分類管理
│   │   ├── wildcards.html      # Wildcard 瀏覽
│   │   ├── import.html         # 匯入頁面
│   │   ├── export.html         # 匯出頁面
│   │   ├── comfy_monitor.html  # ComfyUI 監控
│   │   └── translation_settings.html  # 翻譯設定
│   └── static/                 # 靜態資源 (CSS, JS, images)
├── auto_categorizer.py         # 自動分類邏輯 (169+ 規則)
├── ollama_helper.py            # Ollama API 封裝
├── gemini_helper.py            # Gemini API 封裝
├── init_categories.py          # 預設分類樹初始化腳本
├── bulk_import.py              # 批量匯入工具
├── import_data.py              # 獨立匯入腳本 (CLI)
├── docker-compose.yml          # Docker 服務編排
├── Dockerfile                  # Web 服務容器定義
├── requirements.txt            # Python 依賴
├── data/                       # SQLite 資料檔 (本機模式)
├── logs/                       # 日誌目錄
└── sample file/wildcards/      # 測試用 wildcard 檔案
```

### Docker 服務架構
```yaml
services:
  db:           # PostgreSQL 15 資料庫
  ollama:       # Ollama 本地 LLM 服務 (GPU 加速)
  web:          # Flask 應用程式
```

### 資料流向
```
[使用者]
   ↕ (HTTP)
[Flask App (app.py)]
   ↕
[SQLAlchemy ORM (webapp/models.py)]
   ↕
[PostgreSQL Database]

[Flask App] → [Ollama Helper] → [Ollama Service] (翻譯/分類)
[Flask App] → [Gemini Helper] → [Gemini API] (翻譯)
[Flask App] ↔ [ComfyUI Wildcard 目錄] (檔案 I/O)
```

---

## 資料庫架構

### 1. `categories` 表 - 分類（樹狀結構）
```sql
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,              -- 系統名稱 (如: anime_artists)
    display_name VARCHAR(100) NOT NULL,      -- 顯示名稱 (如: 動漫藝術家)
    description TEXT,                        -- 分類說明
    color VARCHAR(20) DEFAULT '#6c757d',     -- 顏色標記 (Bootstrap 色碼)
    sort_order INTEGER DEFAULT 0,            -- 排序順序
    parent_id INTEGER REFERENCES categories(id),  -- 父分類 ID (NULL=根分類)
    level INTEGER DEFAULT 0,                 -- 層級 (0=根, 1=第一層...)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(parent_id, name)                  -- 同一父分類下名稱唯一
);

CREATE INDEX idx_parent_sort ON categories(parent_id, sort_order);
```

**重要欄位**:
- `parent_id`: NULL 表示根分類，否則指向父分類
- `level`: 自動計算，用於查詢優化
- `sort_order`: 同層級內的排序

**關聯**:
- 自引用 (self-referential): `children` / `parent`
- 一對多: `categories` → `wildcards`

### 2. `wildcards` 表 - Wildcard 項目
```sql
CREATE TABLE wildcards (
    id SERIAL PRIMARY KEY,
    content VARCHAR(500) NOT NULL,           -- 英文內容
    content_zh VARCHAR(500),                 -- 中文翻譯
    category_id INTEGER NOT NULL REFERENCES categories(id),
    source_file VARCHAR(255),                -- 來源檔案名稱
    priority INTEGER DEFAULT 0,              -- 優先級/權重
    is_active BOOLEAN DEFAULT TRUE,          -- 是否啟用
    tags VARCHAR(500),                       -- 標籤 (逗號分隔)
    notes TEXT,                              -- 備註
    translation_status VARCHAR(20) DEFAULT 'pending',  -- pending/translated/failed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(category_id, content)             -- 同一分類下內容唯一
);

CREATE INDEX idx_content_active ON wildcards(content, is_active);
```

**重要欄位**:
- `is_active`: 控制是否啟用，影響匯出和 ComfyUI 同步
- `translation_status`: 追蹤翻譯進度
- `priority`: 保留欄位，可用於加權隨機選擇

### 3. `import_history` 表 - 匯入記錄
```sql
CREATE TABLE import_history (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(20),                   -- txt/zip/directory
    items_imported INTEGER DEFAULT 0,
    items_skipped INTEGER DEFAULT 0,         -- 重複跳過數量
    status VARCHAR(20),                      -- success/failed/partial
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4. `app_settings` 表 - 應用程式設定
```sql
CREATE TABLE app_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT
);
```

**目前使用的 key**:
- `comfyui_wildcard_path`: ComfyUI Wildcard 目錄路徑

### 5. `translation_settings` 表 - 翻譯設定
```sql
CREATE TABLE translation_settings (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) UNIQUE NOT NULL,    -- 'ollama' / 'gemini'
    is_active BOOLEAN DEFAULT FALSE,         -- 是否為啟用的翻譯引擎
    model_name VARCHAR(100),
    temperature FLOAT DEFAULT 0.3,
    system_prompt TEXT,
    api_key TEXT                             -- Gemini API Key (未加密)
);

CREATE INDEX idx_provider ON translation_settings(provider);
CREATE INDEX idx_active ON translation_settings(is_active);
```

**注意**: 同時只能有一個 `provider` 的 `is_active=TRUE`

---

## 重要檔案說明

### 核心應用程式

#### `app.py` (1480 行)
- **角色**: Flask 主應用程式
- **責任**:
  - 定義所有 HTTP 路由 (頁面 + API)
  - 實作 REST API 邏輯
  - 資料庫初始化 (`create_tables`, `init_categories`, `init_translation_settings`)
  - 檔案匯入/匯出邏輯
  - ComfyUI 同步邏輯
- **重要函式**:
  - `get_comfy_wildcard_path()`: 從資料庫獲取 ComfyUI 路徑
  - `import_txt_file()`: 單檔匯入核心邏輯
  - `import_from_directory()`: 目錄遞迴匯入
  - `get_translation_service()`: 獲取當前啟用的翻譯服務
  - `get_comfy_filepath_for_category()`: 分類路徑映射到檔案路徑
- **API 端點**: 見下方 "API 端點完整列表"

#### `webapp/models.py` (215 行)
- **角色**: SQLAlchemy ORM 模型定義
- **模型**:
  - `Category`: 分類模型（樹狀結構）
  - `Wildcard`: Wildcard 項目模型
  - `ImportHistory`: 匯入歷史模型
  - `AppSetting`: 應用程式設定模型
  - `TranslationSetting`: 翻譯設定模型
- **重要方法**:
  - `Category.get_full_path()`: 獲取完整路徑字串
  - `Category.get_all_children()`: 遞迴獲取所有子分類
  - `Category.get_all_wildcards()`: 獲取此分類及子分類的所有 wildcards
  - `Category.to_dict()`: 序列化為 JSON
  - `Wildcard.to_dict()`: 序列化為 JSON

### AI 整合模組

#### `ollama_helper.py` (186 行)
- **角色**: Ollama API 封裝
- **功能**:
  - `generate()`: 通用文本生成
  - `translate_to_chinese()`: 單一翻譯
  - `batch_translate()`: 並行批量翻譯（ThreadPoolExecutor）
  - `suggest_category()`: AI 輔助分類
  - `check_connection()`: 檢查 Ollama 服務狀態
  - `list_models()`: 列出可用模型
- **設定來源**: `TranslationSetting` 表 (provider='ollama')

#### `gemini_helper.py` (111 行)
- **角色**: Google Gemini API 封裝
- **功能**:
  - `generate()`: 通用文本生成
  - `translate_to_chinese()`: 單一翻譯
  - `batch_translate()`: 並行批量翻譯
  - `check_api_key()`: 驗證 API Key 有效性
- **依賴**: `google-generativeai` SDK
- **設定來源**: `TranslationSetting` 表 (provider='gemini')

### 分類系統

#### `auto_categorizer.py` (279 行)
- **角色**: 基於規則的自動分類器
- **核心資料**: `CATEGORY_PATTERNS` - 169+ 條分類規則
  - 格式: `({'keyword1', 'keyword2', ...}, 'category/path')`
  - 由具體到一般排序（越前面越優先匹配）
- **函式**:
  - `find_best_category(filename)`: 根據檔名匹配最佳分類
  - `get_category_by_path(path)`: 將路徑字串轉換為 Category 物件
  - `get_category_suggestions(filename, top_n)`: 獲取多個建議
- **分類結構**:
  ```
  people/           # 人物
    artists/        # 藝術家
      anime_artists/
      photographers/
      ...
    characters/     # 角色
      actors/
      actresses/
      ...
  body/             # 身體
    poses/          # 姿勢
    body_parts/     # 部位
    ...
  clothing/         # 服飾
  creatures/        # 生物
  scenes/           # 場景
  art_style/        # 藝術風格
  technical/        # 技術
  objects/          # 物件
  adjectives/       # 形容詞
  colors/           # 顏色
  composition/      # 構圖
  misc/             # 其他
  ```

#### `init_categories.py` (511 行)
- **角色**: 初始化預設分類樹
- **資料**: `CATEGORY_TREE` - 完整的預設分類樹定義
- **函式**: `create_category_tree()` - 遞迴建立分類樹
- **觸發時機**: 應用程式啟動時，如果 `categories` 表為空

### 其他工具

#### `bulk_import.py`
- **角色**: 命令列批量匯入工具
- **用途**: 大量資料匯入，可指定翻譯和分類選項

#### `import_data.py`
- **角色**: 獨立匯入腳本（早期版本，部分功能已整合至 app.py）

---

## API 端點完整列表

### 統計 API

#### `GET /api/stats`
- **功能**: 獲取系統統計資訊
- **回傳**:
  ```json
  {
    "total_wildcards": 1234,
    "active_wildcards": 1200,
    "inactive_wildcards": 34,
    "total_categories": 56,
    "category_stats": [
      {
        "name": "anime_artists",
        "display_name": "動漫藝術家",
        "color": "#007bff",
        "count": 234
      },
      ...
    ]
  }
  ```

### 分類管理 API

#### `GET /api/categories`
- **功能**: 獲取分類列表
- **Query 參數**:
  - `tree=true`: 返回樹狀結構（只返回根分類，子分類嵌套在 children）
  - `flat=true`: 返回扁平列表（預設）
  - `parent_id=<int>`: 只返回特定父分類的子分類
- **回傳**: `Category[]` 或樹狀結構

#### `POST /api/categories`
- **功能**: 建立新分類
- **Body**:
  ```json
  {
    "name": "new_category",
    "display_name": "新分類",
    "description": "說明",
    "color": "#ff5733",
    "sort_order": 10,
    "parent_id": 1  // 可選
  }
  ```
- **回傳**: 建立的 `Category` 物件

#### `PUT /api/categories/<int:category_id>`
- **功能**: 更新分類
- **Body**: 同 POST（部分更新）
- **特殊邏輯**:
  - 更改 `parent_id` 時會遞迴更新所有子分類的 `level`
  - 防止循環依賴

#### `DELETE /api/categories/<int:category_id>`
- **功能**: 刪除分類（級聯刪除）
- **行為**:
  - 刪除該類別下的所有 wildcards
  - 刪除所有子類別及其 wildcards
  - 自動從 ComfyUI 檔案中移除相關內容
- **回傳**: 200 OK
  ```json
  {
    "message": "類別已刪除",
    "deleted_wildcards": 15,
    "deleted_children": 3
  }
  ```

### Wildcard 管理 API

#### `GET /api/wildcards`
- **功能**: 獲取 wildcard 列表（分頁）
- **Query 參數**:
  - `page=<int>`: 頁碼（預設 1）
  - `per_page=<int>`: 每頁數量（預設 50）
  - `category_id=<int>`: 篩選分類
  - `search=<string>`: 搜尋內容（ILIKE）
  - `is_active=<true|false>`: 篩選啟用狀態
- **回傳**:
  ```json
  {
    "items": [...],
    "total": 1234,
    "page": 1,
    "per_page": 50,
    "pages": 25
  }
  ```

#### `POST /api/wildcards`
- **功能**: 建立新 wildcard
- **Body**:
  ```json
  {
    "content": "a beautiful cat",
    "category_id": 12,
    "content_zh": "一隻美麗的貓",  // 可選
    "priority": 5,                // 可選
    "is_active": true,            // 可選
    "tags": "animal,pet",         // 可選
    "notes": "備註"               // 可選
  }
  ```

#### `GET /api/wildcards/<int:wildcard_id>`
- **功能**: 獲取單一 wildcard
- **回傳**: `Wildcard` 物件

#### `PUT /api/wildcards/<int:wildcard_id>`
- **功能**: 更新 wildcard
- **Body**: 同 POST（部分更新）
- **特殊邏輯**:
  - `is_active` 狀態改變時會同步到 ComfyUI 檔案系統
  - 啟用：將內容附加到對應 .txt 檔案
  - 停用：從 .txt 檔案中移除該行

#### `DELETE /api/wildcards/<int:wildcard_id>`
- **功能**: 刪除 wildcard
- **回傳**: 204 No Content

#### `POST /api/wildcards/batch-delete`
- **功能**: 批量刪除 wildcards
- **Body**:
  ```json
  {
    "ids": [1, 2, 3, 4, 5]
  }
  ```
- **回傳**: `{"deleted": 5}`

#### `POST /api/wildcards/batch-update-category`
- **功能**: 批量更新分類
- **Body**:
  ```json
  {
    "ids": [1, 2, 3],
    "category_id": 10
  }
  ```
- **回傳**: `{"message": "...", "updated": 3}`

#### `POST /api/wildcards/batch-update-active`
- **功能**: 批量更新啟用狀態
- **Body**:
  ```json
  {
    "ids": [1, 2, 3, 4, 5],
    "is_active": true  // true=啟用, false=停用
  }
  ```
- **特殊邏輯**:
  - 自動同步到 ComfyUI 檔案系統
  - 啟用：將內容附加到對應 .txt 檔案
  - 停用：從 .txt 檔案中移除該行
  - 只處理狀態有變化的項目
- **回傳**:
  ```json
  {
    "message": "成功啟用 5 個 wildcards",
    "updated": 5,
    "errors": 0
  }
  ```

### 翻譯 API

#### `POST /api/wildcards/<int:wildcard_id>/translate`
- **功能**: 翻譯單一 wildcard
- **前提**: 需有啟用的翻譯服務（TranslationSetting.is_active=True）
- **邏輯**:
  - 已翻譯則直接返回
  - 特定分類（藝術家、emoji）跳過翻譯
  - 使用當前啟用的翻譯引擎
- **回傳**:
  ```json
  {
    "id": 123,
    "content_zh": "翻譯結果",
    "status": "translated"
  }
  ```

#### `POST /api/wildcards/batch-translate`
- **功能**: 批量翻譯 wildcards
- **Body**:
  ```json
  {
    "ids": [1, 2, 3, ...]
  }
  ```
- **邏輯**: 使用 `batch_translate()` 並行處理
- **回傳**:
  ```json
  {
    "translated": 45,
    "failed": 2
  }
  ```

### 匯入 API

#### `POST /api/import/upload`
- **功能**: 上傳檔案匯入（TXT 或 ZIP）
- **Content-Type**: `multipart/form-data`
- **Form 欄位**:
  - `file`: 檔案
  - `category_id`: 手動指定分類（可選）
  - `translate`: 是否翻譯（true/false）
- **邏輯**:
  - ZIP 檔案會解壓縮後遞迴處理
  - 支援自動分類或手動指定
  - 記錄到 `import_history`
- **回傳**:
  ```json
  {
    "imported": 123,
    "skipped": 5,
    "errors": []
  }
  ```

#### `POST /api/import/directory`
- **功能**: 從伺服器目錄匯入
- **Body**:
  ```json
  {
    "directory": "sample_file/wildcards",
    "use_ollama_classify": false,
    "use_ollama_translate": false,
    "recursive": true
  }
  ```
- **回傳**: 同上

### 匯出 API

#### `GET /api/export/<format>`
- **功能**: 匯出資料
- **參數**:
  - `<format>`: txt / json / csv
- **Query 參數**:
  - `category_id=<int>`: 僅匯出特定分類（可選）
  - `filename=<string>`: 自訂檔名（可選）
- **邏輯**: 只匯出 `is_active=True` 的項目
- **回傳**: 檔案下載

### ComfyUI 整合 API

#### `GET /api/comfy-wildcard/scan`
- **功能**: 掃描 ComfyUI Wildcard 目錄結構
- **回傳**:
  ```json
  {
    "success": true,
    "data": {
      "name": "Comfy_Wildcard",
      "type": "directory",
      "children": [...],
      "file_count": 234,
      "total_lines": 12345
    },
    "summary": {
      "total_files": 234,
      "total_lines": 12345,
      "scan_time": "2025-12-08T12:00:00"
    }
  }
  ```

#### `POST /api/comfy-wildcard/sync`
- **功能**: 將 ComfyUI 目錄同步到資料庫
- **Body**:
  ```json
  {
    "dry_run": false  // true=預覽，不實際寫入
  }
  ```
- **邏輯**:
  - 根據目錄結構自動建立分類樹
  - 檔案名稱（不含副檔名）作為最深層分類
  - 檔案內容作為 wildcards 匯入
- **回傳**:
  ```json
  {
    "success": true,
    "imported": 1234,
    "skipped": 56,
    "errors": [],
    "dry_run": false
  }
  ```

#### `POST /api/sync/status-from-comfy`
- **功能**: 從 ComfyUI 檔案系統反向同步啟用狀態
- **邏輯**:
  1. 掃描所有 .txt 檔案，收集所有 wildcard 內容
  2. 資料庫中所有 wildcards 先設為 `is_active=False`
  3. 檔案中存在的設為 `is_active=True`
- **用途**: 在外部修改 ComfyUI 檔案後，同步狀態回資料庫
- **回傳**:
  ```json
  {
    "message": "同步成功",
    "files_scanned": 234,
    "wildcards_found_in_files": 12345,
    "total_wildcards_in_db": 15000,
    "activated_wildcards": 12345
  }
  ```

### 系統管理 API

#### `POST /api/clear-all-data`
- **功能**: 清除所有資料並重新初始化分類
- **警告**: 危險操作，會刪除所有 wildcards、categories、import_history
- **邏輯**:
  1. 刪除 `import_history`
  2. 刪除 `wildcards`
  3. 刪除 `categories`
  4. 呼叫 `init_categories()` 重建預設分類
- **回傳**:
  ```json
  {
    "message": "所有資料已清除並重新初始化分類",
    "deleted_wildcards": 1234,
    "deleted_categories": 56,
    "deleted_import_history": 12
  }
  ```

#### `GET /api/settings/comfy-path`
- **功能**: 獲取 ComfyUI Wildcard 路徑
- **回傳**: `{"path": "/app/comfy_wildcard"}`

#### `PUT /api/settings/comfy-path`
- **功能**: 更新 ComfyUI Wildcard 路徑
- **Body**: `{"path": "/new/path"}`
- **邏輯**: 儲存到 `app_settings` 表，同時更新 `app.config`

### 翻譯設定 API

#### `GET /api/translation-settings`
- **功能**: 獲取所有翻譯提供者設定
- **回傳**: `TranslationSetting[]`

#### `PUT /api/translation-settings/<string:provider>`
- **功能**: 更新特定提供者設定
- **參數**: `<provider>` = ollama / gemini
- **Body**:
  ```json
  {
    "model_name": "qwen3:8b",
    "temperature": 0.3,
    "system_prompt": "...",
    "api_key": "..."  // 僅 Gemini 需要
  }
  ```

#### `POST /api/translation-settings/activate`
- **功能**: 啟用指定翻譯提供者
- **Body**: `{"provider": "ollama"}`
- **邏輯**: 將所有 provider 設為 inactive，只有指定的設為 active

#### `POST /api/translation-settings/test`
- **功能**: 測試翻譯設定（不保存）
- **Body**:
  ```json
  {
    "text": "a beautiful cat",
    "provider": "ollama",
    "settings": {
      "model_name": "qwen3:8b",
      "temperature": 0.3,
      "system_prompt": "...",
      "api_key": "..."  // Gemini only
    }
  }
  ```
- **回傳**:
  ```json
  {
    "original": "a beautiful cat",
    "translated": "一隻美麗的貓",
    "settings": {...}
  }
  ```

### Prompt Builder API

#### `GET /api/prompt-builder/wildcards`
- **功能**: 獲取所有 wildcard 分類和內容（用於提示詞構建器）
- **邏輯**:
  - 獲取所有啟用的 wildcards
  - 按分類組織
  - 只返回有內容的分類
- **回傳**:
  ```json
  [
    {
      "id": 1,
      "name": "anime_artists",
      "display_name": "動漫藝術家",
      "full_path": "People > Artists > Anime Artists",
      "color": "#007bff",
      "level": 2,
      "parent_id": 5,
      "wildcard_count": 150,
      "wildcards": [
        {
          "id": 123,
          "content": "makoto shinkai",
          "content_zh": "新海誠"
        },
        ...
      ]
    },
    ...
  ]
  ```

#### `POST /api/prompt-builder/preview`
- **功能**: 預覽提示詞（隨機化 wildcard 語法，支援變數）
- **Body**:
  ```json
  {
    "prompt": "{$artist=__anime_artists__} a beautiful portrait of a {girl|woman} by $artist, $artist style"
  }
  ```
- **語法處理順序**:
  1. `{$varname=value}` → 定義變數（value 可包含 wildcard 或選項語法）
  2. `__category__` → 從該分類隨機選擇一個 wildcard
  3. `{option1|option2|option3}` → 隨機選擇一個選項
  4. `$varname` → 替換為變數值
  - 支援巢狀處理（最多 10 層）
- **回傳**:
  ```json
  {
    "original": "{$artist=__anime_artists__} a beautiful portrait of a {girl|woman} by $artist, $artist style",
    "preview": "a beautiful portrait of a woman by makoto shinkai, makoto shinkai style",
    "variables": {
      "artist": "makoto shinkai"
    }
  }
  ```

---

## 工作流程

### 1. 應用程式啟動流程
```
1. Docker Compose 啟動
   ├─ db (PostgreSQL) 啟動 → healthcheck
   ├─ ollama 啟動
   └─ web 等待 db 健康檢查通過

2. Flask App 初始化 (app.py)
   ├─ 載入環境變數
   ├─ 初始化資料庫連接
   └─ 註冊路由

3. 第一次 HTTP 請求觸發 @app.before_request
   ├─ db.create_all() - 建立表格
   ├─ init_categories() - 初始化預設分類（如果為空）
   ├─ init_translation_settings() - 初始化翻譯設定
   └─ init_app_settings() - 初始化應用程式設定

4. 應用程式就緒
```

### 2. 檔案匯入流程（帶翻譯）
```
1. 用戶上傳 .txt 或 .zip
   ↓
2. import_from_directory() 或 import_txt_file()
   ↓
3. 讀取檔案內容，逐行處理
   ├─ clean_line() - 清理行號標記
   ├─ 檢查重複（Wildcard.query.filter_by(content=...)）
   └─ 跳過或繼續
   ↓
4. 自動分類
   ├─ 如果指定 target_category_id → 使用指定分類
   ├─ 如果 use_ollama_classify → AI 建議分類
   └─ 否則 → auto_categorizer.find_best_category()
   ↓
5. 建立 Wildcard 物件並加入 session
   ↓
6. 如果 use_ollama_translate:
   ├─ 收集所有待翻譯文本
   ├─ ollama.batch_translate() - 並行翻譯
   └─ 更新 content_zh 和 translation_status
   ↓
7. db.session.commit()
   ↓
8. 記錄到 import_history
```

### 3. ComfyUI 同步流程

#### 3.1 從資料庫到 ComfyUI（匯出同步）
```
用戶啟用/停用 wildcard (PUT /api/wildcards/<id>)
   ↓
is_active 狀態改變?
   ↓ Yes
get_comfy_filepath_for_category()
   ├─ 根據分類層級構建扁平化檔案名
   └─ 例: people__artists__anime_artists.txt
   ↓
if is_active == True:
   ├─ 確保基礎目錄存在
   └─ 附加內容到 .txt 檔案
if is_active == False:
   ├─ 讀取檔案
   ├─ 移除匹配的行
   └─ 寫回檔案
```

#### 3.2 從 ComfyUI 到資料庫（匯入同步）
```
POST /api/comfy-wildcard/sync
   ↓
掃描 ComfyUI 基礎目錄（不遞迴）
   ↓
對每個 .txt 檔案:
   ├─ 解析扁平化檔案名 → 分類層級
   │   └─ 例: people__artists__anime_artists.txt → ['people', 'artists', 'anime_artists']
   ├─ 使用 get_category_from_filename() 查找分類
   ├─ 若不存在則逐層建立分類
   ├─ 讀取檔案內容
   └─ 批量建立 wildcards
   ↓
db.session.commit()
```

#### 3.3 狀態反向同步
```
POST /api/sync/status-from-comfy
   ↓
掃描所有 .txt 檔案 → Set<content>
   ↓
UPDATE wildcards SET is_active = FALSE  (全部停用)
   ↓
批次處理:
   UPDATE wildcards SET is_active = TRUE WHERE content IN (...)
   ↓
db.session.commit()
```

### 4. 翻譯流程

#### 4.1 單一翻譯
```
POST /api/wildcards/<id>/translate
   ↓
get_translation_service()
   ├─ 查詢 is_active=True 的 TranslationSetting
   ├─ 如果 provider='ollama' → OllamaHelper
   └─ 如果 provider='gemini' → GeminiHelper
   ↓
檢查:
   ├─ 已翻譯? → 直接返回
   ├─ 特殊分類（藝術家/emoji）? → 跳過
   └─ 否則繼續
   ↓
helper.translate_to_chinese(content, system_prompt, temperature)
   ↓
更新 content_zh, translation_status='translated'
   ↓
db.session.commit()
```

#### 4.2 批量翻譯
```
POST /api/wildcards/batch-translate
   ↓
過濾待翻譯項目:
   ├─ 未翻譯 (translation_status != 'translated')
   └─ 非特殊分類
   ↓
helper.batch_translate(texts, system_prompt)
   ├─ 使用 ThreadPoolExecutor (max_workers=4)
   ├─ 並行呼叫 translate_to_chinese()
   └─ 收集結果 {原文: 譯文}
   ↓
批次更新資料庫
   ↓
db.session.commit()
```

---

## 扁平化檔案結構技術說明

### 設計原理

為配合 ComfyUI wildcard 監視目錄需求，系統採用**扁平化單層檔案結構**，但在資料庫中維持**多層級分類樹**。

### 檔案命名規則

**格式**: `層級1__層級2__層級3.txt`

**範例**:
- 原階層路徑: `people/artists/anime_artists`
- 扁平化檔案名: `people__artists__anime_artists.txt`
- 資料庫結構: Category (people) → Category (artists) → Category (anime_artists)

### 核心函式

#### `get_comfy_filepath_for_category(category, base_path)`
**位置**: `app.py:409-429`

**功能**: 從分類物件產生扁平化檔案路徑

**實作邏輯**:
```python
1. 向上遍歷分類樹，收集所有祖先分類名稱
2. 使用 '__' 連接所有層級名稱
3. 添加 .txt 副檔名
4. 回傳基礎目錄路徑 + 檔案名
```

**範例**:
```python
category = Category(name='anime_artists', parent=artists_cat)
# artists_cat.parent = people_cat
# people_cat.parent = None

dir_path, filename = get_comfy_filepath_for_category(category, '/comfy/wildcards')
# dir_path = Path('/comfy/wildcards')
# filename = 'people__artists__anime_artists.txt'
```

#### `get_category_from_filename(filename)`
**位置**: `app.py:432-470`

**功能**: 從扁平化檔案名反推分類物件

**實作邏輯**:
```python
1. 移除 .txt 副檔名
2. 使用 '__' 分割檔案名稱為路徑部分
3. 從最深層分類開始查找資料庫
4. 比對完整路徑避免同名衝突
5. 回傳匹配的分類物件
```

**範例**:
```python
category = get_category_from_filename('people__artists__anime_artists.txt')
# 1. 分割: ['people', 'artists', 'anime_artists']
# 2. 查找 name='anime_artists' 的所有分類
# 3. 驗證其完整路徑是否為 ['people', 'artists', 'anime_artists']
# 4. 回傳匹配的 Category 物件
```

### 修改的 API 端點

#### `GET /api/comfy-wildcard/scan`
- 只掃描基礎目錄（使用 `glob('*.txt')`，不使用 `rglob`）
- 從扁平檔案名建立虛擬樹狀結構供 UI 顯示
- 函式: `build_tree_from_flat_files()`

#### `POST /api/comfy-wildcard/sync`
- 只讀取基礎目錄的 .txt 檔案
- 使用 `get_category_from_filename()` 解析分類
- 找不到時自動建立分類層級

#### `POST /api/sync/status-from-comfy`
- 只掃描基礎目錄同步啟用狀態
- 批次更新資料庫的 `is_active` 欄位

### 限制與注意事項

1. **檔案名長度**: Windows 檔案名限制 255 字元，過深的分類層級可能超過限制
2. **特殊字元**: 分類名稱中的特殊字元經過 `secure_filename()` 清理
3. **遷移需求**: 從舊有階層結構遷移到扁平結構需要手動處理或重新匯出
4. **ComfyUI 設定**: 建議 ComfyUI 監視目錄設定為單層目錄

### 優勢

- ✅ 相容 ComfyUI 單層目錄監視
- ✅ 避免檔案系統深層目錄限制
- ✅ 簡化檔案同步邏輯
- ✅ 保持資料庫的靈活分類結構

---

## LLM 修改注意事項

### 🔴 關鍵約束與規則

#### 1. 資料庫完整性
- **絕對禁止**:
  - 直接操作 SQL 繞過 ORM
  - 手動修改 `level` 欄位（應透過 parent_id 自動計算）
  - 刪除有子分類的分類（會觸發級聯刪除）
- **必須遵守**:
  - 同一 `category_id` 下 `content` 唯一
  - 同一 `parent_id` 下 `name` 唯一
  - 修改 `parent_id` 時，遞迴更新所有子分類的 `level`

#### 2. ComfyUI 同步邏輯
- **檔案路徑計算**: `get_comfy_filepath_for_category()`
  - 路徑結構 = 分類層級結構
  - 檔案名稱 = 最深層分類的 `name` + .txt
  - 例: `people > artists > anime_artists` → `{base}/people/artists/anime_artists.txt`
- **雙向一致性**:
  - 資料庫 `is_active` 改變 → 必須同步檔案
  - 檔案系統改變 → 使用 `/api/sync/status-from-comfy` 同步回資料庫
- **並發安全**: 檔案 I/O 無鎖，高並發環境需注意

#### 3. 翻譯系統
- **單一啟用原則**: 同時只能有一個 `TranslationSetting.is_active=True`
- **提供者切換**: 必須透過 `/api/translation-settings/activate` API
- **模型可用性檢查**:
  - Ollama: 先 `check_connection()`，再檢查模型是否在 `list_models()` 中
  - Gemini: 使用 `check_api_key()` 驗證
- **批量處理**: 使用 ThreadPoolExecutor，注意 API 限流

#### 4. 分類規則
- **優先級順序**:
  1. `target_category_id` (手動指定)
  2. AI 分類 (`use_ollama_classify=True`)
  3. 規則分類 (`auto_categorizer.find_best_category()`)
  4. 預設 `misc` 分類
- **規則維護**: `auto_categorizer.py` 中的 `CATEGORY_PATTERNS` 需與 `init_categories.py` 的 `CATEGORY_TREE` 對應

#### 5. 匯入去重
- **去重層級**: 全局去重（檢查 `content` 是否存在於 `wildcards` 表）
- **合併策略**: 重複項目會 skip，不會更新現有資料
- **歷史記錄**: `items_skipped` 欄位記錄跳過數量

### 🟡 效能考量

#### 1. 批量操作優化
```python
# ❌ 錯誤：逐筆提交
for item in items:
    wildcard = Wildcard(...)
    db.session.add(wildcard)
    db.session.commit()  # 每次都提交，慢！

# ✅ 正確：批量提交
for item in items:
    wildcard = Wildcard(...)
    db.session.add(wildcard)

    if len(items) % 100 == 0:  # 每100筆提交一次
        db.session.commit()

db.session.commit()  # 最後提交剩餘的
```

#### 2. 查詢優化
```python
# ❌ 錯誤：N+1 查詢
wildcards = Wildcard.query.all()
for w in wildcards:
    print(w.category.display_name)  # 每次都查詢！

# ✅ 正確：join 查詢
wildcards = Wildcard.query.options(
    db.joinedload(Wildcard.category)
).all()
for w in wildcards:
    print(w.category.display_name)  # 已載入，不再查詢
```

#### 3. 分頁必要性
- 大量資料（>1000）必須使用分頁
- 前端應實作虛擬滾動或無限滾動
- API 預設 `per_page=50`

### 🟢 擴充建議

#### 1. 新增分類
**步驟**:
1. 在 `init_categories.py` 的 `CATEGORY_TREE` 中定義
2. 在 `auto_categorizer.py` 的 `CATEGORY_PATTERNS` 中加入匹配規則
3. 重新部署或手動透過 API 建立

**範例**:
```python
# init_categories.py
CATEGORY_TREE = [
    {
        'name': 'new_root',
        'display_name': '新根分類',
        'description': '...',
        'color': '#ff5733',
        'children': [
            {
                'name': 'new_child',
                'display_name': '新子分類',
                'description': '...'
            }
        ]
    },
    ...
]

# auto_categorizer.py
CATEGORY_PATTERNS = [
    ({'keyword1', 'keyword2'}, 'new_root/new_child'),
    ...
]
```

#### 2. 新增翻譯引擎
**步驟**:
1. 在 `xxx_helper.py` 中實作 Helper 類別
2. 必須實作方法:
   - `translate_to_chinese(text, system_prompt, temperature)`
   - `batch_translate(texts, system_prompt, temperature)`
3. 在 `app.py` 的 `get_translation_service()` 中加入分支
4. 在 `init_translation_settings()` 中初始化預設設定

**範例**:
```python
# claude_helper.py
class ClaudeHelper:
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model

    def translate_to_chinese(self, text, system_prompt, temperature):
        # 實作翻譯邏輯
        ...

    def batch_translate(self, texts, system_prompt, temperature):
        # 實作批量翻譯
        ...

# app.py - get_translation_service()
elif provider == 'claude':
    if not active_setting.api_key:
        return None, None, "Claude API Key 未設定"
    helper = ClaudeHelper(
        api_key=active_setting.api_key,
        model=active_setting.model_name
    )
    return helper, active_setting, None
```

#### 3. 新增 API 端點
**建議結構**:
```python
@app.route('/api/your-endpoint', methods=['POST'])
def api_your_function():
    """功能說明"""
    try:
        # 1. 驗證輸入
        data = request.json
        if not data or 'required_field' not in data:
            return jsonify({'error': '缺少必要欄位'}), 400

        # 2. 業務邏輯
        result = your_logic(data)

        # 3. 資料庫操作
        db.session.commit()

        # 4. 返回結果
        return jsonify(result), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
```

#### 4. 新增資料表
**步驟**:
1. 在 `webapp/models.py` 定義新模型
2. 加入 `to_dict()` 方法（JSON 序列化）
3. 定義關聯（ForeignKey, relationship）
4. 刪除舊資料庫磁碟區，重建:
   ```bash
   docker-compose down -v
   docker-compose up -d --build
   ```

**範例**:
```python
class YourModel(db.Model):
    __tablename__ = 'your_table'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    foreign_id = db.Column(db.Integer, db.ForeignKey('other_table.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 關聯
    other = db.relationship('OtherModel', back_populates='yours')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat()
        }
```

### 🔵 除錯技巧

#### 1. 資料庫問題
```bash
# 進入資料庫容器
docker-compose exec db psql -U wildcard_user wildcard_db

# 檢查表結構
\d categories
\d wildcards

# 檢查資料
SELECT * FROM categories WHERE parent_id IS NULL;
SELECT COUNT(*) FROM wildcards WHERE is_active = TRUE;

# 檢查翻譯設定
SELECT provider, is_active FROM translation_settings;
```

#### 2. Ollama 連接問題
```bash
# 檢查 Ollama 服務
docker-compose exec web curl http://ollama:11434/api/tags

# 檢查模型列表
docker-compose exec ollama ollama list

# 拉取模型
docker-compose exec ollama ollama pull qwen3:8b
```

#### 3. 日誌查看
```bash
# Flask 應用程式日誌
docker-compose logs -f web

# Ollama 日誌
docker-compose logs -f ollama

# 資料庫日誌
docker-compose logs -f db

# 即時監控所有服務
docker-compose logs -f
```

#### 4. 手動測試 API
```bash
# 獲取統計
curl http://localhost:9000/api/stats

# 獲取分類（樹狀）
curl http://localhost:9000/api/categories?tree=true

# 建立 wildcard
curl -X POST http://localhost:9000/api/wildcards \
  -H "Content-Type: application/json" \
  -d '{"content":"test","category_id":1}'

# 測試翻譯
curl -X POST http://localhost:9000/api/wildcards/1/translate
```

### 🟣 安全性注意

#### 1. API Key 儲存
- **現狀**: Gemini API Key 以明文儲存於資料庫
- **建議**: 實作加密儲存（AES-256）或使用環境變數

#### 2. 檔案路徑安全
- **風險**: `get_comfy_wildcard_path()` 可由用戶設定，可能導致路徑穿越
- **建議**: 驗證路徑必須在允許的目錄內

#### 3. SQL 注入
- **現狀**: 使用 SQLAlchemy ORM，自動防護
- **建議**: 避免使用 `db.session.execute(raw_sql)`

#### 4. 檔案上傳
- **現狀**: 使用 `secure_filename()` 處理
- **建議**:
  - 限制檔案大小
  - 驗證檔案類型（MIME type）
  - 掃描病毒

---

## 環境設定

### Docker Compose 環境變數

#### `db` 服務
```yaml
POSTGRES_DB: wildcard_db          # 資料庫名稱
POSTGRES_USER: wildcard_user      # 資料庫用戶
POSTGRES_PASSWORD: wildcard_pass  # 資料庫密碼
```

#### `ollama` 服務
```yaml
OLLAMA_NUM_GPU: 999               # GPU 數量限制
OLLAMA_GPU_LAYERS: 999            # GPU 層數
# Volume: C:\LLM\model:/root/.ollama  # 模型儲存路徑（Windows）
```

#### `web` 服務
```yaml
FLASK_APP: app.py
FLASK_ENV: development            # development / production
DATABASE_URL: postgresql://wildcard_user:wildcard_pass@db:5432/wildcard_db
OLLAMA_BASE_URL: http://ollama:11434
OLLAMA_MODEL: qwen3:8b            # 預設 Ollama 模型
# 不再使用環境變數設定 ComfyUI 路徑，改由資料庫 app_settings 管理
```

### 主機端口映射
```yaml
db:      5432:5432   # PostgreSQL
ollama:  11434:11434 # Ollama API
web:     9000:5000   # Flask App (主機:9000 → 容器:5000)
```

### Volume 掛載
```yaml
web:
  - ./app.py:/app/app.py                # 熱重載
  - ./webapp:/app/webapp                # 熱重載
  - ./data:/app/data                    # SQLite 資料檔（備用）
  - ./logs:/app/logs                    # 日誌
  - ./sample file:/app/sample_file      # 測試資料
  - D:/ComfyUI-.../wildcards:/app/comfy_wildcard  # ComfyUI 目錄
```

### 本機環境變數（不使用 Docker）
```bash
# 資料庫
export DATABASE_URL="sqlite:///data/wildcard.db"
# 或
export DATABASE_URL="postgresql://user:pass@localhost:5432/wildcard_db"

# Flask
export FLASK_APP=app.py
export FLASK_ENV=development
export SECRET_KEY=your-secret-key

# Ollama
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=qwen3:8b

# ComfyUI（由資料庫管理，此處僅作為初始值）
export COMFYUI_WILDCARD_PATH=/path/to/comfyui/wildcards
```

---

## 快速開始

### 使用 Docker（推薦）

#### 1. 啟動所有服務
```bash
docker-compose up -d
```

#### 2. 檢查服務狀態
```bash
docker-compose ps

# 應顯示:
# wildcard_db      running
# wildcard_ollama  running
# wildcard_web     running
```

#### 3. 查看日誌
```bash
# 查看所有服務日誌
docker-compose logs -f

# 只查看 web 服務
docker-compose logs -f web
```

#### 4. 初始化資料（可選）
```bash
# 進入 web 容器
docker-compose exec web bash

# 執行初始化腳本
python init_categories.py

# 匯入測試資料
python import_data.py sample_file/wildcards
```

#### 5. 訪問服務
- Web UI: http://localhost:9000
- Ollama API: http://localhost:11434

#### 6. 停止服務
```bash
# 停止但保留資料
docker-compose down

# 停止並刪除資料
docker-compose down -v
```

### 本機運行

#### 1. 安裝依賴
```bash
pip install -r requirements.txt
```

#### 2. 設定環境變數
```bash
export DATABASE_URL="sqlite:///data/wildcard.db"
export FLASK_ENV=development
```

#### 3. 啟動應用程式
```bash
python app.py
```

#### 4. 訪問
http://localhost:5000

---

## 常見操作

### 資料庫管理

#### 備份資料庫
```bash
# PostgreSQL
docker-compose exec db pg_dump -U wildcard_user wildcard_db > backup_$(date +%Y%m%d).sql

# SQLite（本機模式）
cp data/wildcard.db data/wildcard_backup_$(date +%Y%m%d).db
```

#### 恢復資料庫
```bash
# PostgreSQL
docker-compose exec -T db psql -U wildcard_user wildcard_db < backup.sql

# SQLite
cp backup.db data/wildcard.db
```

#### 重置資料庫
```bash
# 刪除所有資料並重建
docker-compose down -v
docker-compose up -d
```

### 分類管理

#### 透過 API 建立分類
```bash
curl -X POST http://localhost:9000/api/categories \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_category",
    "display_name": "我的分類",
    "description": "說明",
    "color": "#28a745",
    "sort_order": 10,
    "parent_id": 1
  }'
```

#### 更新分類
```bash
curl -X PUT http://localhost:9000/api/categories/10 \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "新名稱",
    "color": "#dc3545"
  }'
```

#### 刪除分類
```bash
# 注意：會級聯刪除所有 wildcard 和子類別
curl -X DELETE http://localhost:9000/api/categories/10

# 回應範例
{
  "message": "類別已刪除",
  "deleted_wildcards": 15,
  "deleted_children": 3
}
```

### Wildcard 管理

#### 批量匯入
```bash
# 從目錄
curl -X POST http://localhost:9000/api/import/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "sample_file/wildcards",
    "use_ollama_classify": false,
    "use_ollama_translate": true,
    "recursive": true
  }'

# 上傳 ZIP 檔案
curl -X POST http://localhost:9000/api/import/upload \
  -F "file=@wildcards.zip" \
  -F "translate=true"
```

#### 批量翻譯
```bash
curl -X POST http://localhost:9000/api/wildcards/batch-translate \
  -H "Content-Type: application/json" \
  -d '{
    "ids": [1, 2, 3, 4, 5]
  }'
```

#### 批量啟用/停用
```bash
# 批量啟用
curl -X POST http://localhost:9000/api/wildcards/batch-update-active \
  -H "Content-Type: application/json" \
  -d '{
    "ids": [1, 2, 3, 4, 5],
    "is_active": true
  }'

# 批量停用
curl -X POST http://localhost:9000/api/wildcards/batch-update-active \
  -H "Content-Type: application/json" \
  -d '{
    "ids": [1, 2, 3, 4, 5],
    "is_active": false
  }'
```

#### 批量匯出
```bash
# TXT 格式
curl "http://localhost:9000/api/export/txt?category_id=1&filename=my_wildcards" -o output.txt

# JSON 格式
curl "http://localhost:9000/api/export/json?category_id=1" -o output.json

# CSV 格式
curl "http://localhost:9000/api/export/csv" -o output.csv
```

### ComfyUI 整合

#### 掃描目錄
```bash
curl http://localhost:9000/api/comfy-wildcard/scan
```

#### 同步到資料庫
```bash
# 預覽（不實際寫入）
curl -X POST http://localhost:9000/api/comfy-wildcard/sync \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'

# 實際同步
curl -X POST http://localhost:9000/api/comfy-wildcard/sync \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'
```

#### 反向同步狀態
```bash
curl -X POST http://localhost:9000/api/sync/status-from-comfy
```

#### 更新 ComfyUI 路徑
```bash
curl -X PUT http://localhost:9000/api/settings/comfy-path \
  -H "Content-Type: application/json" \
  -d '{"path": "/new/path/to/comfyui/wildcards"}'
```

### 翻譯設定

#### 查看當前設定
```bash
curl http://localhost:9000/api/translation-settings
```

#### 切換翻譯引擎
```bash
# 切換到 Ollama
curl -X POST http://localhost:9000/api/translation-settings/activate \
  -H "Content-Type: application/json" \
  -d '{"provider": "ollama"}'

# 切換到 Gemini
curl -X POST http://localhost:9000/api/translation-settings/activate \
  -H "Content-Type: application/json" \
  -d '{"provider": "gemini"}'
```

#### 更新 Gemini API Key
```bash
curl -X PUT http://localhost:9000/api/translation-settings/gemini \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "your-gemini-api-key",
    "model_name": "gemini-1.5-flash-latest",
    "temperature": 0.3
  }'
```

#### 測試翻譯
```bash
curl -X POST http://localhost:9000/api/translation-settings/test \
  -H "Content-Type: application/json" \
  -d '{
    "text": "a beautiful landscape",
    "provider": "ollama",
    "settings": {
      "model_name": "qwen3:8b",
      "temperature": 0.3,
      "system_prompt": "你是翻譯助手..."
    }
  }'
```

### Ollama 模型管理

#### 列出已安裝模型
```bash
docker-compose exec ollama ollama list
```

#### 拉取新模型
```bash
docker-compose exec ollama ollama pull qwen3:8b
docker-compose exec ollama ollama pull llama2:7b
```

#### 刪除模型
```bash
docker-compose exec ollama ollama rm qwen3:8b
```

#### 測試模型
```bash
docker-compose exec ollama ollama run qwen3:8b "Hello, how are you?"
```

---

## 附錄

### 常見錯誤排查

#### 1. 資料庫連接失敗
```
錯誤: could not connect to server: Connection refused
```
**解決**:
- 檢查 `db` 服務是否啟動: `docker-compose ps`
- 查看資料庫日誌: `docker-compose logs db`
- 等待 healthcheck 通過（約 10-30 秒）

#### 2. Ollama 模型未找到
```
錯誤: Ollama 模型 'qwen3:8b' 未在 Ollama 服務中找到
```
**解決**:
```bash
docker-compose exec ollama ollama pull qwen3:8b
```

#### 3. 資料庫 schema 不一致
```
錯誤: (OperationalError) ... column does not exist
```
**解決**:
```bash
docker-compose down -v  # 刪除舊資料
docker-compose up -d    # 重建
```

#### 4. ComfyUI 路徑不存在
```
錯誤: 目錄不存在: /app/comfy_wildcard
```
**解決**:
- 檢查 `docker-compose.yml` 中的 volume 映射
- 確認主機路徑存在
- 透過 API 更新路徑: `/api/settings/comfy-path`

#### 5. 翻譯服務未啟用
```
錯誤: 沒有啟用的翻譯服務
```
**解決**:
```bash
curl -X POST http://localhost:9000/api/translation-settings/activate \
  -H "Content-Type: application/json" \
  -d '{"provider": "ollama"}'
```

### 效能調優建議

#### 1. 資料庫
- 定期 `VACUUM` (PostgreSQL)
- 建立適當索引（已內建）
- 使用連接池（已配置）

#### 2. Ollama
- 調整 GPU 層數: `OLLAMA_GPU_LAYERS`
- 減少並行數: `max_workers` (預設 4)
- 使用更快的模型（如 qwen3:4b）

#### 3. 批量操作
- 調整批次大小: `batch_size`（預設 10）
- 分批提交資料庫（每 100 筆）
- 使用 `bulk_insert_mappings()` (SQLAlchemy)

#### 4. 前端
- 實作虛擬滾動
- 使用 WebSocket 推送進度（待實作）
- 快取 API 回應

### 開發路線圖

#### 短期（v1.1）
- [ ] API Key 加密儲存
- [ ] WebSocket 即時進度推送
- [ ] 前端虛擬滾動優化
- [ ] 匯入/匯出進度條

#### 中期（v1.2）
- [ ] 用戶系統與權限管理
- [ ] Wildcard 標籤系統增強
- [ ] 圖片預覽功能
- [ ] 批量編輯界面

#### 長期（v2.0）
- [ ] 多語言支援
- [ ] API Rate Limiting
- [ ] 完整 RESTful API
- [ ] 插件系統

---

## 授權與貢獻

### 授權
MIT License

### 作者
- 初始版本: Claude Code 自動生成
- 維護者: [Your Name]

### 貢獻指南
1. Fork 專案
2. 建立功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

---

**文件版本**: v1.0.0
**最後更新**: 2025-12-08
**適用版本**: Wildcard 管理系統 v1.0.0+
