# Personalized Flood Alert System｜個人化淹水預警系統

基於 AI 與多源資料融合的個人化淹水風險預警 App，使用者可登記財產位置，系統自動監測雨量、評估風險並推播通知。

## 技術棧

- **前端**：React Native + Expo SDK 54（TypeScript），EAS Build 部署
- **後端**：FastAPI + SQLAlchemy 2.0 async（Python）
- **資料庫**：PostgreSQL + PostGIS（Supabase 雲端）
- **Migration**：Alembic
- **排程**：APScheduler（AsyncIOScheduler）
- **推播通知**：Expo Push Notifications（FCM / APNs）
- **LLM**：OpenRouter API（gpt-4o-mini）
- **外部 API**：CWA 中央氣象署開放資料（雨量站、鄉鎮預報 F-D0047）、CODIS 逐小時雨量、RSS 新聞
- **部署**：Fly.io

## 主要功能

- **裝置識別**：每台裝置產生唯一 UUID 存於 AsyncStorage，以 `X-Device-Id` header 識別，無需帳號
- **財產管理**：新增並管理個人財產位置，自動查詢行政區與淹水潛勢等級（PostGIS 空間查詢）
- **即時雨量監測**：串接 CWA 雨量站 API，每 10 分鐘自動更新，支援 QPE 雷達格點與實體雨量站雙來源
- **警戒門檻校正**：依水利署（WRA）兩級警戒門檻（lv1 警戒 / lv2 預警），透過 LLM 抽取歷史淹水新聞對應實際雨量，自動校正門檻至鄉鎮層級
- **鄉鎮天氣預報**：串接 CWA F-D0047 鄉鎮預報，顯示未來 6 小時降雨機率與即時氣溫
- **風險評估引擎**：每 10 分鐘評估所有財產，綜合雨量、淹水潛勢等級、鄰近新聞計算風險分數
- **警報系統**：風險達閾值時自動寫入警報並推播通知（FCM / APNs）
- **隱私政策**：內建 `/privacy` 頁面，符合 App Store / Google Play 上架要求

## 本地開發

```bash
# 1. Clone repo
git clone https://github.com/Claraa1110/personalized-flood-alert.git
cd personalized-flood-alert

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env 填入真實 key

# 3. 啟動後端（port 8001）
uv run uvicorn app.main:app --reload --port 8001

# 4. 啟動前端
cd MobileApp
npx expo start
```

後端 API 文件：`http://localhost:8001/docs`

## 資料庫 Migration

```bash
# 建立新 migration
uv run alembic revision --autogenerate -m "description"

# 套用 migration
uv run alembic upgrade head

# 回滾一個版本
uv run alembic downgrade -1
```

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /health | 健康檢查 |
| GET | /health/scheduler | 排程系統狀態 |
| POST | /api/properties | 新增財產 |
| GET | /api/properties | 查詢財產列表 |
| GET | /api/properties/{id} | 查詢單筆財產 |
| PUT | /api/properties/{id} | 修改財產 |
| DELETE | /api/properties/{id} | 刪除財產 |
| GET | /api/properties-with-risk | 財產列表含即時風險分數 |
| GET | /api/location/district | 根據座標查詢行政區 |
| GET | /api/location/flood-risk | 根據座標查詢淹水潛勢等級 |
| GET | /api/rainfall | 查詢座標附近即時雨量 |
| GET | /api/forecast | 查詢座標所在鄉鎮天氣預報（降雨機率 + 氣溫） |
| GET | /api/geocode | 地址轉座標 |
| GET | /api/alerts | 查詢警報列表 |
| GET | /api/alerts/{id} | 查詢單一警報（自動標記已讀） |
| POST | /api/alerts/evaluate | 手動觸發風險評估 |
| GET | /api/thresholds | 查詢鄉鎮警戒門檻 |
| POST | /api/push-tokens | 登錄推播 token |
| GET/PUT | /api/notification-settings | 查詢 / 更新推播設定 |
| GET | /privacy | 隱私政策頁面（HTML） |

