# Backend Engineering Roadmap

> 本文件是後端的深度技術審查結果，依「使用者受到傷害的機率 × 嚴重度」排序。
> 審查基準：commit `301f5dd`（2026-08-14）。
>
> 這是一個**安全關鍵（safety-critical）系統**。使用者把財產安全託付給它，
> 因此排序原則只有一條：**靜默失效（silent failure）比當機更危險**。
> 系統當機使用者會發現；系統回報「安全」但其實沒在監測，使用者不會發現。
>
> 本檔案中的每一項編號（P0-1、P1-5…）都對應 `tests/` 中至少一個
> characterisation test。修好之後請一併更新或移除該測試的 `xfail` 標記。

---

## 目前狀態總評

| 面向 | 評分 | 說明 |
|------|------|------|
| 產品構想與領域建模 | 🟢 強 | 兩級門檻 + LLM 校正 + PostGIS 空間查詢，是紮實的領域設計 |
| 功能完整度 | 🟢 強 | 端到端串起 CWA / WRA / CODIS / RSS，前後端都能跑 |
| 正確性保證 | 🔴 弱 | 審查前**零測試**；時間軸、缺測值、未知行政區三處會靜默失效 |
| 生產可靠性 | 🔴 弱 | 部署設定會讓排程停擺；健康檢查恆為 ok；無錯誤追蹤 |
| 安全性 | 🔴 弱 | 無身分驗證；TLS 驗證全面關閉；除錯端點對外開放 |
| 可維護性 | 🟡 中 | 風險判斷邏輯有三份、建議文案有三份；ORM 與實際 schema 已偏離 |

**一句話總結**：功能已經做完了，但**還沒有變成一個可以信賴的系統**。
下面的 P0 全部完成之前，不建議上架 App Store / Google Play。

---

## P0 — 上架前必須完成

### ✅ P0-0　補齊自動化測試（本次已完成）

**現況**：新增 `tests/`（21 個模組、279 個測試），涵蓋純函式邏輯與 HTTP 契約。
測試**不需要資料庫、不需要網路、不需要 API key**，全部跑完約 0.3 秒。
同時加入 ruff 設定（含 `S` 安全規則與 `ASYNC` 規則）。詳見
[TESTING.md](../TESTING.md)。

安全關鍵路徑（`properties_risk.py`、`threshold_service.py`、`push.py`、`auth.py`）
已達 100% 覆蓋；整體 48%，缺口誠實列在 TESTING.md 的「已知缺口」一節。

本次同時把 **13 個既有缺陷寫成 characterisation test**——測試現行行為並在
docstring 中標註 ROADMAP 編號，讓缺陷變成可執行的文件而不是口耳相傳。
另有 2 個測試以 `xfail(strict=True)` 描述「修好之後應該是什麼樣子」：
修好時它們會轉為 XPASS 而**失敗**，強迫開發者回來移除標記並更新本文件。

**驗收**：`uv run pytest` 全綠（275 passed, 4 xfailed）。

---

### P0-1　`X-Device-Id` 不是身分驗證

**檔案**：`app/auth.py`、所有 `Depends(get_device_id)` 的路由
**測試**：`tests/unit/test_auth.py::test_accepts_any_string_without_verification`、
`tests/api/test_device_scoping.py::test_any_caller_may_impersonate_any_device`

```python
async def get_device_id(x_device_id: str | None = Header(None, alias="X-Device-Id")) -> str:
    if not x_device_id or not x_device_id.strip():
        raise HTTPException(status_code=400, detail="X-Device-Id header is required")
    return x_device_id.strip()   # ← 沒有任何驗證
```

這個 header 是**由客戶端自己宣稱**的識別碼，伺服器完全沒有驗證。後果：

1. **IDOR**：任何人只要知道別人的 device id，就能讀取、修改、刪除該使用者的
   財產位置（= 家的座標）與警報紀錄。財產座標是高度敏感的個資。
2. `curl -H "X-Device-Id: <victim>"` 即可完成上述所有操作，無需任何憑證。
3. Device id 可能經由日誌洩漏——目前 `echo=True`（P1-6）會把它印進 Fly logs。

**建議**：專案已經有 Supabase（`reset-password` 頁面在用），代表 Supabase Auth
已經導入一半。收尾即可：

- 前端登入後取得 JWT，以 `Authorization: Bearer <jwt>` 呼叫 API
- 後端用 Supabase JWKS 驗簽，取出 `sub` 作為 `user_id`
- `properties` / `alerts` / `push_tokens` 全部改以 `user_id` 為 scope
- 若要保留免註冊體驗：發一個**伺服器簽章**的匿名 token（device id 放進 JWT
  payload 並簽名），而不是接受裸字串

**驗收**：`test_any_caller_may_impersonate_any_device` 改寫為「偽造的
identity 回 401」。

