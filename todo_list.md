# Wildcard 管理系統 - 待辦事項清單

> 本文件記錄所有待辦功能、bug 修復和改進項目
> 每次修改前請更新此檔案

---

## 📋 目前狀態

**最後更新**: 2025-12-08
**版本**: v1.0.0

---

## 🔴 高優先級 (Critical)

### 功能改進

- [ ] **Wildcard 啟用/停用同步至 ComfyUI**
  - **狀態**: ✅ 已實作 (app.py:421-468)
  - **說明**: 啟用/停用 wildcard 時自動同步到 ComfyUI 檔案系統
  - **實作位置**: `api_update_wildcard()` 函式
  - **功能**:
    - 啟用 (is_active: False → True): 附加內容到對應 .txt 檔案
    - 停用 (is_active: True → False): 從 .txt 檔案移除該行
  - **路徑映射**: 透過 `get_comfy_filepath_for_category()` 計算檔案路徑
  - **待驗證**: 需測試是否正常運作

### Bug 修復

- [ ] **資料庫 Schema 版本管理**
  - **問題**: 更新程式碼後，舊資料庫可能不相容
  - **影響**: 用戶必須手動執行 `docker-compose down -v` 刪除資料
  - **建議解決方案**: 實作 Alembic 資料庫遷移
  - **優先級**: 高
  - **預估工作量**: 4-6 小時

- [ ] **Ollama 連接錯誤處理**
  - **問題**: Ollama 服務未啟動時，錯誤訊息不清楚
  - **建議**: 在翻譯頁面顯示 Ollama 連接狀態
  - **優先級**: 中高
  - **預估工作量**: 2 小時

---

## 🟡 中優先級 (Important)

### 安全性

- [ ] **Gemini API Key 加密儲存**
  - **現狀**: API Key 以明文儲存於 `translation_settings` 表
  - **風險**: 資料庫洩漏會暴露 API Key
  - **解決方案**: 使用 AES-256 加密或環境變數
  - **預估工作量**: 3-4 小時

- [ ] **ComfyUI 路徑驗證**
  - **現狀**: 用戶可透過 API 設定任意路徑
  - **風險**: 路徑穿越攻擊
  - **解決方案**: 驗證路徑必須在允許的目錄內
  - **預估工作量**: 1-2 小時

- [ ] **檔案上傳限制**
  - **現狀**: 無檔案大小限制
  - **建議**:
    - 限制單一檔案 < 10MB
    - 限制 ZIP 解壓後 < 50MB
    - 驗證 MIME type
  - **預估工作量**: 2 小時

### 功能增強

- [ ] **批量操作進度顯示**
  - **需求**: 批量翻譯、匯入時顯示即時進度
  - **技術方案**: WebSocket 或 Server-Sent Events
  - **受益功能**:
    - 批量翻譯 (`/api/wildcards/batch-translate`)
    - 目錄匯入 (`/api/import/directory`)
    - ComfyUI 同步 (`/api/comfy-wildcard/sync`)
  - **預估工作量**: 6-8 小時

- [ ] **Wildcard 去重優化**
  - **現狀**: 只檢查 content 是否存在（全局去重）
  - **問題**: 相同內容可能屬於不同分類
  - **建議**:
    - 選項 1: 分類內去重（已實作：`UNIQUE(category_id, content)`）
    - 選項 2: 允許跨分類重複，但標記為「重複項」
  - **需要討論**: 產品需求
  - **預估工作量**: 2 小時（如果選擇選項 2）

- [ ] **分類拖拉排序 (前端)**
  - **需求**: 在分類管理頁面支援拖拉重新排序
  - **技術**: SortableJS 或 HTML5 Drag & Drop
  - **後端支援**: 已有 `sort_order` 欄位
  - **預估工作量**: 4 小時

---

## 🟢 低優先級 (Nice to Have)

### UI/UX 改進

