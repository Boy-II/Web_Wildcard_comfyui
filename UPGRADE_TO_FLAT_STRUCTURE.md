# 升級到扁平化檔案結構指南

## 問題說明

如果您發現啟用 wildcard 時還是在創建資料夾結構（例如 `people/artists/anime_artists.txt`），這是因為 Docker 容器還在運行舊代碼。

## 解決步驟

### 1. 停止並重啟 Docker 容器

```bash
# 停止現有容器
docker-compose down

# 重新啟動（會載入新代碼）
docker-compose up -d

# 檢查日誌確認啟動成功
docker-compose logs -f web
```

### 2. 驗證新代碼是否生效

啟用一個 wildcard 後，檢查 Docker 日誌：

```bash
docker-compose logs web | grep "扁平化"
```

應該看到類似輸出：
```
[扁平化] 啟用 Wildcard:
  - 基礎目錄: /app/comfy_wildcard
  - 檔案名: people__artists__anime_artists.txt
  - 完整路徑: /app/comfy_wildcard/people__artists__anime_artists.txt
```

### 3. 清理舊的資料夾結構（可選）

如果想清理舊的資料夾結構，可以：

#### 選項 A: 手動清理
```bash
# 進入容器
docker-compose exec web bash

# 檢查目前結構
ls -la /app/comfy_wildcard/

# 刪除舊的資料夾（請謹慎！）
rm -rf /app/comfy_wildcard/*/

# 只保留 .txt 檔案
# (扁平化的檔案已經在根目錄)
```

#### 選項 B: 使用系統重新同步

1. 登入 Web UI
2. 進入「ComfyUI 監視」頁面
3. 點擊「清除所有資料」（會清除資料庫並重新初始化分類）
4. 點擊「從資料庫匯出到 ComfyUI」（會重新生成扁平化檔案）

## 驗證扁平化結構

正確的檔案結構應該是：

```
/app/comfy_wildcard/
├── people__artists__anime_artists.txt
├── people__artists__digital_artists.txt
├── places__cities__tokyo.txt
└── places__nature__mountains.txt
```

**錯誤的結構**（舊版）：
```
/app/comfy_wildcard/
├── people/
│   └── artists/
│       ├── anime_artists.txt
│       └── digital_artists.txt
└── places/
    ├── cities/
    │   └── tokyo.txt
    └── nature/
        └── mountains.txt
```

## 測試

測試腳本已包含在 `test_flat_path.py`：

```bash
# 在宿主機運行
python test_flat_path.py

# 或在容器內運行
docker-compose exec web python test_flat_path.py
```

應該看到所有測試通過：
```
✅ 檔案名正確
✅ 完整路徑正確
✅ 檔案名不包含路徑分隔符
```

## 疑難排解

### 重啟後還是看到資料夾結構

1. **確認代碼版本**：
   ```bash
   docker-compose exec web grep -A 5 "def get_comfy_filepath_for_category" app.py
   ```
   應該看到註解包含「扁平結構」字樣

2. **檢查是否有緩存的 Python bytecode**：
   ```bash
   docker-compose exec web find . -name "*.pyc" -delete
   docker-compose exec web find . -name "__pycache__" -type d -exec rm -rf {} +
   docker-compose restart web
   ```

3. **完全重建容器**：
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

### 舊檔案和新檔案同時存在

這是正常的過渡狀態。您可以：

1. 保留舊檔案（不影響新系統）
2. 手動刪除舊資料夾
3. 使用「清除所有資料」功能重新開始

## 注意事項

- ✅ 資料庫結構保持不變（仍然是多層級分類樹）
- ✅ 所有 API 端點繼續正常工作
- ✅ Web UI 功能不受影響
- ⚠️ 如果有外部腳本直接讀取 ComfyUI 目錄，需要更新以支援扁平化結構

## 支援

如果問題持續存在，請：

1. 提供 `docker-compose logs web` 輸出
2. 提供 `ls -la /app/comfy_wildcard/` 輸出
3. 提供啟用 wildcard 時的日誌輸出

---

**最後更新**: 2025-12-08