---

### P0-2　目前的 Fly 部署設定會讓排程停擺

**檔案**：`fly.toml`、`app/scheduler.py`、`app/main.py`
**測試**：`tests/unit/test_scheduler.py`（釘住排程契約；部署面需靠 runbook 驗證）

```toml
auto_stop_machines = 'stop'
auto_start_machines = true
min_machines_running = 0
```

排程器（APScheduler）跑在 **API process 內**。上述設定的意思是
「沒有 HTTP 流量就把機器停掉」。合起來看：

> **沒有人打開 App 的時候，系統就不再抓雨量、不再評估風險、不再發警報。**

而「沒有人打開 App」正好就是凌晨三點——最需要淹水預警的時候。這是目前
整個系統最嚴重的問題：它讓所有其他功能在最關鍵的時刻歸零。

次要問題：一旦流量上升、Fly 起了第 2 台機器，就會有 **2 個 APScheduler
同時評估所有財產**。`max_instances=1` 只在單一 process 內有效。去重邏輯是

```python
existing = await session.execute("SELECT id FROM alerts WHERE ... created_at > NOW() - INTERVAL '1 hour'")
if existing.fetchone(): continue
await session.execute("INSERT INTO alerts ...")
```

典型的 check-then-insert race，且 `alerts` 沒有對應的 unique constraint，
所以重複推播只是時間問題。

**建議**（依序）：

1. **立即**：`min_machines_running = 1`、移除 `auto_stop_machines`。成本增加有限，
   但這是「系統有沒有在運作」的前提。
2. **短期**：把排程與 API 拆成兩個 Fly process group（`[processes]` 中 `app` 與
   `worker`），worker 固定 1 台、API 可自由縮放。
3. **中期**：以 Postgres advisory lock（`pg_try_advisory_lock`）包住每個 job，
   讓多實例情況下仍只有一個執行。
4. **同時**：`alerts` 加上 partial unique index，把去重從「應用層檢查」變成
   「資料庫保證」：

   ```sql
   CREATE UNIQUE INDEX alerts_dedupe_idx
     ON alerts (property_id, level, date_trunc('hour', created_at));
   ```

**驗收**：新增 runbook 步驟——停止所有 HTTP 流量 30 分鐘後，
`/health/scheduler` 仍回報 `minutes_since_last_update < 15`。

---

### P0-3　查不到行政區時，系統回報「安全」

**檔案**：`app/api/properties_risk.py:_evaluate`、`app/services/risk_engine.py`
**測試**：`tests/unit/test_risk_evaluation.py::test_property_outside_any_known_district_reports_safe`、
`tests/api/test_properties_risk.py::test_a_property_outside_every_district_reads_as_safe`

當 PostGIS 找不到財產所在的鄉鎮（離島、行政區邊界縫隙、尚未匯入的縣市），
兩個門檻 dict 都是空的，於是：

```python
_evaluate(500.0, 500.0, 500.0, {}, {})  # → ('safe', 0.0)
```

**下了 500 mm 的雨，App 顯示綠色的「安全」。**

而排程端的行為又不一樣——`risk_engine` 是 `if not thresholds: continue`，
直接跳過該財產、不寫警報。所以使用者看到綠燈、也收不到通知，
兩邊都沉默，但原因不同。

**建議**：

- 新增第三種狀態 `unknown`，前端以灰色 + 「此地區尚無警戒基準」明確呈現
- `POST /api/properties` 建立財產時就檢查是否落在已知行政區，查不到時
  在回應中標記，讓使用者當下就知道這個位置無法監測
- 加一個 metric：`properties_without_thresholds`，值 > 0 應該要有人去看

**驗收**：上述兩個測試改為斷言 `level == "unknown"`。

---

### P0-4　缺測值被當成「沒有下雨」

**檔案**：`app/services/cwa_service.py:parse_rainfall`
**測試**：`tests/unit/test_cwa_service.py::test_cwa_missing_value_sentinels_are_flattened_to_zero`
（另有 `xfail` 版本描述目標行為）

```python
def parse_rainfall(value) -> float:
    try:
        v = float(value)
        return max(0.0, v)      # ← -99 / -990 變成 0.0
    except (TypeError, ValueError):
        return 0.0              # ← None / "N/A" 也變成 0.0
```

CWA 用 `-99`、`-990` 表示「此測站無資料」。`max(0.0, v)` 把它壓成 `0.0`，
於是**故障的雨量站與「確實沒下雨」的雨量站在資料庫裡完全一樣**。

風險引擎取最近測站的值來判斷是否發警報。如果最近的測站當機，
系統會安靜地認為那裡是乾的。

**建議**：

- `parse_rainfall` 回傳 `float | None`，sentinel 與無法解析都回 `None`
- 資料庫欄位允許 `NULL`（已經是 nullable）
- 查詢改成 `WHERE rainfall_1hr IS NOT NULL`，找不到有效測站時往外擴，
  而不是拿一個 0 值來用
