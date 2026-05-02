# Personalized Flood Alert System｜個人化淹水預警系統

基於 AI 與多源資料融合的個人化淹水風險預警 app。

## 技術棧

- **前端**：React Native + Expo (TypeScript)
- **後端**：FastAPI + SQLAlchemy 2.0 async (Python)
- **資料庫**：PostgreSQL + PostGIS（Supabase 雲端）
- **Migration**：Alembic
- **LLM**：Anthropic Claude API
- **外部 API**：CWA 中央氣象署開放資料

## 本地開發

```bash
# 1. Clone repo
git clone https://github.com/Claraa1110/personalized-flood-alert.git
cd personalized-flood-alert

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env 填入真實 key

# 3. 啟動後端
docker-compose up

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

- 財產管理：新增並管理個人財產位置（PostGIS 空間查詢）
- 即時雨量監測：串接 CWA 自動雨量站 API（O-A0002-001）
- 新聞 NLP：分析淹水相關新聞
- 風險評估：結合雨量、地形、財產位置計算風險
- 推播通知：風險達閾值時主動通知

## 專案結構

```
FF/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app 入口
│   ├── database.py        # async engine + session
│   ├── dependencies.py    # get_db() 等共用依賴
│   ├── api/               # Routers
│   │   ├── items.py       # 練習用 CRUD
│   │   └── test.py        # 測試 endpoints
│   ├── models/            # SQLAlchemy ORM Models
│   │   ├── property.py
│   │   ├── alert.py
│   │   ├── rainfall.py
│   │   └── news.py
│   ├── schemas/           # Pydantic Schemas
│   │   ├── property.py
│   │   ├── alert.py
│   │   └── rainfall.py
│   └── services/
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