- [ ] **前端虛擬滾動**
  - **需求**: Wildcard 列表超過 1000 條時效能下降
  - **技術**: Intersection Observer 或 react-window
  - **預估工作量**: 6 小時

- [ ] **深色模式**
  - **需求**: 支援深色主題
  - **技術**: CSS 變數 + Bootstrap 深色主題
  - **預估工作量**: 4 小時

- [ ] **多語言支援 (i18n)**
  - **需求**: 英文、簡體中文介面
  - **技術**: Flask-Babel
  - **預估工作量**: 8-10 小時

### 資料管理

- [ ] **匯出時自訂欄位**
  - **需求**: 匯出 CSV 時可選擇欄位
  - **範例**: 只匯出 content 和 content_zh
  - **預估工作量**: 2 小時

- [ ] **匯入歷史詳細資訊**
  - **需求**: 記錄每次匯入的具體項目
  - **技術**: 新增 `import_history_items` 關聯表
  - **預估工作量**: 3 小時

- [ ] **定期自動備份**
  - **需求**: 每日自動備份資料庫
  - **技術**: Cron job + pg_dump
  - **預估工作量**: 2 小時

### AI 功能

- [ ] **新增翻譯引擎: Claude**
  - **需求**: 支援 Anthropic Claude API
  - **參考**: `ollama_helper.py`, `gemini_helper.py`
  - **預估工作量**: 3-4 小時

- [ ] **新增翻譯引擎: DeepL**
  - **需求**: 支援 DeepL API (專業翻譯)
  - **預估工作量**: 3 小時

- [ ] **AI 輔助分類改進**
  - **現狀**: 使用 Ollama 單次分類
  - **建議**: 批量分類 + 信心分數
  - **預估工作量**: 4 小時

---

## 🔵 技術債務 (Technical Debt)

### 重構

- [ ] **分離業務邏輯與路由**
  - **問題**: `app.py` 過於龐大 (1480 行)
  - **建議結構**:
    ```
    webapp/
    ├── routes/
    │   ├── api/
    │   │   ├── categories.py
    │   │   ├── wildcards.py
    │   │   ├── import_export.py
    │   │   ├── comfy_sync.py
    │   │   └── settings.py
    │   └── pages.py
    ├── services/
    │   ├── category_service.py
    │   ├── wildcard_service.py
    │   ├── import_service.py
    │   └── translation_service.py
    └── models.py
    ```
  - **預估工作量**: 12-16 小時

- [ ] **單元測試覆蓋率**
  - **現狀**: 無測試
  - **目標**: >80% 覆蓋率
  - **工具**: pytest, pytest-flask
  - **預估工作量**: 20-30 小時

- [ ] **API 文件自動生成**
  - **工具**: Flask-RESTX 或 Swagger
  - **好處**: 自動生成 API 文件和測試介面
  - **預估工作量**: 6 小時

### 效能

- [ ] **資料庫查詢優化**
  - **問題**: 部分查詢存在 N+1 問題
  - **位置**:
    - `api_get_wildcards()` - 需要 joinedload
    - `api_stats()` - 可快取結果
  - **預估工作量**: 4 小時

- [ ] **Redis 快取層**
  - **用途**: 快取統計資料、分類樹
  - **技術**: Flask-Caching + Redis
  - **預估工作量**: 6 小時

---

## 🟣 研究項目 (Research)

- [ ] **ComfyUI Plugin 整合**
  - **想法**: 開發 ComfyUI 插件，直接在 ComfyUI 內管理 wildcards
  - **可行性**: 待研究
  - **預估研究時間**: 4 小時

- [ ] **AI 圖像預覽**
  - **想法**: 使用 Stable Diffusion 預覽 wildcard 效果
  - **技術難度**: 高
  - **預估研究時間**: 8 小時

- [ ] **Wildcard 組合推薦**
  - **想法**: AI 推薦搭配良好的 wildcard 組合
  - **技術**: 協同過濾或 LLM
  - **預估研究時間**: 6 小時