- `get_rainfall_for_location` 明確區分「查到 0 mm」與「查不到資料」，
  後者應觸發 P0-3 的 `unknown` 狀態
- 加 metric：`stations_reporting_null_ratio`，異常升高代表上游出問題

**驗收**：`test_missing_readings_should_be_distinguishable_from_zero`
從 `xfail` 轉為正常通過（並移除標記）。

---

### P0-5　健康檢查永遠回報 ok

**檔案**：`app/api/health.py`
**測試**：`tests/api/test_health.py::test_scheduler_health_reports_ok_even_when_badly_stale`

```python
minutes = (datetime.now() - last_rainfall_update).total_seconds() / 60
return {"status": "ok", "minutes_since_last_update": round(minutes, 1)}
```

雨量任務每 10 分鐘跑一次。上次更新是 **12 小時前**時，這個端點仍然回
`{"status": "ok", "minutes_since_last_update": 720.0}`。任何監控這條路由的
uptime check 都會是綠燈，而系統其實已經瞎了 12 小時。

其他問題：`last_rainfall_update` 是 **process 內的全域變數**，機器重啟就歸零
（回報 `no_data`），多台機器時每台的值都不同、且與實際排程狀態無關。

**建議**：

- 狀態改由**資料庫**判定，而非 process 記憶體：
  `SELECT max(observed_at) FROM rainfall_observations`
- 定義門檻：`< 20 min` → `ok`；`20–60 min` → `degraded`；`> 60 min` → `unhealthy`
  並回 HTTP 503，讓 Fly 與外部監控真的會 fail
- 分開 liveness（`/health`）與 readiness/staleness（`/health/scheduler`）
- 導入 Sentry（或同級）做 exception tracking——目前 `except Exception: print(...)`
  的地方，錯誤只會消失在 log 裡
- **監控「警報系統本身」**：連續 N 個評估週期 0 筆警報 + 有大雨 = 異常

**驗收**：測試改為斷言 12 小時未更新時回 `503` / `status == "unhealthy"`。

---

### P0-6　除錯端點暴露在正式環境

**檔案**：`app/api/test.py`、`app/api/alerts.py`、`app/api/push_tokens.py`
**測試**：`tests/api/test_app_wiring.py::test_debug_routes_are_currently_reachable`、
`::test_risk_evaluation_can_be_triggered_by_anyone`

| 端點 | 問題 |
|------|------|
| `POST /api/alerts/evaluate` | **完全無驗證**。掃描資料庫中所有財產並對外扇出推播。任何人都能反覆呼叫 → 資源耗盡 + 對所有使用者的手機轟炸 |
| `POST /api/alerts/seed-test` | 把**捏造的警戒紀錄**寫進真實使用者的警報歷史 |
| `DELETE /api/alerts/seed-test` | 用 regex 比對訊息內容來刪除，會誤刪真實警報 |
| `GET /api/test-postgis` / `test-integrated` | 洩漏其他使用者財產的名稱與距離（**未依 device 過濾**） |
| `GET /api/test-rainfall` | 每次呼叫抓取全台測站、Python 端算 haversine |

`test-postgis` / `test-integrated` 沒有 `Depends(get_device_id)`，
查詢也沒有 `WHERE device_id = ...`，等於一個公開的財產列表 API。

**建議**：

- 直接刪除 `app/api/test.py` 與 `seed-test` 兩個端點；測試資料改由 pytest fixture 提供
- `POST /api/alerts/evaluate` 保留給維運用，但改為需要 admin token，並加上速率限制
- 加一道 guard：`if settings.environment == "production": 不掛載 debug router`

**驗收**：`test_debug_routes_are_currently_reachable` 反轉為
「這些路由在 production 設定下不存在」。

---

### P0-7　時間軸全面錯亂

**檔案**：所有 migration（`sa.DateTime()`）、`cwa_service.py`、`rainfall.py`、`news_service.py`

三個獨立的問題疊在一起：

**(a) 欄位型別**——所有 migration 都用 `sa.DateTime()`，對應
`TIMESTAMP WITHOUT TIME ZONE`。沒有任何欄位存時區。

**(b) 寫入時混用兩個時鐘**：

```python
# cwa_service.py — CWA 給的是 +08:00，把時區資訊丟掉後存入
observed_at = datetime.fromisoformat(obs_time_str).replace(tzinfo=None)   # 台北牆上時間
```

```sql
-- risk_engine.py — 由 Postgres 產生
INSERT INTO alerts (..., created_at) VALUES (..., NOW())                   -- UTC
```

同一個資料庫裡，`rainfall_observations.observed_at` 是台北時間，
`alerts.created_at` 是 UTC，**相差 8 小時**。

