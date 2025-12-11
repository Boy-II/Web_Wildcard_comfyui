# 快速啟動指南

## 🚀 5 分鐘快速開始

### 步驟 1: 啟動服務

```bash
cd /Volumes/M200/project/wildcard
docker-compose up -d
```

### 步驟 2: 等待服務就緒

```bash
# 查看日誌，確認服務啟動成功
docker-compose logs -f web

# 看到以下訊息表示成功：
# * Running on http://0.0.0.0:5000
```

### 步驟 3: 訪問網頁介面

開啟瀏覽器，訪問: **http://localhost:5000**

### 步驟 4: 匯入測試資料

1. 點擊導航欄的「匯入資料」
2. 在目錄路徑欄位保持預設值 `sample_file/wildcards`
3. 點擊「開始匯入」按鈕
4. 等待匯入完成

### 步驟 5: 瀏覽資料

1. 回到首頁查看統計資訊
2. 點擊「Wildcard 列表」瀏覽所有匯入的資料
3. 使用搜尋和篩選功能查找特定內容

## 📋 主要功能

### 1. 首頁儀表板
- 查看總覽統計
- 各類別分布圖表

### 2. Wildcard 列表
- 分頁瀏覽所有資料
- 搜尋特定內容
- 依類別篩選
- 批量刪除

### 3. 類別管理
- 查看所有類別
- 查看每個類別的項目數量

### 4. 匯入資料
- 從目錄匯入 TXT 檔案
- 從 ZIP 檔案匯入
- 自動去重
- 智慧分類

### 5. 匯出資料
- 匯出為 TXT 格式
- 匯出為 JSON 格式
- 匯出為 CSV 格式

## 🔧 命令列工具

### 使用 Python 腳本匯入

```bash
# 方法 1: 在容器中執行
docker-compose exec web python import_data.py sample_file/wildcards

# 方法 2: 本機執行（需要先安裝依賴）
python import_data.py sample_file/wildcards

# 從 ZIP 匯入
python import_data.py sample_file/ccsWildcards_v11.zip
```

## 🛠️ 常用操作

### 查看服務狀態
```bash
docker-compose ps
```

### 查看日誌
```bash
# 所有服務
docker-compose logs -f

# 只看 Web 服務
docker-compose logs -f web

# 只看資料庫
docker-compose logs -f db
```

### 重啟服務
```bash
docker-compose restart
```

### 停止服務
```bash
docker-compose down
```

### 完全清除（包括資料庫）
```bash
docker-compose down -v
```

### 備份資料庫
```bash
docker-compose exec db pg_dump -U wildcard_user wildcard_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 恢復資料庫
```bash
docker-compose exec -T db psql -U wildcard_user wildcard_db < backup.sql
```

## 🐛 故障排除

### 問題: 無法訪問 http://localhost:5000

**解決方法:**
1. 檢查服務是否啟動: `docker-compose ps`
2. 檢查日誌: `docker-compose logs web`
3. 確認端口沒有被佔用: `lsof -i :5000`

### 問題: 資料庫連接失敗

**解決方法:**
1. 確認資料庫容器啟動: `docker-compose ps db`
2. 查看資料庫日誌: `docker-compose logs db`
3. 重啟服務: `docker-compose restart`

### 問題: 匯入時發生錯誤

**解決方法:**
1. 確認檔案路徑正確
2. 確認檔案編碼為 UTF-8
3. 查看詳細錯誤訊息

## 📚 進階使用

### 自訂分類規則

編輯 `app.py` 中的 `categorize_filename` 函數，新增您的分類規則。

### 修改資料庫連接

編輯 `docker-compose.yml` 中的環境變數：

```yaml
environment:
  - DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

### 使用 SQLite（不需要 Docker）

```bash
export DATABASE_URL=sqlite:///data/wildcard.db
python app.py
```

## 📞 需要幫助？

查看完整文件: [README.md](README.md)

---

祝您使用愉快！🎉