---

## ✅ 已完成 (Completed)

### v1.0.0 (2025-12-07 ~ 2025-12-08)

- [x] **基礎架構**
  - [x] Flask + SQLAlchemy + PostgreSQL
  - [x] Docker Compose 部署
  - [x] 資料庫模型設計（5 個表）

- [x] **分類系統**
  - [x] 多層級樹狀分類結構
  - [x] 預設分類樹初始化 (169+ 分類)
  - [x] 自動分類規則 (169+ 規則)

- [x] **Wildcard 管理**
  - [x] CRUD API
  - [x] 批量刪除
  - [x] 批量更新分類
  - [x] 分頁查詢
  - [x] 搜尋篩選

- [x] **AI 翻譯**
  - [x] Ollama 整合
  - [x] Gemini 整合
  - [x] 批量並行翻譯
  - [x] 翻譯設定管理

- [x] **ComfyUI 整合**
  - [x] 目錄掃描
  - [x] 匯入同步（ComfyUI → 資料庫）
  - [x] 匯出同步（資料庫 → ComfyUI）
  - [x] 狀態反向同步

- [x] **匯入/匯出**
  - [x] TXT 檔案匯入
  - [x] ZIP 批量匯入
  - [x] TXT/JSON/CSV 匯出
  - [x] 匯入歷史記錄

- [x] **Web UI**
  - [x] 儀表板（統計）
  - [x] 分類管理頁面
  - [x] Wildcard 瀏覽頁面
  - [x] 匯入頁面
  - [x] 匯出頁面
  - [x] ComfyUI 監控頁面
  - [x] 翻譯設定頁面

- [x] **文件**
  - [x] 完整 README.md（LLM 優化）
  - [x] API 端點文件
  - [x] 工作流程說明
  - [x] 修改注意事項
  - [x] 待辦事項清單 (todo_list.md)

---

## 📝 變更日誌 (Change Log)

### 2025-12-08
- ✅ 建立完整技術文件 (README.md)
- ✅ 建立待辦事項清單 (todo_list.md)
- ✅ 確認 Wildcard 啟用功能已實作（app.py:421-468）
- ✅ 實作類別管理頁面跳轉功能
  - 點擊「查看內容」按鈕可跳轉到 Wildcard 管理頁面
  - 自動帶入該類別 ID 進行篩選
  - 支援從 URL 讀取 `category_id` 和 `search` 參數
  - 修改檔案：`webapp/templates/wildcards.html`
- ✅ 實作批次啟用/停用功能
  - 新增「批次啟用」和「批次停用」按鈕
  - 自動同步到 ComfyUI 檔案系統
  - 前端：`webapp/templates/wildcards.html` (第64-70行，第432-458行)
  - 後端：`app.py` 新增 `/api/wildcards/batch-update-active` API (第521-589行)
- ✅ 實作提示詞構建器 (Prompt Builder)
  - 視覺化界面構建 wildcard 提示詞
  - 支援 comfyui-adaptiveprompts 語法：`__category__` 和 `{option1|option2}`
  - **新增變數系統**：
    - 支援 `{$varname=value}` 定義變數
    - 支援 `$varname` 引用變數
    - 確保提示詞中多處使用相同值（一致性）
    - 變數值可包含 wildcard 或選項語法
  - 即時預覽和多次隨機化生成
  - 預覽結果顯示使用的變數
  - 左側面板：顯示所有可用 wildcard 分類
  - 中間編輯器：提示詞編輯區（含變數輔助按鈕）
  - 右側預覽：即時預覽、變數顯示和多次生成結果
  - 前端：`webapp/templates/prompt_builder.html`
  - 後端：`app.py` (第203-206行, 第1597-1707行)
  - API：
    - `GET /api/prompt-builder/wildcards` - 獲取所有 wildcard 分類和內容
    - `POST /api/prompt-builder/preview` - 預覽提示詞（隨機化，支援變數）
