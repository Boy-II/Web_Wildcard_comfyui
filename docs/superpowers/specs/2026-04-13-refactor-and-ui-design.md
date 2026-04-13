# 設計規格：app.py 重構 + UI 改版

**日期**：2026-04-13
**狀態**：已核准

---

## 範圍摘要

1. 將 2036 行的 `app.py` 拆分為 Flask Blueprint + Services 架構
2. 類別系統扁平化（多層 → 單層）+ 一次性遷移腳本
3. 移除 Pollinations 翻譯 provider
4. 新增通用 OpenAI-compatible 翻譯 provider
5. 整合 Wildcard 列表 + 類別管理為單一頁面
6. 首頁簡化
7. 翻譯設定頁面改版

---

## Section 1：後端架構重構

### 目錄結構

```
app.py                          # 僅 ~20 行：from webapp import create_app; app = create_app()
webapp/
├── __init__.py                 # create_app() 工廠：初始化 db、register blueprints、啟動 hook
├── models.py                   # 不變（Category, Wildcard, TranslationSetting 等）
├── routes/
│   ├── pages.py                # Blueprint pages_bp，prefix=/
│   └── api/
│       ├── categories.py       # Blueprint categories_bp，prefix=/api/categories
│       ├── wildcards.py        # Blueprint wildcards_bp，prefix=/api/wildcards
│       ├── import_export.py    # Blueprint import_export_bp，prefix=/api
│       ├── comfy_sync.py       # Blueprint comfy_bp，prefix=/api/comfy-wildcard
│       └── settings.py         # Blueprint settings_bp，prefix=/api（翻譯設定 + app 設定）
├── services/
│   ├── category_service.py     # 分類 CRUD、扁平化遷移、get_comfy_filepath()
│   ├── wildcard_service.py     # Wildcard CRUD、分頁查詢、批量操作、ComfyUI 檔案讀寫
│   └── translation_service.py  # dispatch 翻譯請求到對應 helper；list_models()
├── helpers/
│   ├── ollama_helper.py        # 從根目錄移入，邏輯不變
│   ├── gemini_helper.py        # 從根目錄移入，邏輯不變
│   └── openai_helper.py        # 新增：通用 OpenAI-compatible
├── templates/                  # 不變（結構），內容依各 section 更新
└── static/                     # 不變
```

根目錄原有的 `ollama_helper.py`、`gemini_helper.py`、`pollinations_helper.py` 一併清除。

### Blueprint 對應表

| Blueprint | url_prefix | 對應原 app.py 路由 |
|---|---|---|
| `pages_bp` | `/` | 所有 render_template 路由 |
| `categories_bp` | `/api/categories` | `/api/categories/**` |
| `wildcards_bp` | `/api/wildcards` | `/api/wildcards/**` |
| `import_export_bp` | `/api` | `/api/import/**`, `/api/export/**` |
| `comfy_bp` | `/api/comfy-wildcard` | `/api/comfy-wildcard/**` |
| `settings_bp` | `/api` | `/api/settings/**`, `/api/translation-settings/**` |

### Services 職責原則

Routes 只做：解析 request → 呼叫 service → 回傳 `jsonify`。不含業務邏輯。

- **category_service**: 分類 CRUD（含遞迴刪除）、`get_comfy_filepath(category)`
- **wildcard_service**: Wildcard CRUD、分頁 + 篩選查詢、批量啟用/停用、ComfyUI `.txt` 讀寫同步
- **translation_service**: `translate(text, provider, settings)` dispatch；`list_models(provider, base_url, api_key)` 呼叫 `{base_url}/v1/models`

### create_app() 初始化順序

```python
def create_app():
    app = Flask(...)
    app.config.from_...
    db.init_app(app)
    # register blueprints
    with app.app_context():
        db.create_all()
        _add_missing_columns()   # 手動 ALTER TABLE（base_url 欄位）
        init_categories()
        init_translation_settings()
        init_app_settings()
    return app
```

---

## Section 2：類別扁平化遷移

### 目標

