# 水先知｜個人化淹水預警系統

以「財產」而非「行政區」為中心的淹水預警 App。使用者登記所關切的財產位置（住家、車輛、店面、倉庫、農地），系統持續比對該座標最近測站的即時雨量與所在鄉鎮的淹水警戒門檻，達警戒時主動推播通知，並依財產類型提供對應的防護建議。

採無帳號架構，不蒐集 email、姓名等個人資料。

## 技術棧

| 層級 | 技術 |
|------|------|
| 前端 | React Native 0.81 + Expo SDK 54（TypeScript），EAS Build |
| 後端 | FastAPI + SQLAlchemy 2.0（async）+ asyncpg |
| 資料庫 | PostgreSQL + PostGIS（Supabase） |
| Migration | Alembic |
| 排程 | APScheduler（AsyncIOScheduler） |
| 推播 | Expo Push Notifications → FCM V1 |
| 速率限制 | slowapi |
| 部署 | Fly.io（Docker） |
| LLM | OpenRouter API（gpt-4o-mini）— 僅用於離線門檻校正 |

**外部資料源**：中央氣象署開放資料（自動雨量站 O-A0002-001、QPE 雷達格點 O-B0045-001、鄉鎮預報 F-D0047）、CODiS 氣候資料服務系統、OpenStreetMap Nominatim（地理編碼）

## 主要功能

### 財產管理
- 支援住家、車輛、店面、倉庫、農地、自訂等類型
- 三種定位方式：輸入地址（Nominatim 地理編碼）、地圖選點、GPS 一次性取得目前位置
- 新增時以 PostGIS 空間查詢自動判定所屬鄉鎮
- 可設定 1–10 的重要程度，作為多處同時警戒時的排序依據
- 列表採兩層式結構：分類總覽（有警報的分類優先排序）→ 該分類財產明細

### 風險評估
- 排程每 10 分鐘評估所有已啟用警報的財產
- 兩級警戒判定：先檢驗一級警戒（水利署官方門檻），未達再檢驗二級預警（優先採用校正門檻）
- 比對 1／3／6 小時三種時間尺度的累積雨量，任一達標即觸發
- 風險比值 = max(實際雨量 ÷ 二級門檻)，供前端以長條圖呈現「距離門檻的接近程度」

### 警報與推播
- 達警戒時寫入警報紀錄並透過 Expo Push Service 推播
- 推播內容含警戒等級、財產名稱、行政區，以及依財產類型客製化的應變建議（5 種類型 × 2 個等級）
- 同一財產的同一等級 1 小時內不重複發送，避免警報疲勞
- 發送前檢查該裝置的推播／音效偏好設定
- Android 平台支援動態桌面圖示：有財產進入警戒時圖示自動變色

### 首頁呈現
- 以表情圖示呈現整體狀態（大晴天／多雲／注意／警戒）
- 多處同時警戒時，依「風險等級優先、重要程度次之」自動排序處理順序
- 雨量狀態區塊以長條填滿比例呈現各財產距警戒門檻的接近程度，搭配天氣圖示與即時雨量值

### 隱私與資安
- 無帳號設計：以裝置端產生的匿名 UUID（`X-Device-Id` header）識別，不蒐集個資
- 識別碼以 expo-secure-store 加密儲存（Android Keystore／iOS Keychain），並含舊版 AsyncStorage 的一次性遷移邏輯
- 資料隔離實作於應用層：所有查詢強制以 device_id 過濾，SQL 全數參數化
- API 速率限制（見下表）
- 正式環境關閉 `/docs`、`/redoc`
- 提供使用者一鍵刪除其全部資料（`DELETE /api/me/data`）
- 內建 `/privacy` 隱私權政策頁面

| 端點 | 限制 | 理由 |
|------|------|------|
| `/api/geocode`、`/api/reverse-geocode` | 10 次/分鐘 | 保護外部 Nominatim 服務，避免 IP 遭封鎖 |
| `POST /api/properties` | 20 次/分鐘 | 阻擋自動化濫用 |
| `DELETE /api/me/data` | 5 次/小時 | 不可逆的破壞性操作 |
| `/health`、`/health/scheduler` | 不限制 | 供外部監控定期檢測 |

## 資料規模

| 資料 | 規模 | 更新頻率 |
|------|------|----------|
| 行政區界圖資 | 368 個鄉鎮市區，22 縣市 | 靜態 |
| 水利署警戒門檻 | 6,461 筆，涵蓋 354 鄉鎮 | 靜態 |
| 自動雨量站 | 1,347 站 | 每 10 分鐘 |
| 歷史淹水事件 | 53 筆（高信心 48 筆） | 2024 年全年 |
| 校正後門檻 | 12 個鄉鎮（5 個數值實際下修） | 離線批次產出 |