- ✅ **重大變更：實作扁平化檔案結構**
  - **背景**：為配合 ComfyUI wildcard 監視目錄需求，從層級資料夾結構改為扁平化單層結構
  - **檔案命名規則**：使用 `__` (雙底線) 作為路徑分隔符
    - 範例：`people/artists/anime_artists.txt` → `people__artists__anime_artists.txt`
    - 所有 .txt 檔案存放於同一目錄（COMFYUI_WILDCARD_PATH）
  - **資料庫結構**：保持原有多層級分類樹（Category 表的 parent_id 關係不變）
  - **修改函式**：
    - `get_comfy_filepath_for_category()` (app.py:409-429)
      - 產生扁平化檔案名稱
      - 所有檔案寫入同一目錄
    - `get_category_from_filename()` (app.py:432-470)
      - 新增：從扁平化檔案名反推分類
      - 完整路徑比對避免同名衝突
    - `api_scan_comfy_wildcard()` (app.py:1162-1274)
      - 只掃描基礎目錄（不遞迴）
      - 從扁平檔案名建立虛擬樹狀結構供 UI 顯示
    - `api_sync_comfy_wildcard()` (app.py:1277-1400)
      - 從扁平檔案匯入資料
      - 自動創建或查找對應分類
    - `api_sync_status_from_comfy()` (app.py:1403-1465)
      - 只掃描基礎目錄同步啟用狀態
  - **影響範圍**：
    - ✅ 啟用/停用 wildcard 自動同步到正確檔案
    - ✅ 批次啟用/停用功能正常運作
    - ✅ ComfyUI 目錄掃描和同步功能
    - ✅ 狀態反向同步功能
  - **注意事項**：
    - 需要手動遷移現有檔案（或重新匯出）
    - 建議在 ComfyUI 監視目錄設定為單層目錄
    - 檔案名長度限制：Windows 255 字元（深層分類需注意）
- ✅ **修改刪除類別功能**
  - **變更**：允許無論是否存在 wildcard 都可以刪除類別
  - **行為**：
    - 級聯刪除該類別下的所有 wildcard
    - 級聯刪除所有子類別及其 wildcard
    - 自動從 ComfyUI 檔案中移除相關內容
    - 返回刪除統計資訊（wildcard 數量、子類別數量）
  - **修改檔案**：
    - 後端：`app.py` - `api_delete_category()` (第333-390行)
    - 前端：`webapp/templates/categories.html` - `deleteCategory()` (第346-370行)
  - **用戶體驗改進**：
    - 更新確認對話框，明確警告級聯刪除範圍
    - 刪除成功後顯示統計資訊
    - 自動處理 ComfyUI 檔案同步
- ✅ **優化提示詞構建器顯示**
  - **變更**：每個分類下只顯示前 3 個 wildcard 標籤
  - **目的**：改善介面可讀性，避免列表過長
  - **顯示邏輯**：
    - 顯示前 3 個 wildcard（包含英文和中文）
    - 如果超過 3 個，顯示「... 共 X 個選項」
    - 點擊任何項目（包括「更多」）都會插入該分類的 wildcard 語法
  - **修改檔案**：`webapp/templates/prompt_builder.html` (第447-473行)
- ✅ **新增特殊字符插入按鈕**
  - **新增功能**：在提示詞構建器中新增 `|` 和 `^` 兩個快捷按鈕
  - **用途**：
    - `|` 按鈕：快速插入選項分隔符（用於 `{opt1|opt2}` 語法）
    - `^` 按鈕：快速插入權重符號（用於 `keyword^2` 增強權重）
  - **實作**：
    - 新增 `insertCharacter(char)` 函數處理單字符插入
    - 在游標位置插入字符並自動聚焦
    - 更新字數統計
  - **UI 位置**：工具欄中，位於語法按鈕和變數按鈕之間
  - **文檔更新**：
    - 語法說明 Modal 中新增 `|` 和 `^` 的使用說明
    - 快速提示中添加特殊字符的使用範例
  - **修改檔案**：`webapp/templates/prompt_builder.html` (第251-256行、第556-572行、第360-369行、第240行)