**(c) 於是所有時間比較都是錯的**：

```sql
WHERE observed_at >= NOW() - INTERVAL '2 hours'
```

`observed_at` 比 `NOW()` 早 8 小時的基準，所以這個「2 小時內的新鮮資料」
實際上是 **10 小時**的窗口。**10 小時前的雨量會被當成即時資料拿來發警報。**

同理，`cleanup_old_data` 的 48 小時實際是 56 小時；
`/api/rainfall/history` 的 `since = datetime.now() - timedelta(hours=hours)`
用的是**伺服器**本地時間（Fly 上是 UTC），與台北時間的 `observed_at` 又差 8 小時，
回傳的區間是錯的。

**建議**：

1. 新增 migration，把所有時間欄位改為 `TIMESTAMP WITH TIME ZONE`
   （`ALTER TABLE ... ALTER COLUMN ... TYPE timestamptz USING ... AT TIME ZONE 'Asia/Taipei'`，
   針對已寫入的台北時間資料做一次性轉換）
2. 應用層一律使用 aware datetime：`datetime.now(timezone.utc)`，
   全面禁用裸 `datetime.now()`（可用 ruff `DTZ` 規則強制）
3. 保留 CWA 回傳的 `+08:00` 偏移，不要 `.replace(tzinfo=None)`
4. 顯示層才轉台北時間

**驗收**：新增 integration test——寫入一筆 `observed_at = now - 3h` 的觀測，
確認 2 小時新鮮度查詢**查不到**它。

---

### P0-8　CI 直接部署，沒有任何檢查

**檔案**：`.github/workflows/fly-deploy.yml`

```yaml
on:
  push:
    branches: [main, master]
jobs:
  deploy:
    steps:
      - uses: actions/checkout@v4
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
```

push 到 main 就直接上線。沒有測試、沒有 lint、沒有型別檢查、沒有
migration 檢查。P0-0 補的測試如果沒有進 CI，很快就會腐爛。

另外 `superfly/flyctl-actions@master` 是浮動 ref——第三方 action 的
任意 commit 都會在有 `FLY_API_TOKEN` 的環境裡執行。應 pin 到 SHA。

**建議**：

```yaml
jobs:
  test:
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@<sha>
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run pytest --cov=app --cov-fail-under=70
  deploy:
    needs: test          # ← 關鍵
    if: github.ref == 'refs/heads/main'
```

另外加一個 PR 觸發的 workflow（目前只在 push 時跑），以及
`alembic check`（偵測 model 與 migration 不同步，見 P1-1）。

**驗收**：故意讓一個測試失敗，確認 deploy job 被擋下。

---

## P1 — 正確性與資料完整性

### P1-1　`alembic --autogenerate` 會刪掉正式環境的資料

**檔案**：`app/models/rainfall.py`、`alembic/env.py`

ORM metadata 已經與實際 schema 偏離：

| 實際 DB | ORM model | autogenerate 會產生 |
|---------|-----------|---------------------|
| `rainfall_observations.rainfall_6hr`（migration `669cacc62c48` 新增） | **model 沒有這個欄位** | `op.drop_column('rainfall_observations', 'rainfall_6hr')` |
| `user_notification_settings` 資料表 | **完全沒有對應的 model** | `op.drop_table('user_notification_settings')` |

`rainfall_6hr` 正是 `risk_engine.get_rainfall_for_location` 讀取的欄位。
下一個執行 `uv run alembic revision --autogenerate` 的人，如果沒有逐行讀
產生的 migration 就套用，會**同時砍掉風險引擎依賴的欄位與所有使用者的通知設定**。

這是一顆已經上膛的地雷，而 README 的「資料庫 Migration」章節正是教大家這樣做。

**建議**：

- 立刻補上 `rainfall_6hr` 欄位定義與 `UserNotificationSettings` model
- 加 CI 檢查：`alembic check`（偵測 model 與 DB 不同步時 fail）
- 決定唯一真實來源：既然 90% 的查詢是原生 SQL（見 P2-1），
  也可以選擇**放棄 autogenerate**、改為手寫 migration，並在 README 明講

---

### P1-2　所有對外請求都關閉 TLS 驗證

**檔案**：`cwa_service.py`（×2）、`forecast.py`、`codis_service.py`、`test.py`、多個 `scripts/`

```python
async with httpx.AsyncClient(timeout=30, verify=False) as client:
```

**決定要不要對使用者發出淹水警報的雨量數字，是從一個未經驗證的通道取得的。**
中間人可以任意竄改雨量值——調低則警報不發，調高則全體使用者半夜被吵醒。

`verify=False` 通常是為了繞過憑證鏈問題臨時加的，然後就留下來了。

**建議**：

- 移除所有 `verify=False`
- 若 CWA / CODIS 確實有憑證鏈問題，用 `certifi` 或指定 CA bundle 解決，
  不要關閉驗證
