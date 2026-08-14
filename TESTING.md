# Testing Guide

後端測試指南。測試策略、如何執行、如何新增，以及**目前刻意不測的部分**。

---

## 快速開始

```bash
uv sync --group dev
uv run pytest
```

測試**不需要資料庫、不需要網路、不需要任何 API key**。
任何測試若開始需要這三者之一，代表它應該屬於 integration 層（見「已知缺口」）。

常用指令：

```bash
uv run pytest                          # 全部
uv run pytest tests/unit               # 只跑純邏輯
uv run pytest tests/api                # 只跑 HTTP 契約
uv run pytest -k threshold             # 依名稱篩選
uv run pytest -x -q                    # 第一個失敗就停
uv run pytest --cov=app --cov-report=term-missing
uv run pytest --cov=app --cov-report=html && open htmlcov/index.html
```

Lint / format：

```bash
uv run ruff check .
uv run ruff format .
```

## 現況

**279 個測試，全部通過，執行時間 < 0.5 秒**（其中 4 個是刻意的 `xfail`，見下文）。

整體行覆蓋率 48%，但**平均數在這裡沒有意義**——重點是安全關鍵路徑的覆蓋：

| 模組 | 覆蓋率 | |
|------|--------|---|
| `api/properties_risk.py` | 100% | ★ App 燈號判斷 |
| `services/threshold_service.py` | 100% | ★ 兩級門檻解析 |
| `push.py` / `auth.py` / `utils.py` | 100% | |
| `api/location.py` `thresholds.py` `push_tokens.py` `notification_settings.py` `health.py` | 100% | |
| `api/properties.py` | 76% | |
| `api/alerts.py` | 63% | |
| `services/risk_engine.py` | **15%** | ⚠️ 排程主迴圈，見「已知缺口」 |
| `services/cwa_service.py` | **17%** | ⚠️ 需要真實 HTTP fixture |
| `services/news_service.py` | **0%** | 生產環境未使用（ROADMAP P2-3） |

`risk_engine.py` 的 15% 是目前最需要補的一塊：它是唯一會寫入警報的程式碼。

---

## 測試哲學

這是一個**安全關鍵系統**。使用者拿它來決定要不要移車、要不要把貨物墊高。
因此測試的目標不是覆蓋率數字，而是回答三個問題：

1. **該響的時候會不會響？** — 門檻比對、雨量累積、兩級判斷
2. **不該響的時候會不會亂響？** — 去重、邊界值、缺資料
3. **壞掉的時候看不看得出來？** — 這是目前最弱的一環（見 ROADMAP P0-5）

所以測試優先順序是：**風險判斷邏輯 > 資料轉換 > HTTP 契約 > 其他**。

---

## 測試分層

| 層 | 位置 | 依賴 | 測什麼 |
|----|------|------|--------|
| **Unit** | `tests/unit/` | 無 | 純函式：門檻比對、雨量解析、距離計算、文案對照 |
| **API 契約** | `tests/api/` | 無（DB 以 fake 取代） | 路由存在、狀態碼、request/response 形狀、device scoping |
| **Integration** | *尚未建立* | 真實 PostGIS | 空間查詢、SQL 正確性、migration（見「已知缺口」） |

### 為什麼 API 層不用真的資料庫

專案幾乎全部使用原生 `text()` SQL。要真正驗證那些 SQL，需要一個裝了
PostGIS 且匯入了行政區界線與淹水潛勢圖的資料庫——那是 integration 測試的
範疇，成本高、啟動慢，不適合放在每次 commit 都跑的迴圈裡。

現階段的取捨是：**用 fake session 快速鎖住「路由行為 + 資料轉換 + 權限範圍」，
並誠實地把「SQL 本身正確嗎」標記為缺口**（ROADMAP P3）。

---

## 目錄結構

```
tests/
├── conftest.py                  # 共用 fixture；在 import app 之前設定環境變數
├── fakes.py                     # AsyncSession 的測試替身
├── unit/
│   ├── test_utils.py            # haversine 球面距離
│   ├── test_auth.py             # X-Device-Id 解析（含信任模型的現況記錄）
│   ├── test_cwa_service.py      # 雨量字串解析、缺測值 sentinel
│   ├── test_codis_service.py    # 測站 ID → stn_type、1h/3h/6h 累積
│   ├── test_risk_evaluation.py  # ★ 核心：兩級門檻判斷與風險百分比
│   ├── test_threshold_service.py# 座標 → 兩級門檻（含校正門檻防呆）
│   ├── test_advice_parity.py    # 後端兩份建議文案不得漂移
│   ├── test_push.py             # Expo 推播組裝與「失敗不得拋例外」
│   ├── test_scheduler.py        # 排程 job 集合與週期
│   ├── test_geocode_helpers.py  # Nominatim address → 中文短地址
│   └── test_forecast_helpers.py # 縣市正規化與 F-D0047 對照表完整性
└── api/
    ├── test_app_wiring.py       # 路由清單、OpenAPI、除錯端點現況
    ├── test_device_scoping.py   # ★ 每條路由都要求且過濾 X-Device-Id
    ├── test_health.py           # /health 與 /health/scheduler
    ├── test_alerts.py           # 警報列表、詳情、標記已讀
    ├── test_properties.py       # 財產 CRUD、序列化、擁有權範圍
    ├── test_properties_risk.py  # ★ App 主畫面燈號的端到端形狀
    ├── test_thresholds.py       # 門檻查詢與校正門檻列表
    ├── test_location.py         # 行政區與淹水潛勢查詢
    ├── test_notification_settings.py
    └── test_push_tokens.py
```