雨量觀測資料每日凌晨 3 點自動清理 48 小時前的紀錄。

## 門檻校正說明

水利署門檻以鄉鎮為單位，是概括值，未必貼合各地實際致災雨量。本專案設計了一套離線校正流程：

1. **事件萃取**：以具網路檢索能力的 LLM 搭配預設查詢語句（涵蓋 2024 年梅雨季、凱米、山陀兒、康芮等主要事件），自新聞報導萃取「地點 + 時間」的結構化資料，含信心程度欄位
2. **時空對應**：依萃取結果自 CODiS 下載對應測站的逐時雨量，反推事件當下的 1／3／6 小時累積量
3. **事件篩選**：僅保留高信心、且實際雨量達原門檻 60%–100% 之間的事件
   - 低於 60%：可能肇因於排水堵塞等非降雨因素，不宜據以調降
   - 高於 100%：原門檻已能正確預警，無需下修
4. **保守取值**：取通過篩選事件的最小值（寧可提早提醒）
5. **合理性檢核**：維持 6h ≥ 3h ≥ 1h 單調性，不符者該尺度沿用原值

**設計取捨**：校正值僅套用於二級預警，一級警戒固定採用水利署官方門檻。理由是二級預警目的為提早提醒，可貼近在地經驗；一級警戒涉及緊急應變，應以官方標準為準。執行期另設防呆：若校正後二級門檻高於一級門檻，自動回退官方值並記錄警告。

**校正結果**（數值實際下修者）：

| 鄉鎮 | 1 小時 | 3 小時 | 6 小時 |
|------|--------|--------|--------|
| 嘉義縣水上鄉 | 50 → 32.5 | 105 → 78.5 | 140 → 117 |
| 高雄市仁武區 | 45 → 32.5 | 100 → 65.5 | 130 → 90 |
| 基隆市中正區 | 40 → 24.5 | — | — |
| 屏東縣里港鄉 | 60 → 50 | 120 → 107 | — |
| 高雄市梓官區 | — | 100 → 68.5 | — |

其餘 7 個處理過的鄉鎮校正結果與官方門檻相同，代表該地歷史事件的實際致災雨量本即接近官方標準。

## 本地開發

```bash
# 1. Clone
git clone https://github.com/Claraa1110/personalized-flood-alert.git
cd personalized-flood-alert

# 2. 環境變數
cp .env.example .env
# 編輯 .env 填入 DATABASE_URL、CWA_API_KEY、OPENROUTER_API_KEY 等

# 3. 後端（port 8001）
uv run uvicorn app.main:app --reload --port 8001

# 4. 前端
cd MobileApp
npx expo start
```

開發環境的 API 文件：`http://localhost:8001/docs`（`ENVIRONMENT=production` 時自動關閉）

### 行動端建置

```bash
cd MobileApp

# 測試用 APK（可直接安裝）
eas build --platform android --profile preview

# 上架用 AAB（上傳 Google Play Console）
eas build --platform android --profile production
```

`expo-notifications` 的推播功能與 `react-native-change-icon` 的動態圖示屬原生模組，**無法在 Expo Go 中測試**，需使用上述建置版本或 development build。

## 資料庫 Migration

```bash
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
uv run alembic downgrade -1
```

## 部署

後端部署於 Fly.io：

```bash
fly deploy
```

**重要設定**：`fly.toml` 中 `auto_stop_machines = 'off'`、`min_machines_running = 1`。排程與 API 服務運行於同一程序，若機器因閒置而休眠，排程會一併停止——對預警系統而言，最需要運作的時刻（深夜豪雨）正是無人使用的時刻，故機器必須常駐。

可透過 `/health/scheduler` 驗證排程是否正常運作，該端點回傳距上次雨量更新的分鐘數，正常應維持在 10 分鐘以內。

## API 端點