- ruff `S501`（`request-with-no-cert-validation`）已在本次設定中啟用，
  修完後 CI 會擋住回歸

---

### P1-3　設定散落各處，且依賴 import 順序才能正確運作

**檔案**：`app/database.py`、`app/services/cwa_service.py`、`app/services/llm_service.py` 等
**測試**：`tests/conftest.py` 開頭的註解

```python
# app/services/cwa_service.py — module import 時就讀取
CWA_API_KEY = os.getenv("CWA_API_KEY")
```

```python
# app/main.py — load_dotenv() 在所有 router import 之後才呼叫
from app.api.test import router as test_router
...
load_dotenv()
```

目前能運作純屬巧合：`app.api.test` → `app.dependencies` → `app.database`，
而 `app/database.py` 在自己的 module 層呼叫了 `load_dotenv()`。
只要有人調整 `main.py` 的 import 順序，`CWA_API_KEY` 就會變成 `None`——
而且不會拋錯，只會讓 CWA 請求安靜地失敗（`except: print(...)`）。

缺少的 key 也不會 fail fast：`CWA_API_KEY=None` 會一路送到 CWA API，
拿到錯誤後被吞掉，系統照常啟動、照常回報 healthy。

**建議**：

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    cwa_api_key: str
    openrouter_api_key: str | None = None
    supabase_url: str
    supabase_anon_key: str
    environment: Literal["development", "staging", "production"] = "development"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()   # 缺少必填值 → 啟動即失敗，訊息清楚
```

同時清掉 `.env.example` 中未使用的 `WRA_API_ID` / `WRA_API_SECRET` /
`GOOGLE_MAPS_API_KEY`（見 P2-8）。

---

### P1-4　風險判斷邏輯有三份、建議文案有三份

**檔案**：`risk_engine.py`、`properties_risk.py`、`thresholds.py`（＋前端 `advice.ts`）
**測試**：`tests/unit/test_advice_parity.py`

同一套「比對雨量與兩級門檻」的邏輯被實作了三次：

| 位置 | 用途 | 已知差異 |
|------|------|----------|
| `risk_engine.evaluate_all_properties` | 排程寫警報、發推播 | 查不到門檻 → `continue`（不評估） |
| `properties_risk._evaluate` | App 主畫面的燈號 | 查不到門檻 → `'safe'`（綠燈） |
| `thresholds.get_threshold_by_location` | 單點查詢 | 又一份 inline 迴圈 |

三者已經在「查不到門檻」這個 case 上出現分歧（即 P0-3）。
建議文案同樣有三份複本（後端兩份 + 前端一份），本次已用
`test_advice_parity.py` 把後端兩份釘在一起，但那是防守，不是解法。

**建議**：

- 抽出 `app/services/risk_rules.py`，內含**唯一一個**純函式：
  `classify(rainfall: Rainfall, thresholds: Thresholds) -> RiskAssessment`
- 三個呼叫端都改用它；純函式易於測試，現有的
  `tests/unit/test_risk_evaluation.py` 可直接沿用
- 建議文案移到單一資料來源，由 API 回傳給前端，前端不再自帶一份

---

### P1-5　`calculate_max_rainfall` 違反自己的單調性不變式

**檔案**：`app/services/codis_service.py`
**測試**：`tests/unit/test_codis_service.py::test_series_shorter_than_three_hours_reports_zero_for_3h`

```python
max_3h = 0.0
for i in range(max(0, n - 2)):     # n < 3 時 range 為空
    total = sum(rainfalls[i:i+3])
```

序列不足 3 小時時，`max_3h` 保持 `0.0`：

```python
calculate_max_rainfall([{"rainfall_mm": 80.0}])
# → {'1h': 80.0, '3h': 0.0, '6h': 80.0}
```

README 明文承諾「維持單調性：6h ≥ 3h ≥ 1h」，這裡直接違反。
這個函式的輸出會流進門檻校正流程（`scripts/calibrate_thresholds.py`），
低估的 3h 值會讓校正後的 3h 門檻偏低或被錯誤過濾。

**建議**：`max_3h = max(sum(rainfalls[i:i+3]) for i in range(max(1, n - 2)))`，
或明確以 `min(3, n)` 的窗口計算並在文件中說明短序列語意。

**驗收**：`test_short_series_should_also_be_monotonic` 從 `xfail` 轉為通過。

---

### P1-6　正式環境開著 SQL echo

**檔案**：`app/database.py`

```python
engine = create_async_engine(_url, echo=True, ...)
```

每一條 SQL 與**所有繫結參數**都會印到 stdout，也就是 Fly logs。參數包含：

- 使用者財產的經緯度（＝家的座標）
- 地址字串
- device id（在 P0-1 修好之前，這等同於帳號密碼）

這同時是**個資外洩**與**效能問題**——排程每 10 分鐘寫入約 500 筆雨量，
每筆都會產生一段 log。

**建議**：`echo=settings.environment == "development"`。
需要看 SQL 時用 `SQLALCHEMY_ECHO` 環境變數臨時開啟。

---

### P1-7　雨量寫入：每個測站開一個 session、一個 transaction

**檔案**：`app/services/cwa_service.py:save_rainfall_observations`

```python
for station in stations:              # 約 500 個測站
    async with AsyncSessionLocal() as session:
        await session.execute(text("INSERT INTO rainfall_observations ..."))
        await session.commit()