★ = 出問題時使用者會直接受影響的部分，改動這些檔案時請特別小心。

---

## 核心工具

### `FakeSession` — `AsyncSession` 的測試替身

以 **SQL 片段比對**的方式注入查詢結果，而不是依賴呼叫順序：

```python
async def test_returns_stored_settings(client, db):
    db.when(
        "user_notification_settings",
        rows=[Row(notify_enabled=False, sound_enabled=True)],
    )

    body = (await client.get("/api/notification-settings")).json()

    assert body == {"notify_enabled": False, "sound_enabled": True}
```

沒有被 `when()` 攔截的查詢一律回傳空結果集，所以「查無資料」是預設行為——
測試 happy path 時必須明確地把資料放進去，不會因為忘了 stub 而誤判通過。

可用的斷言輔助：

| 方法 | 用途 |
|------|------|
| `db.when(sql_fragment, rows=[...])` | 注入結果；`times=n` 限制生效次數 |
| `db.when_raises(sql_fragment, exc)` | 模擬資料庫錯誤 |
| `db.sql_matching(fragment)` | 取出實際執行過的 SQL（驗證 `ON CONFLICT`、`LIMIT` 等） |
| `db.params_for(fragment)` | 取出繫結參數（驗證 device scoping） |
| `db.commits` / `db.rollbacks` | 交易行為 |

`Row` 同時支援屬性存取與 `._mapping`，與 SQLAlchemy 的 `Row` 一致。

### `client` / `anon_client` fixture

以 `httpx.ASGITransport` 直接掛上 ASGI app，**刻意不使用 `TestClient`**：
`ASGITransport` 不會觸發 lifespan，因此 APScheduler 與啟動時的 CWA 抓取
都不會在測試中執行。這也是為什麼測試不需要網路。

- `client` — 自動帶上 `X-Device-Id`
- `anon_client` — 不帶任何 header，用來驗證「沒有 device id 就該被拒絕」

### 環境變數

`tests/conftest.py` 在 **import 任何 `app.*` 之前**設定環境變數。這是必要的，
因為 `app/database.py` 在 module 層就建立了 async engine、
`app/services/*` 在 module 層就讀取 API key。

這件事本身是個設計問題，已記錄為 ROADMAP P1-3。修好之後，
conftest 開頭那段 `os.environ.setdefault` 就可以移除。

---

## 兩種特殊的測試

### Characterisation test — 記錄「現在是什麼樣子」

程式碼中有多處已知缺陷。我們**不假裝它們不存在**，也不直接改行為
（那屬於 ROADMAP 的工作），而是把當前行為寫成測試並附上編號：

```python
def test_property_outside_any_known_district_reports_safe():
    """Characterisation of a real safety gap.

    ... 500 mm 的雨會顯示為綠色的「安全」 ... Tracked as ROADMAP P0-3.
    """
    level, pct = _evaluate(500.0, 500.0, 500.0, {}, {})
    assert level == "safe"
```

好處有三：
1. 缺陷變成**可執行的文件**，不會在交接時遺失
2. 重構時如果不小心改變了行為，測試會失敗、逼人正視
3. 修復時知道要動哪個測試，以及「修好」的定義是什麼

目前的 characterisation test 對應：
P0-1、P0-3、P0-4、P0-5、P0-6、P1-4、P1-5、P1-12、P2-2、P2-3、P2-4、P2-5、P2-6。

### `xfail(strict=True)` — 記錄「應該變成什麼樣子」

對於已經知道正確行為的缺陷，額外寫一個**目前會失敗**的測試：

```python
@pytest.mark.xfail(strict=True, reason="ROADMAP P0-4: 缺測值應為 None 而非 0.0 mm")
def test_missing_readings_should_be_distinguishable_from_zero(sentinel):
    assert parse_rainfall(sentinel) is None
```

`strict=True` 是重點：修好之後這個測試會**通過**，而 strict xfail 遇到
非預期的通過會判定為**失敗**，強迫開發者回來移除標記、順手更新 ROADMAP。
等於把「修完要記得更新文件」變成 CI 會擋的事。

目前有 2 個：`test_cwa_service.py`（P0-4）、`test_codis_service.py`（P1-5）。