### 需帶 `X-Device-Id` header

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/properties` | 新增財產 |
| GET | `/api/properties` | 財產列表 |
| GET | `/api/properties/{id}` | 單筆財產 |
| PUT | `/api/properties/{id}` | 修改財產 |
| DELETE | `/api/properties/{id}` | 刪除財產 |
| GET | `/api/properties-with-risk` | 財產列表含風險等級與風險比值 |
| GET | `/api/geocode` | 地址轉座標 |
| GET | `/api/reverse-geocode` | 座標轉地址 |
| GET | `/api/alerts` | 警報列表 |
| GET | `/api/alerts/{id}` | 單一警報（自動標記已讀） |
| POST | `/api/alerts/mark-all-read` | 全部標記已讀 |
| POST | `/api/register-push-token` | 註冊推播 token |
| GET/PUT | `/api/notification-settings` | 查詢／更新通知偏好 |
| GET | `/api/me` | 查詢當前裝置識別碼 |
| DELETE | `/api/me/data` | 刪除該裝置所有資料 |
| GET | `/api/rainfall` | 座標附近即時雨量 |
| GET | `/api/rainfall/history` | 測站雨量歷史序列 |
| GET | `/api/threshold` | 座標所在鄉鎮的警戒門檻 |
| GET | `/api/corrected-thresholds` | 校正門檻列表 |
| GET | `/api/forecast` | 鄉鎮天氣預報（降雨機率、氣溫） |
| GET | `/api/location/district` | 座標查行政區 |
| GET | `/api/location/flood-risk` | 座標查淹水潛勢等級（見「已知限制」） |

### 公開端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/health` | 健康檢查 |
| GET | `/health/scheduler` | 排程狀態（距上次雨量更新的分鐘數） |
| GET | `/privacy` | 隱私權政策頁面（HTML） |

App 實際使用的端點為 properties、properties-with-risk、geocode／reverse-geocode、alerts、register-push-token、notification-settings、me/data、health/scheduler、privacy；其餘端點目前未被前端呼叫，保留供除錯與後續擴充。

## 資料庫結構

| 資料表 | 用途 |
|--------|------|
| `properties` | 使用者財產（device_id、type、location、priority_stars） |
| `rainfall_observations` | 雨量站觀測（rainfall_1hr／3hr／6hr、location、observed_at） |
| `districts` | 鄉鎮市區界線圖資 |
| `villages` | 村里界線圖資 |
| `wra_alert_thresholds` | 水利署原始兩級警戒門檻 |
| `corrected_thresholds` | 校正後的二級預警門檻 |
| `flood_events` | LLM 萃取的歷史淹水事件 |
| `codis_raw_rainfall` | CODiS 歷史逐時雨量 |
| `alerts` | 警報紀錄（level、message、triggered_by jsonb） |
| `push_tokens` | 推播 token |
| `user_notification_settings` | 通知偏好 |

空間欄位皆建立 GiST 索引。

### 空間查詢設計

- **點面包含**（座標 → 行政區）：`ST_Within`，轉 `geometry` 型別於平面座標運算
- **鄰近搜尋**（最近雨量站）：`ST_DWithin` 篩 50km 內 + `ST_Distance` 排序，轉 `geography` 型別以球面計算
- 測站排序策略為「先比資料時效、再比距離」，避免選中已停止回報的最近站點
- 新增財產時的空間查詢各自包在 savepoint 中，單項失敗僅降級為空值，不影響整筆交易

## 資料來源

| 資料 | 來源 |
|------|------|
| 行政區界線 | 內政部鄉鎮市區界線 |
| 警戒門檻 | 經濟部水利署兩級警戒標準（自行擷取後比對至鄉鎮） |
| 即時雨量 | CWA 自動雨量站（O-A0002-001）、QPE（O-B0045-001） |
| 逐小時雨量 | CODiS 氣候資料服務系統 |
| 鄉鎮預報 | CWA F-D0047 |
| 地理編碼 | OpenStreetMap Nominatim |

## 專案結構

