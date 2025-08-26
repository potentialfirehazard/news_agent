# 使用 Python 3.11（slim）作為基礎映像
FROM python:3.11-slim

# 設定時區與 Python 執行環境
ENV TZ=Asia/Taipei \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 安裝必要系統套件（含 tzdata、lxml 依賴）
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    build-essential \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 複製相依檔並安裝套件（先複製 requirements 提高快取命中率）
COPY requirements.txt .

RUN pip install --upgrade pip==24.2 \
 && pip install -r requirements.txt

# 複製專案原始碼
COPY . .

# 預設使用環境變數注入 MongoDB 連線字串
# 可被 docker-compose.yml 覆蓋
ENV MONGODB_CONNECTION_STRING="mongodb://localhost:27017"

# 預設啟動指令（若主程式不是 main.py 請同步修改 compose 的 command）
CMD ["python", "main.py"]