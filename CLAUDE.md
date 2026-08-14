# CLAUDE.md

給 Claude Code（以及任何第一次接觸這個 repo 的人）的工作指南。

---

## 這是什麼

個人化淹水預警系統。使用者登記自己的財產位置（家、車、店面、倉庫、農田），
系統持續監測雨量，當雨量達到該鄉鎮的警戒門檻時寫入警報並推播通知。

**這是安全關鍵系統。** 使用者會依據它的輸出決定要不要移車、要不要撤離。
因此本 repo 的最高原則是：

> **寧可大聲失敗，也不要安靜地回報「安全」。**

目前系統有數個已知的靜默失效路徑，全部記錄在
[docs/ROADMAP.md](docs/ROADMAP.md)。動到相關程式碼前請先讀那份文件。

- 後端：FastAPI + SQLAlchemy 2.0 async + PostgreSQL/PostGIS（Supabase）
- 前端：React Native + Expo（`MobileApp/`，本文件不涵蓋）
- 部署：Fly.io（`nrt`），GitHub Actions 自動部署

---

## 常用指令

```bash
# 環境
uv sync --group dev                    # 安裝相依（含測試工具）
cp .env.example .env                   # 然後填入真實的 key

# 開發
uv run uvicorn app.main:app --reload --port 8001
open http://localhost:8001/docs

# 測試（不需要 DB、不需要網路）
uv run pytest
uv run pytest tests/unit -q
uv run pytest --cov=app --cov-report=term-missing

# 品質
uv run ruff check .
uv run ruff format .

# Migration —— ⚠️ 見下方「已知地雷」
uv run alembic upgrade head
uv run alembic downgrade -1
```

---

## 架構速覽

```
CWA 雨量站 API ──每 10 分鐘──▶ rainfall_observations
                                        │
座標 ──PostGIS──▶ districts ──▶ wra_alert_thresholds  （官方兩級門檻）
                                └──▶ corrected_thresholds（LLM 校正後的 level2）
                                        │
                                        ▼
                              risk_engine.evaluate_all_properties
                                   （每 10 分鐘，APScheduler）
                                        │
                                  alerts ──▶ Expo Push
```

**兩級警戒**是這個系統的核心領域概念：

- `level1`（一級警戒 / 紅）— **一律**使用水利署 WRA 官方門檻，不接受校正
- `level2`（二級預警 / 黃）— 優先使用 LLM 校正後的門檻，沒有則退回 WRA lv2
- 不變式：**`level2 門檻 < level1 門檻`**。`threshold_service.py` 有防呆，
  校正值若 ≥ level1 會退回官方值

三個時間尺度（1h / 3h / 6h）**任一**超過門檻即觸發，先判 level1 再判 level2。

### 檔案地圖

| 路徑 | 職責 |
|------|------|
| `app/main.py` | 只做 router 組裝與 lifespan，不放商業邏輯 |
| `app/scheduler.py` | APScheduler 設定（雨量抓取、風險評估、清理） |
| `app/auth.py` | `X-Device-Id` header 解析（⚠️ 不是身分驗證，見 ROADMAP P0-1） |
| `app/services/risk_engine.py` | ★ 排程主迴圈：評估 → 寫警報 → 推播 |
| `app/services/threshold_service.py` | ★ 座標 → 兩級門檻（含校正防呆） |
| `app/services/cwa_service.py` | CWA 雨量站與 QPE 格點 |
| `app/services/codis_service.py` | CODIS 歷史逐小時雨量（門檻校正用） |
| `app/api/properties_risk.py` | ★ App 主畫面的燈號 API |
| `app/models/` | SQLAlchemy ORM（⚠️ 只有 `Property` 真的在用，其餘已漂移） |
| `scripts/` | 一次性的匯入與校正腳本，**不是**測試 |

★ = 改動會直接影響使用者安全的檔案。

---

## 已知地雷（動手前必讀）

### 1. 不要直接執行 `alembic revision --autogenerate`

ORM model 與實際 schema 已經不同步。autogenerate 目前會產生：

```python
op.drop_column('rainfall_observations', 'rainfall_6hr')   # 風險引擎正在讀這個欄位
op.drop_table('user_notification_settings')               # 所有使用者的通知設定
```

若必須新增 migration，請**逐行檢視**產生的檔案並刪掉所有 `drop_*`。
根治方式見 ROADMAP P1-1。

### 2. 風險判斷邏輯有三份

`risk_engine.py`（排程）、`properties_risk.py`（列表 API）、
`thresholds.py`（單點查詢）各有一份門檻比對邏輯，而且**已經在
「查不到門檻」的處理上分歧**。改任何一份都要同步檢查另外兩份，
否則 App 顯示的燈號會和實際發出的警報不一致。

建議文案（`_ADVICE` / `_PUSH_ADVICE`）也有兩份，
`tests/unit/test_advice_parity.py` 會擋住漂移。

去重方式見 ROADMAP P1-4。

### 3. 時間欄位全部沒有時區

所有 `TIMESTAMP WITHOUT TIME ZONE`，而且寫入端混用兩個時鐘
（CWA 的台北時間 vs Postgres 的 `NOW()` UTC）。任何涉及時間比較的
查詢目前都是錯的（詳見 ROADMAP P0-7）。