- ✅ **整合 Adaptive Prompts 進階語法說明**
  - **來源**：E:\README.md (comfyui-adaptiveprompts 文檔)
  - **新增內容**：
    - 多重選擇語法：`{5$$__fruit__}`, `{2-4$$__animal__|__color__}`
    - 自定義分隔符：`{3$$ and $$__animal__}`
    - 機率權重：`%80% common`, `%10% uncommon`
    - 資料夾 Globbing：`__colors/*__`, `__colors*__`
    - 註解語法：`## 註解內容 ##`
    - Adaptive 變數語法：`__fruit^a__`, `__^a__`, `__^a*__`
    - 唯一變數賦值：`{opt1|opt2}^var1^var2^var3`
  - **使用範例**：完整的進階範例和 Adaptive Prompts 變數範例
  - **修改檔案**：`webapp/templates/prompt_builder.html` (第387-445行)
- ✅ **Ollama 翻譯效能優化**
  - **硬體環境**：RTX 5080 16GB，模型 Qwen3:8b Q4_K_M（約 5GB）
  - **問題**：翻譯速度慢，未充分利用 GPU 資源
  - **優化方案**：
    - **並行處理**：OLLAMA_NUM_PARALLEL 從 1 增加到 12（同時處理 12 個請求）
    - **請求隊列**：OLLAMA_MAX_QUEUE 從預設增加到 30
    - **後端線程**：Python ThreadPoolExecutor max_workers 從 4 增加到 12
    - **模型保留**：OLLAMA_KEEP_ALIVE 設為 10m（避免重複載入）
    - **模型限制**：OLLAMA_MAX_LOADED_MODELS 設為 1（專注翻譯）
  - **預期效果**：
    - 批次翻譯速度提升約 3 倍（4 → 12 並發）
    - GPU 利用率提升（充分利用 16GB 記憶體）
    - 翻譯延遲降低（排隊機制優化）
  - **修改檔案**：
    - `docker-compose.yml`（Ollama 環境變數）
    - `ollama_helper.py`（max_workers: 4 → 12）
    - `gemini_helper.py`（max_workers: 4 → 12）

### 2025-12-07
- ✅ 初始專案架構完成
- ✅ 所有核心功能實作完成
- ✅ Docker 環境配置完成

---

## 🎯 近期計畫 (Roadmap)

### Sprint 1 (1-2 週)
1. 驗證並修復 Wildcard 啟用同步功能
2. 實作 Gemini API Key 加密儲存
3. 加入檔案上傳限制
4. 新增批量操作進度顯示

### Sprint 2 (3-4 週)
1. 重構 app.py，分離業務邏輯
2. 實作基礎單元測試
3. 前端虛擬滾動優化
4. 資料庫查詢效能優化

### Sprint 3 (5-6 週)
1. 實作 Alembic 資料庫遷移
2. API 文件自動生成
3. 深色模式支援
4. Claude 翻譯引擎整合

---

## 📌 注意事項

### 修改前檢查清單
- [ ] 閱讀 README.md 相關章節
- [ ] 更新此 todo_list.md
- [ ] 確認資料庫 schema 變更是否需要遷移
- [ ] 執行本地測試
- [ ] 更新 CHANGES.md

### 提交前檢查清單
- [ ] 程式碼符合 PEP 8 規範
- [ ] 新增或更新註解
- [ ] 測試所有相關 API 端點
- [ ] 更新文件（如有必要）
- [ ] Git commit message 清晰描述變更

---

**維護者**: [Your Name]
**聯絡方式**: [Your Email]