```

每 10 分鐘產生約 **500 次連線取得 + 500 次 commit**，且完全序列執行。
在 Supabase 的連線池上這是明顯的浪費，也讓整個抓取週期拉得很長。

**建議**：

```python
async with AsyncSessionLocal() as session:
    await session.execute(insert_stmt, [row_dict for station in stations])  # executemany
    await session.commit()
```

一個 transaction、一次 round trip。同時具備原子性——目前若第 300 個測站
失敗，資料庫會停在「一半新、一半舊」的狀態。

---

### P1-8　`rainfall_observations` 只增不改，且每輪都塞入重複資料

**檔案**：`app/services/cwa_service.py`、`app/scheduler.py`

每 10 分鐘為同一批測站 INSERT 約 500 筆新列，即使 CWA 的 `ObsTime` 沒有變。
一天約 72,000 列，`cleanup_old_data` 每天凌晨 3 點才清一次。
所有查詢都要 `ORDER BY observed_at DESC` 掃過這個持續膨脹的表。

**建議**：

- 加 `UNIQUE (station_id, observed_at)`，改用
  `INSERT ... ON CONFLICT (station_id, observed_at) DO UPDATE`
- 清理改為每小時執行，或直接用 `pg_partman` 做時間分割
- 加索引：`(station_id, observed_at DESC)` 支援熱路徑查詢

---

### P1-9　一筆失敗的 SQL 會讓整輪評估全部失敗

**檔案**：`app/services/risk_engine.py:evaluate_all_properties`

```python
for prop in properties:
    try:
        ...
        await session.execute(text("INSERT INTO alerts ..."))
    except Exception as e:
        logger.error(f"財產 {prop.name} 評估失敗：{e}")
        continue                      # ← 沒有 rollback
```

SQLAlchemy 的 session 在一條語句失敗後會進入 **pending rollback** 狀態，
之後的任何語句都會拋 `PendingRollbackError`。因此：

> 只要有**一個**財產評估失敗，這一輪剩下的**所有**財產都會連帶失敗——
> 而且每一個都只是被 `logger.error` 記一筆，然後 `continue`。

最後 `await session.commit()` 也會失敗，該輪一則警報都不會寫入。
外部看起來系統完全正常。

**建議**：

- `except` 區塊內加 `await session.rollback()`
- 更好的做法：每個財產用 `async with session.begin_nested():`（SAVEPOINT），
  讓單一財產的失敗被隔離
- 加 metric：`evaluation_failures_total`，> 0 就該告警

---

### P1-10　QPE 查詢每次都下載整份格點資料，然後把結果丟掉

**檔案**：`app/services/cwa_service.py:get_qpe_rainfall`、`app/api/rainfall.py`

```python
# cwa_service.py 回傳的 key 是 rainfall_1hr
return {"rainfall_1hr": rainfall, ..., "source": "qpe", ...}
```

```python
# rainfall.py 讀的是 rainfall_mm —— 這個 key 永遠不存在
"rainfall_now_mm": qpe_result.get("rainfall_mm", station.rainfall_mm),
```

`.get()` 永遠取到預設值，所以 **QPE 的結果從來沒有被使用過**，
但每一次 `GET /api/rainfall` 都會：

1. 對 CWA 發一個 timeout 60 秒的請求
2. 下載並解析 441 × 561 = **247,401 個數值**的 XML
3. 算出格點值，然後丟棄

只有 `source` 欄位受影響——它會標成 `"qpe"`，但數字其實來自測站。
**回應內容與 `source` 標籤不一致**，且每個請求都付出這筆成本。

**建議**：

- 修正 key 名稱不一致，並決定 QPE 究竟要不要用
- 若要用：QPE 是**全台共用**的格點資料，應由排程每 10 分鐘抓一次存進資料庫
  （或至少放進 process 內快取），而非每個請求各抓一次
- 若不用：刪掉這條路徑，`source` 誠實標成 `"station"`

---

### P1-11　協程裡有阻塞式 I/O

**檔案**：`news_service.py`、`codis_service.py`、`llm_service.py`

```python
async def fetch_single_source(source_name: str, rss_url: str) -> int:
    feed = feedparser.parse(rss_url)        # 同步 HTTP，阻塞整個 event loop