多層樹狀分類 → 單層 flat list。每個 `Category.name` 直接對應一個 `.txt` 檔案名稱。

### 命名規則

```
People > Artists > Anime Artists  (name: anime_artists)
→ name:         people__artists__anime_artists
→ display_name: 保留原 leaf 的 display_name（如 "Anime Artists"）不變
→ parent_id:    None
→ level:        0
```

### 遷移腳本：`migrate_flatten_categories.py`

執行步驟：

1. 載入所有 Category（含 parent 關聯）
2. 對每個 leaf category（`children == []`）：
   - 計算完整路徑：`people__artists__anime_artists`
   - 更新 `name`、`parent_id = None`、`level = 0`
3. 對有直接 wildcard 但也有子分類的中間節點：
   - 同樣扁平化 name，parent_id = None，level = 0
4. 對只是結構用的中間節點（無直接 wildcard）：
   - 刪除（wildcard 已全部在 leaf）
5. Commit

觸發方式：
```bash
# 方式一：shell 腳本
flask --app app shell < migrate_flatten_categories.py

# 方式二：一次性 API（執行後可刪除）
POST /api/admin/migrate-flatten
```

### ComfyUI 檔案影響

現有 `.txt` 檔案名稱已使用 `__` 分隔（扁平化結構），遷移後 `Category.name` 與檔名一致，**不需更動任何 `.txt` 檔案**。

---

## Section 3：移除 Pollinations / 新增 OpenAI-compatible

### 移除 Pollinations

| 位置 | 動作 |
|---|---|
| `pollinations_helper.py` | 刪除 |
| `init_translation_settings()` | 移除 pollinations 初始化 block |
| `translation_service.py` | 不實作 pollinations dispatch |
| `translation_settings.html` | 移除 tab |
| DB | `create_app()` 啟動時刪除 provider='pollinations' 的 row（如存在）|

### TranslationSetting Model 新欄位

```python
base_url = db.Column(db.String(500))  # OpenAI-compatible 的 base URL
```

由於無 Alembic，`create_app()` 啟動時執行：

```python
def _add_missing_columns():
    try:
        db.session.execute(text(
            "ALTER TABLE translation_settings ADD COLUMN IF NOT EXISTS base_url VARCHAR(500)"
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()  # SQLite fallback：column 已存在時忽略
```

### OpenAI-compatible Helper：`webapp/helpers/openai_helper.py`

```
class OpenAIHelper:
    __init__(base_url, api_key, model)
    translate_to_chinese(text, system_prompt, temperature) → str | None
    list_models() → list[str]
    check_connection() → bool
```

實作細節：
- 使用 `requests`（不引入 openai SDK）
- 呼叫 `POST {base_url}/chat/completions`（標準 OpenAI 格式）
- `list_models()` → `GET {base_url}/models`，回傳 model id 列表
- `api_key` 為空時不帶 `Authorization` header（相容本地無鑑權服務，如 LM Studio、Ollama /v1）
- timeout: 30s（translate），10s（list_models / check_connection）

### DB 初始化：openai provider 預設值

```python
TranslationSetting(
    provider='openai',
    is_active=False,
    base_url='https://api.openai.com/v1',
    model_name='gpt-4o-mini',
    temperature=0.3,
    system_prompt="你是一個專業的AI繪圖提示詞翻譯助手..."
)
```

### 新增 API Endpoints

```
# 使用頁面上現填的 base_url + api_key 即時掃描（不需先儲存）
POST /api/translation-settings/openai/probe-models
Body: { "base_url": "...", "api_key": "..." }
Response: ["gpt-4o", "gpt-4o-mini", ...]

# 儲存 openai 設定（已有的 PUT /api/translation-settings/<provider> 通用即可）
PUT /api/translation-settings/openai
Body: { base_url, api_key, model_name, temperature, system_prompt }
```

---

## Section 4：UI 設計

### 4-1 首頁（`index.html`）簡化

**移除**：類別統計列表（`category_stats` 圖表區塊）

