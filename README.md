# Web_Wildcard_comfyui

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.x-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-compatible-orange.svg)](https://github.com/comfyanonymous/ComfyUI)

**基於 ComfyUI AdaptivePrompts 節點開發的 Web Wildcard 管理系統**

支援多層級分類、AI 翻譯、AI 助手、Danbooru 整合、ComfyUI 工作流執行

[功能特點](#-功能特點) • [快速開始](#-快速開始) • [文檔](#-文檔)

</div>

---

## 💡 專案起源

本專案基於 [ComfyUI AdaptivePrompts](https://github.com/Alectriciti/comfyui-adaptiveprompts) 節點開發，提供完整的 Web 管理介面和資料庫支援，讓 wildcard 管理更加便捷。

---

## ✨ 功能特點

### 🎯 核心功能

- **多層級分類管理** — 樹狀結構組織 wildcard，分類名稱支援中文排序
- **AI 智慧翻譯** — 整合 Ollama / LM Studio / Google Gemini / OpenAI-compatible API，自動翻譯提示詞
- **AI 助手** — 對話式介面，可搜尋 wildcard、批量遷移分類、生成 prompt、直接操作資料庫
- **ComfyUI 工作流執行** — 上傳 API-format workflow JSON，在 Web 介面直接執行並預覽圖片
- **Danbooru 整合** — 搜尋圖片、提取 tag、批量加入 Wildcard DB
- **提示詞構建器** — 三分欄可拖曳介面，整合 Wildcard、Danbooru、Tag DB 三種 tab

### 💡 進階特性

- **批量操作** — 批量匯入、翻譯、啟用/停用、遷移分類
- **多格式支援** — 匯入 TXT/ZIP，匯出 TXT/JSON/CSV/YAML
- **ComfyUI 檔案同步** — 資料庫 ↔ `COMFYUI_WILDCARD_PATH` 扁平 txt 檔
- **Docker 支援** — 一鍵部署，PostgreSQL + Flask

---

## 🚀 快速開始

### 前置需求

- Docker & Docker Compose
- ComfyUI（已安裝 [AdaptivePrompts 節點](https://github.com/Alectriciti/comfyui-adaptiveprompts)）
- (可選) Ollama / LM Studio 用於本地 AI 翻譯與助手

### 安裝步驟

```bash
git clone https://github.com/Boy-II/Web_Wildcard_comfyui.git
cd Web_Wildcard_comfyui

cp .env.example .env
# 編輯 .env，設定 COMFYUI_WILDCARD_PATH、SECRET_KEY 等

docker-compose up -d
# 開啟瀏覽器 http://localhost:9000
```

---

## 📚 主要功能說明

### 1️⃣ Wildcard 管理

- 建立、編輯、刪除 wildcard
- 批量啟用/停用、遷移分類
- 自動去重（`POST /api/wildcards` 重複時回傳 409）
- 支援 Danbooru tag 驗證狀態（valid / deprecated / not_found）

### 2️⃣ 分類系統

- 無限層級樹狀分類；`name` 為機器安全 slug，`display_name` 為人類可讀名稱
- 分類在 API 及頁面均依 `display_name` 中文排序
- 顏色標記、級聯刪除保護
- ComfyUI 檔案命名：`__` 分隔層級（`people__artists__anime_artists.txt`）

### 3️⃣ LLM 設定檔

設定頁面（`/settings`）分兩區：

| 區塊 | 說明 |
|------|------|
| **翻譯功能** | 選擇翻譯 wildcard 時使用的 LLM 設定檔 |
| **AI 助手** | 選擇 AI 助手對話時使用的 LLM 設定檔 |

**支援 Provider：**

| Provider | 說明 |
|----------|------|
| OpenAI-compatible | LM Studio、Ollama `/v1`、OpenAI、任何相容端點 |
| Ollama | Ollama native API |
| Google Gemini | Gemini API（需 API Key）|

### 4️⃣ AI 助手

對話式介面，支援：

- **搜尋 wildcard** — 依分類名稱批量抓取（≤100 筆/批次），或關鍵字搜尋
- **批量遷移分類** — 以 `move_wildcard` action 批量修改 category_id
- **生成 prompt** — 使用 `__分類/子分類__` wildcard 語法
- **新增 / 刪除 wildcard** — 直接操作資料庫
- **修改分類** — 更新 display_name、描述、顏色
- **分批處理** — 超過 100 筆顯示「繼續下一批 N 筆」按鈕

所有操作透過 `<action>JSON</action>` 標籤由 server 自動執行，不需手動貼指令。

### 5️⃣ 提示詞構建器

三欄可拖曳介面（左固定 + 中 + 右可調 180–520px）：

| Tab | 說明 |
|-----|------|
| **Wildcard** | 插入 `__category/sub__` 語法 |
| **Danbooru** | 圖片搜尋 + tag 提取，支援評級/類型過濾 |
| **Tag DB** | 分類樹狀展開，lazy 載入 tag chip |

點擊任何 tag 或 wildcard 均透過 `insertIntoPrompt()` 插入，自動補上逗號。

**支援 AdaptivePrompts 語法：**
```
{$artist=__anime_artists__} a portrait by $artist, $artist style
```

### 6️⃣ ComfyUI 工作流執行

1. 上傳 API-format workflow JSON
2. 在 JSON 中嵌入 `%placeholder%` 變數（`%model%`、`%prompt%`、`%seed%` 等）
3. 在 Web 介面填入參數後執行，前端每 3s 輪詢狀態
4. 完成後預覽圖片（原始比例，不裁切）

### 7️⃣ Danbooru 整合

- 圖片搜尋 + 排行榜（`order:rank`）
- 評級過濾：G / S / Q / E（OR 語法）
- 類型過濾：角色 / 畫師 / 版權 / 一般
- 點擊 tag → 插入提示詞；hover `+` → 新增到 Wildcard DB（預設 `other`/`未分類`/`未整理`）

---

## 🛠️ 技術棧

- **後端**: Python 3.11, Flask 3.x, SQLAlchemy 2.x
- **資料庫**: PostgreSQL（Docker），SQLite（本地開發）
- **前端**: Bootstrap 5.3 dark mode, Vanilla JavaScript（無 build step）
- **AI**: OpenAI-compatible API / Ollama / Google Gemini
- **部署**: Docker Compose

---

## 📖 文檔

- [CLAUDE.md](CLAUDE.md) — 開發指引、架構說明、Blueprint 一覽

---

## 🙏 致謝

- **[ComfyUI AdaptivePrompts](https://github.com/Alectriciti/comfyui-adaptiveprompts)** — 核心節點靈感來源
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) — Stable Diffusion 工作流工具
- [Ollama](https://ollama.ai/) — 本地 AI 支援
- [Google Gemini](https://ai.google.dev/) — 雲端翻譯支援

---

## 📞 聯絡與支援

- **Issues**: [GitHub Issues](https://github.com/Boy-II/Web_Wildcard_comfyui/issues)

---

<div align="center">

**如果這個專案對您有幫助，請給個 ⭐️**

Made with ❤️ for ComfyUI Community

</div>
