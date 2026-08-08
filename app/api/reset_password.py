import os
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_SUPABASE_URL = os.getenv("SUPABASE_URL", "")
_SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

_HTML = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0" />
  <title>水先知 — 重設密碼</title>
  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      min-height: 100dvh;
      background: linear-gradient(160deg, #1a5fa8 0%, #2e75b6 50%, #3d8fd4 100%);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px 16px;
    }

    .card {
      background: #fff;
      border-radius: 24px;
      padding: 36px 28px 32px;
      width: 100%;
      max-width: 400px;
      box-shadow: 0 12px 40px rgba(0,0,0,0.18);
    }

    .logo {
      text-align: center;
      margin-bottom: 28px;
    }
    .logo-drop {
      font-size: 52px;
      line-height: 1;
      display: block;
      margin-bottom: 10px;
    }
    .logo-name {
      font-size: 22px;
      font-weight: 800;
      color: #1a1a2e;
      letter-spacing: 1px;
    }
    .logo-sub {
      font-size: 13px;
      color: #888;
      margin-top: 4px;
    }

    h2 {
      font-size: 20px;
      font-weight: 700;
      color: #1a1a2e;
      text-align: center;
      margin-bottom: 8px;
    }
    .hint {
      font-size: 13px;
      color: #888;
      text-align: center;
      margin-bottom: 24px;
      line-height: 1.5;
    }

    label {
      display: block;
      font-size: 13px;
      font-weight: 600;
      color: #555;
      margin-bottom: 6px;
      margin-top: 16px;
    }
    label:first-of-type { margin-top: 0; }

    .input-wrap {
      position: relative;
    }
    input[type=password], input[type=text] {
      width: 100%;
      padding: 13px 44px 13px 14px;
      border: 1.5px solid #e0e0e0;
      border-radius: 12px;
      font-size: 15px;
      color: #222;
      background: #fafafa;
      outline: none;
      transition: border-color .2s;
      -webkit-appearance: none;
    }
    input:focus { border-color: #2e75b6; background: #fff; }

    .eye-btn {
      position: absolute;
      right: 12px;
      top: 50%;
      transform: translateY(-50%);
      background: none;
      border: none;
      cursor: pointer;
      padding: 4px;
      color: #aaa;
      font-size: 18px;
      line-height: 1;
    }

    .err-box {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      background: #fff0f0;
      border-radius: 10px;
      padding: 10px 12px;
      margin-top: 14px;
      font-size: 13px;
      color: #c00000;
      line-height: 1.4;
    }
    .err-box .icon { flex-shrink: 0; }

    .btn {
      display: block;
      width: 100%;
      padding: 15px;
      margin-top: 22px;
      background: #2e75b6;
      color: #fff;
      font-size: 16px;
      font-weight: 700;
      border: none;
      border-radius: 14px;
      cursor: pointer;
      box-shadow: 0 4px 14px rgba(46,117,182,.35);
      transition: opacity .2s, transform .1s;
      -webkit-appearance: none;
    }
    .btn:active { opacity: .85; transform: scale(.98); }
    .btn:disabled { opacity: .6; cursor: not-allowed; transform: none; }

    /* ── success ── */
    .success-wrap {
      text-align: center;
      padding: 8px 0 4px;
    }
    .success-icon { font-size: 56px; margin-bottom: 16px; }
    .success-title { font-size: 20px; font-weight: 700; color: #1a1a2e; margin-bottom: 10px; }
    .success-sub { font-size: 14px; color: #666; line-height: 1.6; }

    /* ── fatal error (invalid link) ── */
    .fatal-wrap {
      text-align: center;
      padding: 8px 0 4px;
    }
    .fatal-icon { font-size: 48px; margin-bottom: 16px; }
    .fatal-title { font-size: 18px; font-weight: 700; color: #c00000; margin-bottom: 10px; }
    .fatal-sub { font-size: 13px; color: #888; line-height: 1.6; }

    /* ── spinner ── */
    .spinner-wrap { text-align: center; padding: 16px 0 8px; }
    .spinner {
      display: inline-block;
      width: 36px; height: 36px;
      border: 4px solid #e0e9f5;
      border-top-color: #2e75b6;
      border-radius: 50%;
      animation: spin .8s linear infinite;
      margin-bottom: 12px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .spinner-text { font-size: 14px; color: #888; }

    [hidden] { display: none !important; }
  </style>
</head>
<body>
<div class="card">
  <div class="logo">
    <span class="logo-drop">💧</span>
    <div class="logo-name">水先知</div>
    <div class="logo-sub">守護你的財產安全</div>
  </div>

  <!-- 驗證中 -->
  <div id="state-loading">
    <div class="spinner-wrap">
      <div class="spinner"></div>
      <div class="spinner-text">驗證連結中…</div>
    </div>
  </div>

  <!-- 連結失效 -->
  <div id="state-fatal" hidden>
    <div class="fatal-wrap">
      <div class="fatal-icon">⚠️</div>
      <div class="fatal-title">連結無效或已過期</div>
      <div class="fatal-sub" id="fatal-msg">請重新申請密碼重設，重設連結有效期限為 1 小時。</div>
    </div>
  </div>

  <!-- 設定新密碼表單 -->
  <div id="state-form" hidden>
    <h2>設定新密碼</h2>
    <p class="hint">請輸入並確認你的新密碼（至少 6 個字元）</p>

    <label for="pw">新密碼</label>
    <div class="input-wrap">
      <input type="password" id="pw" placeholder="至少 6 個字元" autocomplete="new-password" />
      <button class="eye-btn" type="button" onclick="toggleEye('pw', this)" aria-label="顯示密碼">👁</button>
    </div>

    <label for="pw2">確認新密碼</label>
    <div class="input-wrap">
      <input type="password" id="pw2" placeholder="再次輸入密碼" autocomplete="new-password" />
      <button class="eye-btn" type="button" onclick="toggleEye('pw2', this)" aria-label="顯示密碼">👁</button>
    </div>

    <div class="err-box" id="form-err" hidden>
      <span class="icon">⚠️</span>
      <span id="form-err-msg"></span>
    </div>

    <button class="btn" id="submit-btn" onclick="handleSubmit()">確認重設密碼</button>
  </div>

  <!-- 重設成功 -->
  <div id="state-success" hidden>
    <div class="success-wrap">
      <div class="success-icon">✅</div>
      <div class="success-title">密碼重設成功！</div>
      <div class="success-sub">
        你的新密碼已儲存。<br />
        請回到「水先知」App，<br />
        用新密碼重新登入。
      </div>
    </div>
  </div>
</div>

<script>
(function () {
  const SUPABASE_URL  = "__SUPABASE_URL__";
  const SUPABASE_ANON = "__SUPABASE_ANON_KEY__";
  const client = supabase.createClient(SUPABASE_URL, SUPABASE_ANON, {
    auth: { detectSessionInUrl: false }
  });

  function show(id) {
    ["state-loading","state-fatal","state-form","state-success"].forEach(function(s) {
      document.getElementById(s).hidden = (s !== id);
    });
  }

  function showFatal(msg) {
    if (msg) document.getElementById("fatal-msg").textContent = msg;
    show("state-fatal");
  }

  function showFormError(msg) {
    var box = document.getElementById("form-err");
    document.getElementById("form-err-msg").textContent = msg;
    box.hidden = false;
  }

  function hideFormError() {
    document.getElementById("form-err").hidden = true;
  }

  function toggleEye(inputId, btn) {
    var inp = document.getElementById(inputId);
    if (inp.type === "password") {
      inp.type = "text";
      btn.textContent = "🙈";
    } else {
      inp.type = "password";
      btn.textContent = "👁";
    }
  }
  window.toggleEye = toggleEye;

  // Parse URL hash — Supabase appends session after redirect
  var hash = window.location.hash.replace(/^#/, "");
  var params = new URLSearchParams(hash);
  var access_token  = params.get("access_token");
  var refresh_token = params.get("refresh_token") || "";
  var type          = params.get("type");

  if (!access_token || type !== "recovery") {
    showFatal("此連結不是有效的密碼重設連結。請重新申請，或確認你點擊的是最新一封重設信中的連結。");
    return;
  }

  // Set session so updateUser works
  client.auth.setSession({ access_token: access_token, refresh_token: refresh_token })
    .then(function(result) {
      if (result.error) {
        showFatal("連結已失效或過期（" + result.error.message + "）。請重新申請密碼重設。");
      } else {
        show("state-form");
      }
    })
    .catch(function(e) {
      showFatal("驗證連結時發生錯誤，請稍後再試。");
    });

  window.handleSubmit = async function() {
    var pw  = document.getElementById("pw").value;
    var pw2 = document.getElementById("pw2").value;
    hideFormError();

    if (!pw) { showFormError("請輸入新密碼"); return; }
    if (pw.length < 6) { showFormError("密碼至少需要 6 個字元"); return; }
    if (pw !== pw2) { showFormError("兩次密碼不符，請重新確認"); return; }

    var btn = document.getElementById("submit-btn");
    btn.disabled = true;
    btn.textContent = "處理中…";

    try {
      var result = await client.auth.updateUser({ password: pw });
      if (result.error) {
        showFormError(result.error.message || "更新密碼失敗，請稍後再試");
        btn.disabled = false;
        btn.textContent = "確認重設密碼";
      } else {
        show("state-success");
      }
    } catch(e) {
      showFormError("發生錯誤，請稍後再試");
      btn.disabled = false;
      btn.textContent = "確認重設密碼";
    }
  };
})();
</script>
</body>
</html>"""


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page():
    html = _HTML.replace("__SUPABASE_URL__", _SUPABASE_URL)
    html = html.replace("__SUPABASE_ANON_KEY__", _SUPABASE_ANON_KEY)
    return HTMLResponse(content=html)