```
personalized-flood-alert/
├── app/
│   ├── main.py                  # FastAPI 入口（router 組裝、限流器註冊）
│   ├── database.py              # async engine + session
│   ├── dependencies.py          # get_db() 等共用依賴
│   ├── auth.py                  # X-Device-Id 驗證
│   ├── limiter.py               # slowapi 限流器（device_id / IP 為 key）
│   ├── scheduler.py             # APScheduler：雨量擷取、風險評估、資料清理
│   ├── push.py                  # Expo Push 發送
│   ├── utils.py
│   ├── api/
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
│   │   ├── privacy.py
│   │   └── health.py
│   ├── models/
│   │   ├── property.py
│   │   ├── district.py
│   │   ├── village.py
│   │   ├── alert.py
│   │   ├── rainfall.py
│   │   ├── codis_rainfall.py
│   │   ├── wra_threshold.py
│   │   ├── corrected_threshold.py
│   │   ├── flood_event.py
│   │   ├── flood_risk.py
│   │   └── push_token.py
│   ├── schemas/
│   │   ├── property.py
│   │   ├── alert.py
│   │   └── rainfall.py
│   └── services/
│       ├── cwa_service.py       # CWA API 串接 & 雨量更新
│       ├── codis_service.py     # CODiS 逐小時雨量下載
│       ├── city_forecast_map.py # 縣市 → F-D0047 endpoint 對照
│       ├── threshold_service.py # 座標 → 兩級門檻查詢
│       ├── risk_engine.py       # 風險評估、警報產生、推播派送
│       └── llm_service.py       # OpenRouter 呼叫
├── scripts/                     # 離線資料處理（非服務執行期）
│   ├── import_districts.py
│   ├── import_villages.py
│   ├── import_flood_risk.py
│   ├── import_all_flood_risk.py
│   ├── scrape_wra_thresholds.py     # 擷取水利署門檻
│   ├── match_wra_thresholds.py      # 門檻比對至鄉鎮
│   ├── fetch_flood_events_2024.py   # LLM 萃取歷史淹水事件
│   ├── fill_rainfall_for_flood_events.py  # 回溯事件雨量
│   ├── calibrate_thresholds.py      # 門檻校正
│   ├── calculate_idw_rainfall.py    # IDW 空間內插（方法探索）
│   └── build_city_forecast_map.py
├── MobileApp/
│   └── src/
│       ├── navigation/
│       │   └── AppNavigator.tsx
│       ├── screens/
│       │   ├── HomeScreen.tsx          # 整體狀態、優先順序、雨量長條
│       │   ├── PropertyListScreen.tsx  # 兩層式財產列表
│       │   ├── AddPropertyScreen.tsx
│       │   ├── AlertScreen.tsx
│       │   ├── SettingsScreen.tsx
│       │   └── AboutScreen.tsx
│       ├── components/
│       │   ├── LocationTabPicker.tsx   # 三種定位方式
│       │   ├── TypeSelector.tsx
│       │   └── PrioritySlider.tsx      # 1–10 重要程度滑桿
│       └── lib/
│           ├── api.ts              # apiFetch（自動帶 X-Device-Id）
│           ├── deviceId.ts         # SecureStore + 舊版遷移
│           ├── propertyCache.ts    # stale-while-revalidate 快取
│           ├── notifications.ts    # 推播註冊、badge 計算
│           ├── appIcon.ts          # 動態桌面圖示
│           └── advice.ts           # 類型 × 等級的建議文字
├── sql/
├── alembic/
├── Dockerfile
├── fly.toml
└── pyproject.toml
```

## 已知限制

- **淹水潛勢未納入風險判定**：`models/flood_risk.py`、`api/location.py` 與新增財產流程保留了淹水潛勢的查詢邏輯，但水利署潛勢圖資（24h 200mm 情境）尚未匯入資料庫，`flood_risk_zones` 表不存在，相關查詢一律降級回傳 0。目前的風險判定僅依據「即時雨量 vs 警戒門檻」，未納入地形因子。匯入該圖資為後續首要工作。
- **測站空間代表性**：以最近且資料時效在 2 小時內的測站代表該點位雨量，在測站稀疏地區存在代表性誤差。`scripts/calculate_idw_rainfall.py` 為空間內插的方法探索，尚未納入主要流程。
- **門檻校正覆蓋率**：354 個具門檻資料的鄉鎮中僅 12 個完成校正（約 3.4%），受限於新聞報導對輕微積水事件的覆蓋偏差與單一年度樣本。
- **無自動化測試**：`scripts/test_*.py` 為 print 式的手動驗證腳本，無斷言機制；`.github/workflows/` 僅有自動部署，流程中不執行測試。
- **RLS 未生效**：後端以資料庫管理者角色直連，PostgreSQL 的 Row Level Security 對該角色不生效。實際的資料隔離邊界在應用層的 device_id 過濾。若未來開放多個 client 直連資料庫，應改用受限權限角色並啟用 RLS。
- **殘留項目**：資料庫中的 `news_articles` 表為已移除的即時新聞功能殘留；`api/test.py`、`api/reset_password.py` 已清空但檔案未刪除（未被 `main.py` 引用）；`screens/PropertyScreen.tsx`、`screens/MapScreen.tsx` 未接入導航，為改版前的舊檔案；前端 `@supabase/supabase-js`、`@tanstack/react-query`、`axios`、`react-native-paper`、`expo-font` 已安裝但未被引用。

## 授權

本 App 提供的淹水預警資訊僅供參考，不代表官方正式警報。實際災害狀況請以中央氣象署、經濟部水利署及各級政府發布的官方警報與指示為準。
