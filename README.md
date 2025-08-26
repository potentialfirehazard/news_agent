# 📰 News Fetcher

一個自動抓取新聞 RSS、進行網頁爬蟲、存入 MongoDB，並執行情感分析與去重比對的程式。  
本專案使用 **Docker Compose** 部署，包含三個服務：
- **app**：Python 爬蟲與分析程式
- **mongo**：MongoDB 資料庫
- **mongo-express**：Web 管理介面

---

## 🚀 安裝流程

### 1. 前置需求
- 安裝 [Docker](https://docs.docker.com/get-docker/) (Engine 20+ 或 Docker Desktop 最新版)  
- 安裝 [Docker Compose](https://docs.docker.com/compose/install/) (v2 以上)

檢查：
```bash
docker --version
docker compose version
```

---

### 2. 取得專案
解壓縮專案 zip：
```bash
unzip news-fetcher.zip
cd news-fetcher
```

專案結構：
```
news-fetcher/
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
├─ main.py
├─ parsing/
│  ├─ html_scraper.py
│  ├─ sentiment_analysis.py
│  └─ deduplication.py
└─ data/
   └─ keyword_filter_set_zh.csv
```

---

### 3. 設定環境變數
建立 `.env` 檔案，僅需設定 MongoDB 帳密：

```
MONGO_INITDB_ROOT_USERNAME=root
MONGO_INITDB_ROOT_PASSWORD=example-strong-password
```

> ⚠️ 不需要設定 `OPENAI_API_KEY`，它已經寫死在 `docker-compose.yml`。  
> ⚠️ 建議將 Mongo 密碼換成安全字串。  

---

### 4. 建置與啟動
第一次啟動需先建置：
```bash
docker compose build
docker compose up -d
```

這會啟動三個服務：
- `mongo` → MongoDB
- `app` → 爬蟲程式
- `mongo-express` → Web 管理介面 (http://localhost:8081)

---

## 🔍 使用方法

### 查看容器狀態
```bash
docker compose ps
```

### 查看程式日誌
```bash
docker compose logs -f app
```

### 手動觸發抓取
```bash
docker exec -it news-fetcher python main.py
```

### 進入 Mongo CLI
```bash
docker exec -it mongo mongosh -u root -p <你的密碼> --authenticationDatabase admin
```

查詢範例：
```javascript
use news_info
db.article_info.countDocuments()
db.article_info.findOne()
```

### 使用 Web 管理介面
打開瀏覽器：
👉 http://localhost:8081  
即可透過圖形化介面查看資料。

---

## ⚙️ 日常操作

- 啟動  
  ```bash
  docker compose up -d
  ```
- 停止  
  ```bash
  docker compose down
  ```
- 重建（修改了 Dockerfile 或 requirements）  
  ```bash
  docker compose build app
  docker compose up -d
  ```
- 只重啟 App  
  ```bash
  docker compose restart app
  ```

---

## 💾 資料保存
- MongoDB 資料存在 volume `mongo-data` 中，刪除容器不會消失。  
- 若要清空（⚠️會刪光所有資料）：  
  ```bash
  docker compose down -v
  ```

---

## ✅ 總結
1. 安裝 Docker + Compose  
2. 解壓縮專案並進入目錄  
3. 建立 `.env`（只放 Mongo 帳密，不需 OpenAI Key）  
4. `docker compose build && docker compose up -d`  
5. 打開 http://localhost:18081 或用 `mongosh` 查資料  

---


## Description

News Agent will scrape 350 articles at 3 scheduled times a day (07:30, 13:30, 18:00  UTC+8) from a list of sources. The sources are split into high priority and low priority categories, and the high priority list is fetched first. The low priority list will be fetched after, and the rest of the articles needed to meet the 350 quota will be scraped from PTT Stock Board. The articles are checked for keywords and skipped if no keywords are found, and they are also checked against the articles already in the database to see if there is already a duplicate in the database. If a duplicate is found, the article is skipped. Information from these articles are stored in the "article_info" collection in the database. After parsing, the articles go through deduplication through TF-IDF or SBERT vectorization and cosine similarity. Most exact duplicates should have already been skipped, so this step would be for removing articles on similar topics. There is a threshold parameter to control what similarity score is considered too high, which allows for customization of how similar articles must be for removal. After deduplication, the articles go through sentiment analysis via concurrent calls to OpenAI. This creates three documents for each article: one for general sentiment analysis, one for detail on the confidence score given, and one for entity matches. These are each stored in a separate collection, and each parsed article is linked to its three connecting analysis files by the "id" field in each document.    
Python Version 3.11.9

## Components

main.py handles the scheduling of runs and all RSS parsing, as well as calling functions from other modules.  
Parsing folder contains the following modules:  
- html_scraper.py: handles all html parsing using BeautifulSoup  
- deduplication.py: handles deduplication via tf-idf or sbert vectorization and cosine similarity.  
- sentiment_analysis.py: gets responses from OpenAI to analyze the news scraped from main.py

## Configurables:

- deduplication.py— tfidf_comparison /sbert_comparison— either can be utilized
- deduplication.py — tfidf_comparison/sbert_comparison—threshold parameter can be changed when the function is called depending on what similarity score is considered “too similar”
- html_scraper.py—find_text_by_name/find_text_by_id/find_text_by_class—can all be utilized to find the body text in p tags within the tag identified by name, id, or class.
- main.py—connection_string—replace with the connection string of the desired MongoDB database
- main.py—database_name—replace with the name of the desired database
- sentiment_analysis.py—async_analyze—will require OpenAI key, currently is using a key saved to my environment

## Testing:

- **main.py** — To test: run the daily_fetch() function, errors/time taken for each step are logged. — Expected result: fetches information from 350 articles each run, 3 runs scheduled per day—Note: the functions in main.py rely on other modules (deduplication.py, sentiment_analysis.py, html_scraper.py)
- **html_scraper.py**—To test: run the file (has logic to run on its own)—Expected result: PTT scraping functions gather information from a specific amount of articles and stores in MongoDB. Functions to get body text can be tested with the fetch() function in main.py.
- **deduplication.py**—To test: run the file (has logic to run on its own)— Expected result: Removes duplicates from a MongoDB collection. Titles of deleted articles are logged and can be used to determine if the deduplication logic is running properly.
- **sentiment_analysis.py**—To test: run the file (has logic to run on its own)—Expected result: gets OpenAI responses to analyze all documents from the specified start index, stores 3 types of results (entity match, sentiment analysis, confidence score detail) in 3 different collections.
