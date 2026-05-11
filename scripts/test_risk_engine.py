from app.services.risk_engine import calculate_risk_score, score_to_level


def test_scenarios():
    print("=== 風險評估測試 ===\n")

    scenarios = [
        {
            "name": "高風險（大雨 + 高潛勢 + 有新聞）",
            "rainfall_1hr": 85,
            "flood_potential": 4,
            "news_severity": "high",
            "expected": "emergency",
        },
        {
            "name": "中風險（中雨 + 中潛勢 + 無新聞）",
            "rainfall_1hr": 55,
            "flood_potential": 3,
            "news_severity": "none",
            "expected": "warning",
        },
        {
            "name": "低風險（小雨 + 低潛勢 + 無新聞）",
            "rainfall_1hr": 10,
            "flood_potential": 1,
            "news_severity": "none",
            "expected": "notice",
        },
        {
            "name": "安全（沒雨 + 低潛勢 + 無新聞）",
            "rainfall_1hr": 0,
            "flood_potential": 1,
            "news_severity": "none",
            "expected": "safe",
        },
        {
            "name": "新聞補足（小雨但有高嚴重度新聞）",
            "rainfall_1hr": 20,
            "flood_potential": 3,
            "news_severity": "high",
            "expected": "warning",
        },
    ]

    all_pass = True
    for s in scenarios:
        score = calculate_risk_score(
            rainfall_1hr=s["rainfall_1hr"],
            flood_potential=s["flood_potential"],
            news_severity=s["news_severity"],
        )
        level = score_to_level(score)
        passed = level == s["expected"]
        status = "✅" if passed else "❌"
        if not passed:
            all_pass = False

        print(f"{status} {s['name']}")
        print(f"   分數：{score}，等級：{level}（預期：{s['expected']}）\n")

    print("=" * 40)
    print(f"結果：{'全部通過 ✅' if all_pass else '有測試失敗 ❌'}")


if __name__ == "__main__":
    test_scenarios()