## 門檻校正說明

系統以鄉鎮為單位，從水利署原始警戒門檻出發，透過下列流程自動校正：

1. LLM 從歷史新聞抽取「地點 + 淹水時間」
2. CODIS 下載對應測站的逐小時雨量，反推 1h/3h/6h 累積值
3. 篩選「實際雨量 ≥ 60% 門檻且未超標」的高品質事件
4. 以事件最低雨量作為校正後門檻（保守取 MIN）
5. 維持單調性：6h ≥ 3h ≥ 1h

## 資料來源

| 資料 | 來源 |
|------|------|
| 行政區界線 | 內政部鄉鎮市區界線（114年版） |
| 淹水潛勢圖 | 經濟部水利署 24h 200mm 情境 |
| 警戒門檻 | 經濟部水利署（WRA）兩級警戒標準 |
| 即時雨量 | CWA 自動雨量站（O-A0002-001）、QPE（O-B0045-001） |
| 逐小時雨量 | CODIS 氣象資料開放平台 |
| 鄉鎮預報 | CWA F-D0047 各縣市鄉鎮預報 |
| 新聞 | 自由時報、聯合新聞網、Google 新聞（RSS） |

## 專案結構

```
personalized-flood-alert/
├── app/
│   ├── main.py              # FastAPI app 入口（僅 router 組裝）
│   ├── database.py          # async engine + session
│   ├── dependencies.py      # get_db() 等共用依賴
│   ├── scheduler.py         # APScheduler 排程設定
│   ├── auth.py              # 裝置 ID 驗證
│   ├── push.py              # Expo 推播通知發送
│   ├── supabase_client.py   # Supabase client
│   ├── utils.py             # 通用工具（haversine 等）
│   ├── api/                 # Routers
│   │   ├── properties.py
│   │   ├── properties_risk.py
│   │   ├── location.py
│   │   ├── rainfall.py
│   │   ├── forecast.py
│   │   ├── geocode.py
│   │   ├── alerts.py
│   │   ├── thresholds.py
│   │   ├── push_tokens.py
│   │   ├── notification_settings.py
│   │   ├── me.py
│   │   ├── reset_password.py
│   │   ├── privacy.py
│   │   ├── health.py
│   │   └── test.py
│   ├── models/              # SQLAlchemy ORM Models
│   │   ├── property.py
│   │   ├── district.py
│   │   ├── flood_risk.py
│   │   ├── alert.py
│   │   ├── rainfall.py
│   │   ├── codis_rainfall.py
│   │   ├── wra_threshold.py
│   │   ├── corrected_threshold.py
│   │   ├── flood_event.py
│   │   ├── news.py
│   │   ├── push_token.py
│   │   └── village.py
│   ├── schemas/             # Pydantic Schemas
│   │   ├── property.py
│   │   ├── alert.py
│   │   └── rainfall.py
│   └── services/
│       ├── cwa_service.py       # CWA API 串接 & 雨量更新
│       ├── codis_service.py     # CODIS 逐小時雨量下載
│       ├── city_forecast_map.py # 縣市 → F-D0047 endpoint 對照表
│       ├── threshold_service.py # 座標 → 鄉鎮警戒門檻查詢
│       ├── risk_engine.py       # 風險評估 & 警報產生
│       ├── news_service.py      # RSS 新聞抓取 & 地名抽取
│       └── llm_service.py       # OpenRouter LLM 呼叫
├── scripts/
│   ├── import_districts.py
│   ├── import_flood_risk.py
│   ├── import_wra_thresholds.py
│   └── calibrate_thresholds.py  # 門檻自動校正
├── sql/                     # 手動 migration SQL
├── data/                    # Shapefile 等原始資料（不進 git）
├── alembic/
│   └── versions/
├── MobileApp/               # Expo 前端
│   └── src/
│       ├── navigation/
│       ├── screens/
│       └── lib/
├── Dockerfile
├── fly.toml
├── pyproject.toml
└── .env.example
```