```

```python
res = httpx.post(url, ...)                  # 同步 client（codis_service）
response = get_llm_client().chat.completions.create(...)  # 同步 OpenAI client
```

在 async 應用中，一次阻塞呼叫會凍結**整個 process** 的所有請求，
而不只是當前這個任務。RSS 來源或 OpenRouter 慢一秒，全部 API 就慢一秒。

**建議**：`httpx.AsyncClient` + `AsyncOpenAI`；`feedparser` 沒有 async 版本，
改為 `await asyncio.to_thread(feedparser.parse, url)`。
ruff 的 `ASYNC` 規則已在本次設定中啟用，可協助抓出這類問題。

---

### P1-12　`GET /api/properties` 的 N+1 查詢

**檔案**：`app/api/properties.py:list_properties`

```python
for p in props:
    rainfall_row = await lookup_rainfall(db, shape.y, shape.x)   # 每個財產一次查詢
```

每個財產一次 PostGIS 空間查詢（`ST_DWithin` + `ST_Distance` over 50 km）。
`properties_risk.py` 已經示範了正確做法（`LEFT JOIN LATERAL` 一次搞定），
把同樣的模式套過來即可。

---

### P1-13　全域鎖把地理編碼序列化成 1 req/s

**檔案**：`app/api/geocode.py`

```python
_last_call: float = 0.0
_lock = asyncio.Lock()
...
async with _lock:
    if elapsed < 1.0:
        await asyncio.sleep(1.0 - elapsed)