**保留**：
```
┌──────────┐  ┌──────────┐  ┌──────────┐
│  12,450  │  │  11,200  │  │    48    │
│ 總Wildcard│  │  已啟用  │  │  分類數  │
└──────────┘  └──────────┘  └──────────┘

快速跳轉按鈕列：
[Wildcard 管理]  [匯入資料]  [匯出資料]  [翻譯設定]
```

`/api/stats` 回傳簡化：不需 `category_stats` 陣列，只要三個數字。

### 4-2 整合頁面 `/wildcards`

**版面**：Bootstrap 雙欄（左 `col-3`，右 `col-9`），響應式（小螢幕堆疊）

```
┌─ 左欄 ───────────────────┐ ┌─ 右欄 ─────────────────────────────────────────┐
│ [+ 新增分類]             │ │ [🔍 搜尋___________] [狀態▼] [批量操作▼]       │
│ [🔍 搜尋分類...]         │ │                                                   │
│                           │ │ ☐ 全選    共 234 筆    [← 批量翻譯]              │
│ ● anime_artists  (123)   │ │                                                   │
│   background     (45)    │ │ ☐  a1 artist    一位藝術家    ●啟用   [⋯]        │
│   body_types     (67)    │ │ ☐  a2 artist    未翻譯        ○停用   [⋯]        │
│   ...                    │ │ ☐  ...                                            │
│                           │ │                                                   │
│ ── 選中：anime_artists ── │ │ ────── 分頁 ◀ 1 2 3 ... ▶ ──────               │
│ [✏️ 改名]  [🗑️ 刪除]    │ └───────────────────────────────────────────────────┘
└───────────────────────────┘
```

**左欄互動**：
- 點擊分類 → 右欄載入（highlight 選中項）
- `+ 新增分類` → 左欄頂部 inline input，Enter 確認，Escape 取消
- Hover 顯示 `✏️ 改名` / `🗑️ 刪除`（操作針對當前選中分類）
- 刪除確認 dialog：顯示「將刪除 N 個 wildcard」

**右欄互動**：
- 搜尋 debounce 300ms，即時 filter
- `[⋯]` dropdown：編輯英文內容、編輯中文翻譯、刪除
- 批量操作：全選 → 批量啟用 / 停用 / 翻譯 / 刪除
- 翻譯進行中：row 顯示 spinner；完成後中文欄即時更新

**Navbar 調整**：
- 移除「類別管理」獨立連結
- 「Wildcard 管理」連結保留（指向整合頁）

### 4-3 翻譯設定頁（`translation_settings.html`）

Tabs：`[Ollama]  [Google Gemini]  [OpenAI-compatible]`

**OpenAI-compatible Tab**：
```
Base URL:   [https://api.openai.com/v1_____________]
            提示：本地服務如 LM Studio 填入 http://localhost:1234/v1

API Key:    [•••••••••••••••••••]
            留空 = 無鑑權模式（相容 LM Studio、Ollama /v1 等本地服務）

模型:       [gpt-4o-mini ▼]   [🔍 掃描可用模型]
            ↑ 點擊後使用頁面上當前填入的 base_url + api_key 即時查詢
              成功 → 填入下拉選單 + toast「找到 N 個模型」
              失敗 → toast 顯示錯誤原因

溫度:       [────●────]  0.3

系統提示詞:
┌────────────────────────────────────────┐
│ 你是一個專業的AI繪圖提示詞翻譯助手... │
└────────────────────────────────────────┘

[💾 儲存 OpenAI 設定]
```

---

## Section 5：不在本次範圍

以下項目維持現狀，不在本次實作：
- Alembic 正式資料庫遷移
- 批量操作 SSE 即時進度
- 前端虛擬滾動
- 單元測試
- 深色模式

---

## 實作順序建議

1. 後端重構（Blueprint + Services）— 不改功能，先讓結構正確
2. 移除 Pollinations + 新增 openai_helper + DB 欄位
3. 遷移腳本 migrate_flatten_categories.py
4. 首頁簡化
5. 翻譯設定頁面更新（移除 tab / 新增 tab）
6. 整合頁面 `/wildcards` 重新設計