---

## 新增測試的慣例

**命名**：測試名稱寫成一句完整的行為描述，不要寫 `test_evaluate_2`。

```python
def test_threshold_is_inclusive(): ...
def test_level1_wins_over_level2_when_both_are_crossed(): ...
def test_a_404_does_not_mark_anything_read(): ...
```

**結構**：Arrange / Act / Assert 之間空一行，不需要寫註解標示。

**非同步**：`asyncio_mode = "auto"`，直接寫 `async def test_...`，
不需要 `@pytest.mark.asyncio`。

**一個測試一件事**：斷言可以多條，但都應該在描述同一個行為。
`test_response_carries_the_full_property_contract` 這種「釘住整個回應形狀」的
例外要在名稱上講清楚。

**加新路由時**，至少要有：
1. `tests/api/test_app_wiring.py` 的 `DOCUMENTED_ROUTES` 加一筆
2. 若是 device-scoped，`tests/api/test_device_scoping.py` 加一筆
3. happy path + 至少一個錯誤路徑

---

## 已知缺口

**這一節請保持誠實。** 覆蓋率數字會讓人誤以為系統被驗證過了，實際上下列
部分完全沒有自動化驗證：

| 缺口 | 影響 | 對應 |
|------|------|------|
| **原生 SQL 從未被執行** | 所有 PostGIS 查詢（`ST_Within`、`ST_DWithin`、LATERAL join）只在 fake 上跑過。SQL 打錯字、索引沒用到、join 條件錯誤，測試都抓不到 | ROADMAP P3 |
| **Migration 未被測試** | `alembic upgrade head` 從未在 CI 執行。ROADMAP P1-1 描述的「autogenerate 會 drop 掉正式欄位」正是這個缺口的產物 | P1-1 / P3 |
| **時區行為未被測試** | ROADMAP P0-7 的錯誤需要真實 Postgres 才能重現——`timestamp` 與 `timestamptz` 的比較語意無法用 fake 表達 | P0-7 |
| **`evaluate_all_properties` 未被測試** | 排程的主迴圈（約 150 行，含交易管理與推播扇出）沒有任何測試。P1-9 的 transaction poisoning 就藏在這裡 | P1-9 |
| **外部 API 解析未被測試** | CWA / CODIS / Nominatim 的回應解析只有 helper 層被測；真實 payload 的形狀變更不會被發現 | 建議加 recorded fixtures |
| **前後端契約未被測試** | `MobileApp` 對回應欄位的假設沒有任何保護 | P3 |
| **併發與競態未被測試** | 警報去重的 check-then-insert race（P0-2）無法用單執行緒測試重現 | P0-2 |

補上第一項（PostGIS integration test）是投資報酬率最高的下一步，
建議用 `testcontainers` 起 `postgis/postgis` 映像。

---

## CI

`.github/workflows/ci.yml` 在 **每個 PR 與每次 push 到 main** 時執行三個 job：

| Job | 內容 | 會擋 merge / deploy 嗎 |
|-----|------|------------------------|
| `lint` | `ruff check .`（全 repo）+ `ruff format --check tests/` | ✅ 會 |
| `test` | `pytest --cov-fail-under=45`，並上傳 junit / coverage 報告 | ✅ 會 |
| `migrations` | 對真實 PostGIS 容器跑 `alembic upgrade head` + `alembic check` | ❌ 不會（見下） |

`.github/workflows/fly-deploy.yml` 以 `needs: ci` 呼叫這個 workflow，
所以**測試沒過就不會部署**（ROADMAP P0-8 已完成）。

### 覆蓋率門檻是一個 ratchet

`--cov-fail-under=45` 是目前實際值（48%）稍微往下取的**地板**，用來防止退步，
不是目標。隨著 ROADMAP 推進（特別是 `risk_engine.py` 補上測試後）應該逐步調高。

**請不要把這個數字當成品質指標。**
上面那張「已知缺口」表比覆蓋率百分比更能說明這個系統被驗證的程度。

### `migrations` job 目前是 `continue-on-error`

因為 ROADMAP P1-1（ORM metadata 與實際 schema 已偏離）尚未修復，
`alembic check` 現在必然失敗。這個 job 的作用是**讓那個偏離持續可見**，
並提供一個明確的「修好了沒」判準。

修好 P1-1 之後請移除 `continue-on-error: true`，讓 schema drift 變成硬性失敗。

### Lint 的 ratchet

`pyproject.toml` 的 `[tool.ruff.lint.per-file-ignores]` 列出既有程式碼尚未
滿足的規則，逐檔標註對應的 ROADMAP 編號。這樣做的目的是：

- **新程式碼**從第一天起就受完整規則集保護（例如新增的 `verify=False`
  會立刻被 `S501` 擋下）
- 導入 CI 的 PR 不需要夾帶上千行的機械式改寫

**這份清單只能變短。** 每修好一項就刪掉對應的行。