```

process 內**所有**地理編碼請求排成一列，每秒最多一個。第 11 個併發使用者
會等超過 10 秒（httpx timeout）而失敗。同時，這個限流在多台機器上並不成立，
仍然可能違反 Nominatim 的使用政策（該政策也要求 User-Agent 附上聯絡方式）。

**建議**：短期加上結果快取（同一地址不重複查詢）；中長期改用
自架 Nominatim 或商用 geocoding 服務。限流狀態若要跨實例，需放進 Redis。

---

## P2 — 可維護性、契約與成本

### P2-1　ORM model 與原生 SQL 並存，兩邊都不完整
只有 `Property` 真正透過 ORM 使用；其餘 model 是裝飾品，並已與實際 schema 偏離（P1-1）。
**建議**：選一種。原生 SQL 沒問題（空間查詢本來就適合），但那就該刪掉未使用的
model，並改為手寫 migration。

### P2-2　Expo 推播回執完全沒有處理
**測試**：`tests/unit/test_push.py::test_per_token_expo_receipts_are_not_inspected`
Expo 對失效 token 會回 HTTP 200 + `{"status":"error","details":{"error":"DeviceNotRegistered"}}`。
目前只看 status code，所以失效 token 永遠不會被清除，`push_tokens` 只增不減，
而且**推播送不到完全不會被察覺**。
**建議**：解析 ticket、依 receipt id 回查、刪除 `DeviceNotRegistered` 的 token。

### P2-3　新聞 / LLM 流程在正式環境是死的
**測試**：`tests/unit/test_scheduler.py::test_news_ingestion_is_not_scheduled`
`fetch_news` 沒有排程，只能從 `scripts/` 手動執行 → `news_articles` 永遠是空的
→ `risk_engine.get_news_signal_near`（查詢該表）本身也從未被呼叫。
README 宣稱的「鄰近新聞」風險因子實際上不存在。
**建議**：接上排程，或誠實地從 README 移除、把死碼刪掉。

### P2-4　`_get_stn_type` 對非預期的測站 ID 直接崩潰
**測試**：`tests/unit/test_codis_service.py::test_unrecognised_station_id_raises`
`re.match(r'^([A-Z]+)', station_id).group(1)` 在不匹配時是 `AttributeError`，
不是可處理的錯誤。**建議**：回傳 `None` 並讓呼叫端跳過該測站。

### P2-5　回應沒有 schema、警報沒有分頁
**測試**：`tests/api/test_alerts.py::test_total_counts_the_returned_page_not_the_whole_history`
多數路由回傳裸 `dict`，OpenAPI 上是無型別的 `{}`，前端沒有契約可依循。
`/api/alerts` 硬編碼 `LIMIT 50` 且 `total = len(rows)`——超過 50 筆之後
使用者無法再往前翻，`total` 也是錯的。
**建議**：補上 `response_model`；改為 cursor 分頁並回傳真實總數。

### P2-6　錯誤契約不一致、驗證不一致
**測試**：`tests/api/test_thresholds.py::test_unknown_district_returns_200_with_an_error_body`、
`::test_coordinates_are_not_range_validated`
`/api/threshold` 查無資料時回 **200 + `{"error": ...}`**，其他路由則是 404。
`/api/location/*` 有 `ge/le` 座標驗證，`/api/threshold` 沒有。
路徑也沒有版本（`/api/` 而非 `/api/v1/`），未來無法安全地做破壞性變更。
**建議**：統一 error envelope、統一驗證、加上版本前綴。

### P2-7　用 `print()` 取代 logging
`app/` 下有 19 處 `print()`（`cwa_service`、`risk_engine`、`codis_service`）。
沒有等級、沒有結構化欄位、沒有 request id，Fly log 無法有效查詢。
**建議**：全面改用 `logging`，並導入 structlog + request id middleware。

### P2-8　死碼與設定漂移
- `app/supabase_client.py`：**從未被 import**，且若被 import 會因
  `os.environ["SUPABASE_SERVICE_ROLE_KEY"]` 而 `KeyError`（該變數連
  `.env.example` 都沒有）。刪掉。
- `.env.example` 中的 `WRA_API_ID` / `WRA_API_SECRET` / `GOOGLE_MAPS_API_KEY`
  在程式中沒有任何引用。刪掉，減少誤導與外洩面。
- `app/schemas/alert.py` 宣告 `Literal["notice", "warning", "emergency"]`，
  但系統實際使用 `level1` / `level2`。這個 schema 沒有被任何路由使用。

### P2-9　容器與部署設定
- `Dockerfile` 用 `python:3.11-slim`，但 `requires-python = ">=3.13"`、
  `.python-version` 是 `3.13` → uv 得在 build 時另外抓一份 3.13，浪費且易混淆
- `.dockerignore` 排除了 `alembic/` → **映像檔內無法執行 migration**，
  只能從開發機直連正式資料庫執行，這條路徑沒有稽核也沒有防呆
- 容器以 root 執行、沒有 `HEALTHCHECK`、`fly.toml` 沒有 `[checks]`

### P2-10　`GET /api/alerts/{id}` 會改變狀態
GET 應為 idempotent，目前它會把警報標為已讀。任何預抓（prefetch）、
重試或爬蟲都會誤標。**建議**：改為 `POST /api/alerts/{id}/read`。

### P2-11　重設密碼頁的前端安全性
`app/api/reset_password.py` 從 CDN 載入 `@supabase/supabase-js`，
沒有 SRI、沒有 CSP header。CDN 被入侵即可竊取重設中的密碼。
HTML 以字串替換注入設定值，雖然目前的值不含特殊字元，但這個模式很脆弱。
**建議**：加上 `Content-Security-Policy`、`X-Frame-Options`、
`Referrer-Policy`；自行託管該 JS 或加上 SRI hash。

### P2-12　全站沒有速率限制
沒有任何端點有速率限制。`/api/geocode`（外部服務且有配額）、
`/api/alerts/evaluate`（會發推播）、`/api/rainfall`（會下載 250k 值的 XML）
都可以被無限呼叫。**建議**：以 `slowapi` 或 Fly 層的限流做基本防護。

---

## P3 — 後續投資

| 項目 | 說明 |
|------|------|
| PostGIS 整合測試 | 用 testcontainers 起一個 `postgis/postgis`，測真正的空間查詢與 SQL（目前的單元測試刻意不碰資料庫，見 TESTING.md 的「已知缺口」） |
| 前後端契約測試 | 從 OpenAPI 產生 TypeScript 型別，讓 `MobileApp` 編譯期就能發現契約破壞 |
| 門檻校正的回測框架 | 用歷史事件評估校正後門檻的 precision / recall——目前無從得知校正是否真的比原始門檻好 |
| 負載測試 | 颱風天流量會是平時的數十倍，需要知道現在的架構在哪裡先斷 |
| 分散式追蹤 | OpenTelemetry，用來看清「CWA 抓取 → 風險評估 → 推播」整條鏈路 |
| 警報有效性回饋 | 讓使用者回報「這次真的淹了嗎」，這是唯一能持續改進門檻的資料來源 |

---

## 建議執行順序

```
第 1 週   P0-0 ✅ 測試　→　P0-8 CI gate　→　P0-2 部署設定（讓排程真的會跑）
第 2 週   P0-7 時區　→　P0-4 缺測值　→　P0-3 unknown 狀態
第 3 週   P0-1 身分驗證　→　P0-6 移除除錯端點
第 4 週   P0-5 健康檢查與可觀測性　→　P1-1 alembic 地雷　→　P1-2 TLS
第 5-6 週 P1-3 設定　→　P1-4 邏輯去重　→　P1-6/7/8/9 效能與正確性
之後      P2 依序處理；P3 視產品節奏安排
```

前三週的順序有意義：**先讓系統真的在跑（P0-2），再確保它跑得正確
（P0-7 / P0-4 / P0-3），最後才是保護它（P0-1 / P0-6）**。
一個沒在運作的系統，加上再好的身分驗證也沒有意義。
