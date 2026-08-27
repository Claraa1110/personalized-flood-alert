"""Render the pytest + coverage results as a GitHub Actions job summary.

Reads ``junit.xml`` and ``coverage.json`` from the working directory and writes
markdown to stdout; the workflow appends that to ``$GITHUB_STEP_SUMMARY``.

Runs with ``if: always()``, so it must degrade gracefully when a report is
missing (e.g. pytest crashed before writing one) and must never fail the job.
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# The modules where a coverage regression actually costs a user something.
# The repo-wide average is close to meaningless (see TESTING.md); these are the
# paths that decide whether an alert fires, so they get their own table.
SAFETY_CRITICAL = {
    "app/services/risk_engine.py": "排程主迴圈：寫警報、發推播",
    "app/services/threshold_service.py": "座標 → 兩級門檻",
    "app/api/properties_risk.py": "App 主畫面燈號",
    "app/services/cwa_service.py": "雨量擷取與解析",
    "app/push.py": "Expo 推播送出",
    "app/auth.py": "device scoping",
}

COVERAGE_FLOOR = 45


def _pct(value: float) -> str:
    return f"{value:.0f}%"


def _badge(pct: float) -> str:
    if pct >= 90:
        return "🟢"
    if pct >= 60:
        return "🟡"
    return "🔴"


def render_tests(junit: Path) -> list[str]:
    if not junit.exists():
        return ["## 🧪 測試", "", "⚠️ 找不到 `junit.xml`——pytest 可能在產生報告前就中止了。", ""]

    # S314: this XML is pytest's own output from the step immediately above,
    # not third-party input. Contrast app/services/cwa_service.py, where the
    # XML really does come from an external API (ROADMAP P1-2).
    suite = ET.parse(junit).getroot().find("testsuite")  # noqa: S314
    if suite is None:
        return ["## 🧪 測試", "", "⚠️ `junit.xml` 沒有 testsuite。", ""]

    total = int(suite.get("tests", 0))
    failures = int(suite.get("failures", 0))
    errors = int(suite.get("errors", 0))
    skipped = int(suite.get("skipped", 0))
    duration = float(suite.get("time", 0))
    passed = total - failures - errors - skipped

    xfails: list[tuple[str, str]] = []
    for case in suite.iter("testcase"):
        node = case.find("skipped")
        if node is not None and node.get("type") == "pytest.xfail":
            xfails.append((case.get("name", "?"), node.get("message", "")))

    icon = "✅" if failures == 0 and errors == 0 else "❌"
    parts = [f"**{passed} passed**"]
    if failures:
        parts.append(f"**{failures} failed**")
    if errors:
        parts.append(f"**{errors} errors**")
    if xfails:
        parts.append(f"{len(xfails)} xfailed")

    out = ["## 🧪 測試", "", f"{icon} {' · '.join(parts)} — {duration:.2f}s", ""]

    if xfails:
        out += [
            "<details>",
            f"<summary>{len(xfails)} 個 xfail — 每一個都是 ROADMAP 的待修項目</summary>",
            "",
            "修好之後這些測試會轉為 XPASS 而**失敗**（`strict=True`），"
            "提醒你移除標記並更新 `docs/ROADMAP.md`。",
            "",
        ]
        out += [f"- `{name}`<br>{reason}" for name, reason in xfails]
        out += ["", "</details>", ""]

    return out


def render_coverage(cov: Path) -> list[str]:
    if not cov.exists():
        return ["## 📊 覆蓋率", "", "⚠️ 找不到 `coverage.json`。", ""]

    data = json.loads(cov.read_text())
    total = data["totals"]["percent_covered"]
    files = {name: info["summary"]["percent_covered"] for name, info in data["files"].items()}

    status = "✅" if total >= COVERAGE_FLOOR else "❌"
    out = [
        "## 📊 覆蓋率",
        "",
        f"{status} **{_pct(total)}** （地板 {COVERAGE_FLOOR}%）",
        "",
        "> 這個平均數本身沒有太大意義。真正重要的是下面這張表——"
        "決定「警報會不會響」的那幾個模組。完整缺口見 `TESTING.md`。",
        "",
        "### 安全關鍵路徑",
        "",
        "| 模組 | 職責 | 覆蓋率 |",
        "|------|------|-------:|",
    ]
    for path, role in SAFETY_CRITICAL.items():
        pct = files.get(path)
        cell = f"{_badge(pct)} {_pct(pct)}" if pct is not None else "—"
        out.append(f"| `{path}` | {role} | {cell} |")

    out += [
        "",
        "<details>",
        f"<summary>全部 {len(files)} 個檔案</summary>",
        "",
        "| 檔案 | 覆蓋率 |",
        "|------|-------:|",
    ]
    for path, pct in sorted(files.items(), key=lambda kv: (kv[1], kv[0])):
        out.append(f"| `{path}` | {_pct(pct)} |")
    out += ["", "</details>", ""]

    return out


def main() -> None:
    root = Path.cwd()
    lines = render_tests(root / "junit.xml") + render_coverage(root / "coverage.json")
    sys.stdout.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # A broken summary must never turn a green build red.
        sys.stdout.write(f"## ⚠️ 無法產生測試摘要\n\n```\n{exc!r}\n```\n")
    raise SystemExit(0)
