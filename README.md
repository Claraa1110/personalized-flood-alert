# Personalized Flood Alert System｜個人化淹水預警系統

基於 AI 與多源資料融合的個人化淹水風險預警 app。

## 技術棧

- **前端**：React Native + Expo (TypeScript)
- **後端**：FastAPI + SQLAlchemy 2.0 async (Python)
- **資料庫**：PostgreSQL + PostGIS（Supabase 雲端）
- **Migration**：Alembic
- **排程**：APScheduler（AsyncIOScheduler）
- **LLM**：OpenRouter API（gpt-4o-mini）
- **外部 API**：CWA 中央氣象署開放資料、RSS 新聞來源

## 本地開發

```bash
# 1. Clone repo
git clone https://github.com/Claraa1110/personalized-flood-alert.git
cd personalized-flood-alert

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env 填入真實 key

# 3. 啟動後端
uv run uvicorn app.main:app --reload

# 4. 啟動前端
cd MobileApp
npx expo start
```

後端 API 文件：`http://localhost:8000/docs`

## 資料庫 Migration

```bash
# 建立新 migration
uv run alembic revision --autogenerate -m "description"

# 套用 migration
uv run alembic upgrade head

# 回滾一個版本
uv run alembic downgrade -1
```

## 主要功能

- 財產管理：新增並管理個人財產位置，自動查詢行政區與淹水潛勢等級（PostGIS 空間查詢）
- 行政區查詢：根據座標查詢對應鄉鎮市區（全台 368 個行政區）
- 淹水潛勢查詢：根據座標查詢 24 小時 200mm 情境下的淹水風險等級（全台 22 縣市）
- 即時雨量監測：串接 CWA 自動雨量站 API（O-A0002-001），每 10 分鐘自動排程更新，支援 QPE 雷達格點與實體雨量站雙來源
- 新聞監測：每小時抓取 RSS 新聞，透過 LLM 分類淹水相關新聞並抽取台灣地名，進行地理定位
- 風險評估引擎：每 10 分鐘自動評估所有財產，綜合雨量、淹水潛勢等級、附近新聞訊號計算風險分數
- 警報系統：風險達閾值（notice/warning/emergency）時自動寫入警報，支援查詢與已讀標記

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | /api/properties | 新增財產（自動填入行政區與淹水等級） |
| GET | /api/properties | 查詢財產列表 |
| GET | /api/properties/{id} | 查詢單筆財產 |
| PUT | /api/properties/{id} | 修改財產 |
| DELETE | /api/properties/{id} | 刪除財產 |
| GET | /api/location/district | 根據座標查詢行政區 |
| GET | /api/location/flood-risk | 根據座標查詢淹水潛勢等級 |
| GET | /api/rainfall | 查詢座標附近即時雨量（QPE + 雨量站） |
| GET | /api/alerts | 查詢使用者所有財產的警報列表 |
| GET | /api/alerts/{id} | 查詢單一警報詳情（自動標記已讀） |
| POST | /api/alerts/evaluate | 手動觸發風險評估 |
| GET | /health/scheduler | 排程系統健康檢查 |

## 資料來源

- 行政區界線：內政部鄉鎮市區界線（114年版）
- 淹水潛勢圖：經濟部水利署 24 小時 200mm 情境（22 縣市）
- 即時雨量：CWA 自動雨量站（O-A0002-001）
- QPE 雷達降雨估算：CWA（O-B0045-001）
- 新聞來源：自由時報、聯合新聞網、Google 新聞（RSS）

## 專案結構

```
FF/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app 入口
│   ├── database.py        # async engine + session
│   ├── dependencies.py    # get_db() 等共用依賴
│   ├── scheduler.py       # APScheduler 排程設定
│   ├── api/               # Routers
│   │   ├── properties.py  # 財產 CRUD
│   │   ├── location.py    # 行政區 & 淹水潛勢查詢
│   │   ├── rainfall.py    # 雨量查詢
│   │   ├── alerts.py      # 警報查詢
│   │   └── test.py        # 測試 endpoints
│   ├── models/            # SQLAlchemy ORM Models
│   │   ├── property.py
│   │   ├── district.py
│   │   ├── flood_risk.py
│   │   ├── alert.py
│   │   ├── rainfall.py
│   │   └── news.py
│   ├── schemas/           # Pydantic Schemas
│   │   ├── property.py
│   │   ├── alert.py
│   │   └── rainfall.py
│   └── services/
│       ├── cwa_service.py  # CWA API 串接 & 雨量資料寫入
│       ├── news_service.py # RSS 新聞抓取、LLM 分類、地名抽取
│       ├── llm_service.py  # OpenRouter LLM 呼叫
│       └── risk_engine.py  # 風險評估引擎 & 警報產生
├── scripts/               # 資料匯入腳本
│   ├── import_districts.py
│   ├── import_flood_risk.py
│   └── import_all_flood_risk.py
├── data/                  # Shapefile 資料（不進 git）
├── alembic/               # Migration 管理
│   └── versions/
├── MobileApp/             # Expo 前端
│   └── src/
│       ├── navigation/
│       └── screens/
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml         # uv 套件管理
├── .env                   # 不進 git
├── .env.example           # 進 git
└── README.md
```