**新程式碼一律使用 aware datetime**：`datetime.now(timezone.utc)`，
不要寫裸的 `datetime.now()`。

### 4. 排程跑在 API process 內

`fly.toml` 目前設定 `auto_stop_machines = 'stop'` + `min_machines_running = 0`，
代表沒有 HTTP 流量時機器會停止，**排程也就跟著停止**。
另一方面，若擴到多台機器就會有多個排程器同時評估。
兩個問題都在 ROADMAP P0-2。

### 5. 除錯端點目前對外開放

`/api/test-*`、`/api/alerts/seed-test`、`/api/alerts/evaluate` 都能被匿名呼叫，
其中 `evaluate` 會對所有使用者扇出推播。**不要在這些端點上疊加新功能**，
它們應該被刪除（ROADMAP P0-6）。

---

## 程式碼慣例

**語言**：註解、docstring、log 訊息、使用者可見字串一律用**繁體中文**；
識別字（變數、函式、檔名）用英文。這是既有慣例，請沿用。

**SQL**：目前絕大多數查詢是原生 `text()`。空間查詢用原生 SQL 是合理的選擇，
但**參數一律用繫結參數**（`:lat`、`:device_id`），不要用 f-string 拼接。

**新增 API 路由時**：
1. 在 `app/api/` 新增檔案，`app/main.py` 掛上 router
2. device-scoped 的路由要加 `device_id: str = Depends(get_device_id)`，
   且 SQL 的 `WHERE` 一定要包含 `device_id`
3. 補測試：`tests/api/test_app_wiring.py` 的路由表 +
   `tests/api/test_device_scoping.py`（若是 device-scoped）+ happy path + 錯誤路徑
4. 加 `response_model`（新程式碼請不要再回傳裸 dict）

**錯誤處理**：不要寫 `except Exception: print(...)` 然後繼續。
若某個失敗會讓系統少發一則警報，它必須被記錄成可告警的事件。
在 async session 中 `except` 之後**一定要 `await session.rollback()`**
（否則整個 session 會進入 pending rollback，後續全部失敗——ROADMAP P1-9）。

**日誌**：用 `logging`，不要用 `print()`。既有的 19 處 `print()` 是待清理項目。

**對外 HTTP**：用 `httpx.AsyncClient`，**不要**加 `verify=False`
（既有的都是待修項目，ROADMAP P1-2）。不要在 async 函式裡呼叫同步 client。

---

## 測試

完整說明見 [TESTING.md](TESTING.md)。重點：

- `uv run pytest` 不需要 DB、不需要網路、不需要 API key
- 測試用 `FakeSession` 以 SQL 片段比對來注入結果：
  `db.when("FROM alerts", rows=[...])`
- **原生 SQL 本身沒有被測試**，PostGIS 查詢的正確性目前無保障
- 有兩種特殊測試：
  - **characterisation test** — 記錄現有缺陷的當前行為，附 ROADMAP 編號
  - **`xfail(strict=True)`** — 描述缺陷修好後應有的行為；修好時會轉成
    XPASS 而失敗，提醒你回來移除標記並更新 ROADMAP

修 bug 時的流程：先找到對應的 characterisation test → 改成期望行為 →
讓它失敗 → 修 code → 更新 `docs/ROADMAP.md` 的狀態。

---

## 環境變數

| 變數 | 必要 | 用途 |
|------|------|------|
| `DATABASE_URL` | ✅ | Supabase Postgres；程式會自動改寫成 `postgresql+asyncpg://` |
| `CWA_API_KEY` | ✅ | 中央氣象署開放資料 |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` | ✅ | 重設密碼頁面 |
| `OPENROUTER_API_KEY` | 選用 | LLM 地名抽取與門檻校正（僅 `scripts/` 使用） |
| `ENVIRONMENT` | 選用 | 目前程式碼並未真正依此分歧行為 |

`.env.example` 中的 `WRA_API_ID`、`WRA_API_SECRET`、`GOOGLE_MAPS_API_KEY`
**在程式中沒有任何引用**，是殘留項目（ROADMAP P2-8）。

⚠️ 設定目前是散落的 `os.getenv()`，且**在 module import 時就讀取**。
缺少的 key 不會讓程式啟動失敗，只會讓對應功能安靜地失效。
改動 `app/main.py` 的 import 順序有可能讓 `CWA_API_KEY` 變成 `None`
（ROADMAP P1-3）。

---

## 提交前檢查

```bash
uv run ruff check . && uv run ruff format --check tests/ && uv run pytest
```

這三項就是 CI 會跑的內容（`.github/workflows/ci.yml`）。

- `ruff format` 目前只對 `tests/` 強制；`app/` 與 `scripts/` 的排版清理是
  獨立的待辦（ROADMAP P2-13）
- `pyproject.toml` 的 `per-file-ignores` 是一份 **ratchet 清單**——列出既有
  程式碼尚未滿足的規則。**只能變短，不要往裡面加東西**。新程式碼受完整規則集
  保護，例如新增 `verify=False` 會被 `S501` 立刻擋下

⚠️ 推送到 `main` 會**自動部署到正式環境**（現在會先等 CI 通過）。
