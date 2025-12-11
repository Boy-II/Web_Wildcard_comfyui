# Wildcard Management System

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.x-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-compatible-orange.svg)](https://github.com/comfyanonymous/ComfyUI)

**基於 ComfyUI AdaptivePrompts 節點開發的 Wildcard 提示詞管理系統**

支援多層級分類、AI 翻譯、Web 管理介面

[功能特點](#-功能特點) • [快速開始](#-快速開始) • [截圖展示](#-截圖展示) • [文檔](#-文檔)

</div>

---

## 💡 專案起源

本專案基於 [ComfyUI AdaptivePrompts](https://github.com/Alectriciti/comfyui-adaptiveprompts) 節點開發，提供完整的 Web 管理介面和資料庫支援，讓 wildcard 管理更加便捷。

### 主要增強
- ✅ Web UI 管理介面
- ✅ 資料庫持久化儲存
- ✅ AI 智慧翻譯整合
- ✅ 多層級分類系統
- ✅ 批量操作功能
- ✅ ComfyUI 檔案系統雙向同步

---

## ✨ 功能特點

### 🎯 核心功能
- **多層級分類管理** - 樹狀結構組織您的 wildcard，支援無限層級
- **AI 智慧翻譯** - 整合 Ollama 和 Google Gemini，自動翻譯提示詞
- **智慧自動分類** - 169+ 條內建規則，自動識別並分類 wildcard
- **ComfyUI 完美整合** - 與 AdaptivePrompts 節點完美配合，雙向同步
- **提示詞構建器** - 視覺化界面，支援變數系統和即時預覽

### 💡 進階特性
- **批量操作** - 批量匯入、翻譯、啟用/停用
- **多格式支援** - 匯入 TXT/ZIP，匯出 TXT/JSON/CSV
- **即時同步** - 資料庫與 ComfyUI 檔案系統即時同步
- **Web UI 管理** - 現代化的 Web 介面，簡單易用
- **Docker 支援** - 一鍵部署，包含資料庫和 AI 服務

---

## 🚀 快速開始

### 前置需求
- Docker & Docker Compose
- ComfyUI（已安裝 [AdaptivePrompts 節點](https://github.com/Alectriciti/comfyui-adaptiveprompts)）
- (可選) NVIDIA GPU 用於本地 AI 翻譯

### 安裝步驟

1. **Clone 專案**
```bash
git clone https://github.com/yourusername/wildcard.git
cd wildcard
```

2. **設定環境變數**
```bash
cp .env.example .env
# 編輯 .env，設定 ComfyUI wildcard 目錄路徑
```

3. **啟動服務**
```bash
docker-compose up -d
```

4. **訪問應用**
打開瀏覽器訪問: `http://localhost:9000`

5. **設定 ComfyUI 路徑**
在設定頁面中配置您的 ComfyUI wildcard 目錄路徑

就是這麼簡單！🎉

---

## 📸 截圖展示

### 儀表板
> 一目了然的統計資訊和快速操作

### 分類管理
> 樹狀結構，拖拉排序，直觀管理

### Wildcard 瀏覽
> 搜尋、篩選、批量操作

### 提示詞構建器
> 視覺化組合提示詞，支援 AdaptivePrompts 語法

### AI 翻譯
> 一鍵翻譯，支援批量處理

### ComfyUI 整合
> 與 AdaptivePrompts 節點即時同步

*註：截圖即將添加*

---

## 🎨 使用場景

### ComfyUI + AdaptivePrompts 用戶
- 通過 Web 介面管理 AdaptivePrompts wildcard
- 使用資料庫組織大量提示詞
- AI 自動翻譯和分類
- 與 ComfyUI 工作流無縫整合

### 內容創作者
- 組織和分類提示詞庫
- 批量翻譯英文提示詞為中文
- 匯出為不同格式供其他工具使用

### 團隊協作
- 集中管理團隊的提示詞資源
- 自動分類和去重
- Web 介面方便多人使用

---

## 📚 主要功能說明

### 1️⃣ Wildcard 管理
- 建立、編輯、刪除 wildcard
- 批量啟用/停用
- 自動去重機制
- 標籤和備註支援

### 2️⃣ 分類系統
- 無限層級的樹狀分類
- 拖拉排序
- 顏色標記
- 級聯刪除保護

### 3️⃣ AI 翻譯
**支援兩種翻譯引擎：**

**Ollama (本地)**
- 完全免費
- 隱私保護
- 支援 GPU 加速
- 推薦模型：qwen3:8b

**Google Gemini (雲端)**
- 高品質翻譯
- 無需本地 GPU
- 需要 API Key

### 4️⃣ ComfyUI 整合
- **扁平化文件結構** - 相容 AdaptivePrompts 節點要求
- **檔案命名規則** - 使用 `__` 編碼分類層級（如：`people__artists__anime_artists.txt`）
- **雙向同步** - 資料庫 ↔ ComfyUI 檔案系統
- **狀態追蹤** - 自動更新啟用/停用狀態

### 5️⃣ 提示詞構建器
**完全支援 AdaptivePrompts 語法：**
- `__category__` - 從分類中隨機選擇
- `{option1|option2}` - 從選項中隨機選擇
- `{$var=value}` - 定義變數
- `$var` - 引用變數

**範例：**
```
{$artist=__anime_artists__} a beautiful portrait by $artist, $artist style
```

---

## 🛠️ 技術棧

- **後端**: Python 3.11, Flask 3.x, SQLAlchemy 2.x
- **資料庫**: PostgreSQL 15
- **前端**: HTML5, Bootstrap 5, Vanilla JavaScript
- **AI**: Ollama (本地), Google Gemini (雲端)
- **部署**: Docker Compose

---

## 📖 文檔

- [快速開始指南](QUICKSTART.md) - 5 分鐘上手
- [使用指南](USAGE_GUIDE.md) - 詳細功能說明
- [技術文檔](TECHNICAL.md) - 完整技術細節和 API 文檔
- [ComfyUI 整合指南](COMFY_MONITOR_GUIDE.md) - AdaptivePrompts 整合說明
- [更新日誌](CHANGES.md) - 版本更新記錄

---

## 🤝 貢獻

歡迎貢獻！請查看貢獻指南

### 開發者
如果您想參與開發，請參閱：
- [技術文檔](TECHNICAL.md) - 系統架構和 API 說明
- [測試清單](TESTING_CHECKLIST.md) - 測試指引

---

## 📝 授權

本專案採用 MIT License

---

## 🙏 致謝

本專案基於以下優秀的開源項目：

- **[ComfyUI AdaptivePrompts](https://github.com/Alectriciti/comfyui-adaptiveprompts)** - 核心節點靈感來源
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - 強大的 Stable Diffusion 工作流工具
- [Ollama](https://ollama.ai/) - 本地 AI 支援
- [Google Gemini](https://ai.google.dev/) - 雲端翻譯支援

---

## 📞 聯絡與支援

- **Issues**: [GitHub Issues](https://github.com/yourusername/wildcard/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/wildcard/discussions)

---

<div align="center">

**如果這個專案對您有幫助，請給個 ⭐️**

Made with ❤️ for ComfyUI Community

</div>
