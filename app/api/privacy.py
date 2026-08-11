import os
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse

router = APIRouter()

_ICON_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.png")


@router.get("/privacy-icon.png", include_in_schema=False)
async def privacy_icon():
    return FileResponse(_ICON_PATH, media_type="image/png")

_HTML = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>水先知 — 隱私權政策</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang TC",
                   "Noto Sans TC", sans-serif;
      background: #f0f4f8;
      color: #1a1a2e;
      line-height: 1.75;
      font-size: 15px;
    }

    header {
      background: linear-gradient(135deg, #1a5fa8 0%, #2e75b6 100%);
      color: #fff;
      padding: 32px 20px 28px;
      text-align: center;
    }
    header .logo { margin-bottom: 12px; }
    header .logo img { width: 80px; height: 80px; border-radius: 18px; box-shadow: 0 4px 16px rgba(0,0,0,.25); }
    header h1   { font-size: 22px; font-weight: 800; letter-spacing: 1px; margin-bottom: 4px; }
    header .date { font-size: 13px; opacity: .8; }

    main {
      max-width: 720px;
      margin: 0 auto;
      padding: 28px 16px 60px;
    }

    .intro {
      background: #fff;
      border-radius: 16px;
      padding: 20px;
      margin-bottom: 24px;
      box-shadow: 0 2px 12px rgba(0,0,0,.07);
      font-size: 14px;
      color: #555;
      line-height: 1.8;
    }

    hr {
      border: none;
      border-top: 1.5px solid #e0e8f0;
      margin: 20px 0;
    }

    section {
      background: #fff;
      border-radius: 16px;
      padding: 24px 20px;
      margin-bottom: 16px;
      box-shadow: 0 2px 12px rgba(0,0,0,.07);
    }

    section h2 {
      font-size: 17px;
      font-weight: 800;
      color: #2e75b6;
      margin-bottom: 16px;
      padding-bottom: 10px;
      border-bottom: 2px solid #e8f0fb;
    }

    section h3 {
      font-size: 14px;
      font-weight: 700;
      color: #1a1a2e;
      margin: 16px 0 8px;
    }
    section h3:first-of-type { margin-top: 0; }

    p { margin-bottom: 12px; color: #444; font-size: 14px; }
    p:last-child { margin-bottom: 0; }

    ul {
      padding-left: 20px;
      margin-bottom: 12px;
    }
    ul li {
      color: #444;
      font-size: 14px;
      margin-bottom: 6px;
    }

    strong { color: #1a1a2e; font-weight: 700; }

    .highlight {
      background: #f0f7ff;
      border-left: 4px solid #2e75b6;
      border-radius: 0 8px 8px 0;
      padding: 12px 14px;
      margin: 12px 0;
      font-size: 14px;
      color: #444;
    }

    .warn {
      background: #fff8e1;
      border-left: 4px solid #f0a500;
      border-radius: 0 8px 8px 0;
      padding: 12px 14px;
      margin: 12px 0;
      font-size: 14px;
      color: #5a4000;
    }

    /* Table */
    .table-wrap {
      overflow-x: auto;
      margin: 12px 0;
      border-radius: 10px;
      border: 1.5px solid #d8e8f5;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      min-width: 480px;
    }
    thead tr { background: #2e75b6; }
    thead th {
      color: #fff;
      font-weight: 700;
      padding: 11px 14px;
      text-align: left;
      white-space: nowrap;
    }
    tbody tr:nth-child(even) { background: #f5f9ff; }
    tbody tr:nth-child(odd)  { background: #fff; }
    tbody td {
      padding: 10px 14px;
      color: #444;
      vertical-align: top;
      border-bottom: 1px solid #e8f0fb;
    }
    tbody tr:last-child td { border-bottom: none; }

    .rights-list {
      list-style: none;
      padding: 0;
    }
    .rights-list li {
      padding: 10px 0;
      border-bottom: 1px solid #f0f4f8;
      font-size: 14px;
      color: #444;
    }
    .rights-list li:last-child { border-bottom: none; }
    .rights-list .right-title {
      font-weight: 700;
      color: #2e75b6;
      margin-right: 4px;
    }

    .contact-card {
      background: linear-gradient(135deg, #1a5fa8, #2e75b6);
      border-radius: 14px;
      padding: 20px;
      text-align: center;
      color: #fff;
    }
    .contact-card p { color: rgba(255,255,255,.85); font-size: 14px; margin-bottom: 10px; }
    .contact-card .email {
      display: inline-block;
      background: #fff;
      color: #2e75b6;
      font-weight: 700;
      font-size: 15px;
      padding: 10px 24px;
      border-radius: 10px;
      margin-top: 4px;
      user-select: all;
    }

    footer {
      text-align: center;
      font-size: 12px;
      color: #aaa;
      padding: 20px 16px 40px;
    }

    @media (max-width: 480px) {
      header h1  { font-size: 19px; }
      section    { padding: 20px 16px; }
      section h2 { font-size: 16px; }
    }
  </style>
</head>
<body>

<header>
  <div class="logo"><img src="/privacy-icon.png" alt="水先知" /></div>
  <h1>水先知 隱私權政策</h1>
  <div class="date">最後更新日期：2026 年 8 月 9 日</div>
</header>

<main>

  <div class="intro">
    歡迎使用「水先知」（以下稱「本 App」）。本 App 是一款豪雨誘發淹水預警服務，協助您掌握所登記財產所在地的即時淹水風險。我們非常重視您的隱私，並在設計上盡量減少資料的蒐集。本政策說明我們蒐集哪些資料、如何使用，以及您擁有的權利。使用本 App 即表示您已閱讀並同意本隱私權政策。
  </div>

  <!-- 一 -->
  <section>
    <h2>一、我們的隱私設計原則</h2>
    <p>本 App 不需要註冊帳號、不蒐集您的電子郵件、姓名或任何可直接識別您身分的個人資料。您的財產資料主要儲存在您的手機裝置本機中。為了提供淹水預警與推播通知服務，僅有少量必要資訊會傳送至本服務的伺服器。</p>
  </section>

  <!-- 二 -->
  <section>
    <h2>二、我們蒐集與處理的資料</h2>
    <ul>
      <li><strong>裝置識別碼（Device ID）</strong>：本 App 於首次開啟時，會在您的裝置本機自動產生一組隨機的裝置識別碼，用以區分不同裝置的資料。此識別碼不包含任何個人資訊（非電子郵件、非姓名、無法直接識別您本人），僅作為技術上區分裝置之用。</li>
      <li><strong>財產資料</strong>：財產位置（經緯度座標與地址文字）、財產名稱、財產類型。這些資料主要儲存在您的手機裝置本機。其中「位置座標」會與裝置識別碼一併傳送至本服務伺服器，以便比對雨量、判斷風險並發送推播通知。財產名稱由您自行命名，可能包含您自行輸入的文字。</li>
      <li><strong>推播通知識別碼（Push Token）</strong>：用於在您的財產達到警戒時，向您的裝置發送推播通知。</li>
      <li><strong>通知偏好設定</strong>：推播通知開關、警報音效開關。</li>
    </ul>
    <div class="highlight">
      我們<strong>不會</strong>蒐集您的電子郵件、姓名、電話、身分證字號、金融資訊，也不需要您註冊或登入帳號。
    </div>
  </section>

  <!-- 三 -->
  <section>
    <h2>三、我們如何使用這些資料</h2>
    <ul>
      <li>依您登記的財產位置，比對即時雨量與淹水警戒門檻，判斷風險等級。</li>
      <li>在您的財產達到警戒或預警時，向您發送推播通知與防護建議。</li>
      <li>依您的通知偏好設定，決定是否發送通知及通知形式。</li>
    </ul>
    <div class="highlight">
      我們<strong>不會</strong>將您的資料用於廣告行銷，也<strong>不會</strong>販售您的資料。
    </div>
  </section>

  <!-- 四 -->
  <section>
    <h2>四、資料的儲存與保護</h2>
    <ul>
      <li>財產資料主要儲存於您的手機裝置本機。</li>
      <li>為提供風險判斷與推播，財產座標、裝置識別碼、推播識別碼與通知偏好會儲存於 Supabase（資料庫服務）及本服務的伺服器。</li>
      <li>我們採取合理的技術措施保護伺服器上的資料，包含資料庫層級的存取控制（Row Level Security）。</li>
    </ul>
  </section>

  <!-- 五 -->
  <section>
    <h2>五、與第三方共享的資料</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>第三方服務</th>
            <th>接觸的資料</th>
            <th>用途</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Supabase</td>
            <td>財產座標、裝置識別碼、推播識別碼、通知設定</td>
            <td>資料庫儲存</td>
          </tr>
          <tr>
            <td>Expo Push Service</td>
            <td>推播識別碼、通知內容</td>
            <td>發送推播通知</td>
          </tr>
          <tr>
            <td>Google Firebase Cloud Messaging（Android）</td>
            <td>推播識別碼、通知內容</td>
            <td>Android 裝置推播</td>
          </tr>
          <tr>
            <td>Apple Push Notification service（iOS）</td>
            <td>推播識別碼、通知內容</td>
            <td>iOS 裝置推播</td>
          </tr>
          <tr>
            <td>Nominatim（OpenStreetMap）</td>
            <td>您輸入的地址文字、財產座標</td>
            <td>將地址轉換為座標以定位財產</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p>除上述必要情形外，我們不會將您的資料提供給其他第三方，除非依法律要求或為保護使用者安全之必要。</p>
  </section>

  <!-- 六 -->
  <section>
    <h2>六、資料來源與技術說明</h2>
    <p>本 App 的淹水預警判斷，基於下列公開資料運算，過程中不涉及您的個人資料：</p>
    <ul>
      <li><strong>中央氣象署</strong>：即時雨量與鄉鎮天氣預報。</li>
      <li><strong>經濟部水利署</strong>：淹水警戒門檻。</li>
      <li><strong>公開新聞資料</strong>：後台建立與校正警戒門檻時分析公開新聞標題以辨識歷史淹水事件，不涉及使用者資料。</li>
    </ul>
  </section>

  <!-- 七 -->
  <section>
    <h2>七、資料保存與刪除</h2>
    <ul>
      <li>財產資料儲存於您的裝置本機，當您在 App 中刪除財產時，該筆資料會從本機及伺服器一併移除。</li>
      <li>若您解除安裝本 App，儲存於裝置本機的資料將隨之移除。</li>
      <li>由於本 App 不使用帳號，且裝置識別碼不含個人資訊，我們無法將伺服器上的資料反向對應到特定個人。</li>
    </ul>
  </section>

  <!-- 八 -->
  <section>
    <h2>八、您的權利</h2>
    <ul class="rights-list">
      <li><span class="right-title">查詢與存取：</span>您可在 App 中檢視您登記的所有財產與設定。</li>
      <li><span class="right-title">更正：</span>您可隨時在 App 中修改財產資料與通知偏好。</li>
      <li><span class="right-title">刪除：</span>您可刪除個別財產，或解除安裝 App 以移除本機資料。</li>
      <li><span class="right-title">撤回同意：</span>您可透過設定關閉推播通知。</li>
    </ul>
  </section>

  <!-- 九 -->
  <section>
    <h2>九、兒童隱私</h2>
    <p>本 App 並非針對未滿 13 歲之兒童設計。由於本 App 不蒐集可識別個人身分的資料，我們不會在知情的情況下蒐集兒童的個人資料。</p>
  </section>

  <!-- 十 -->
  <section>
    <h2>十、政策的變更</h2>
    <p>我們可能因應服務調整或法規要求，不時更新本隱私權政策。當有重大變更時，我們會於本頁面更新「最後更新日期」，並在適當情況下於 App 內通知您。</p>
  </section>

  <!-- 十一 -->
  <section>
    <h2>十一、免責聲明</h2>
    <div class="warn">
      本 App 提供的淹水預警資訊僅供參考，係根據公開氣象與水利資料及本服務的模型運算所得，<strong>不代表官方正式警報</strong>。實際災害狀況請以中央氣象署、經濟部水利署及各級政府發布的官方警報與指示為準。本服務不對預警的準確性、即時性或完整性作任何保證，亦不對因使用或信賴本 App 資訊所導致的任何損失負責。遇緊急狀況請立即撥打相關緊急電話並遵循政府指示。
    </div>
  </section>

  <!-- 十二 -->
  <section>
    <h2>十二、聯絡我們</h2>
    <div class="contact-card">
      <p>電子郵件</p>
      <span class="email">ling120959@gmail.com</span>
    </div>
  </section>

</main>

<footer>本政策以繁體中文版本為準。</footer>

</body>
</html>"""


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    return HTMLResponse(content=_HTML)
