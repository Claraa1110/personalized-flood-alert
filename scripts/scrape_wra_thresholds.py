import asyncio
import httpx
from sqlalchemy import text
from app.database import AsyncSessionLocal

COUNTIES = [
    "臺北市", "新北市", "桃園市", "臺中市", "臺南市", "高雄市",
    "基隆市", "新竹市", "嘉義市", "新竹縣", "苗栗縣", "彰化縣",
    "南投縣", "雲林縣", "嘉義縣", "屏東縣", "宜蘭縣", "花蓮縣",
    "臺東縣", "澎湖縣", "金門縣", "連江縣",
]


def fetch_county_thresholds(county: str) -> list:
    url = f"https://fhyv.wra.gov.tw/FhyWeb/v1/Api/Rainfall/RealTimeInfo/AffectedArea/City/{county}/全部?$format=JSON"
    try:
        res = httpx.get(url, timeout=15, verify=False)
        res.raise_for_status()
        data = res.json()
        if not isinstance(data, list):
            data = [data]
        print(f"{county}：取得 {len(data)} 筆")
        return data
    except Exception as e:
        print(f"{county} 爬取失敗：{e}")
        return []


def parse_affected_areas(affected_area_str: str, district: str) -> list[dict]:
    results = []
    if not affected_area_str:
        return results

    parts = affected_area_str.split(",")
    current_district = district
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            segments = part.split("-")
            current_district = segments[0].strip()
            area = segments[1].strip() if len(segments) > 1 else ""
        else:
            area = part.strip()
        if area and (area.endswith("里") or area.endswith("村")):
            results.append({"district": current_district, "area_name": area})

    return results


async def save_thresholds(all_data: list):
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM wra_alert_thresholds"))
        await session.commit()

        count = 0
        for item in all_data:
            try:
                county = item.get("City", {}).get("zh_TW", "")
                district = item.get("Town", {}).get("zh_TW", "")
                affected_area = item.get("AffectedArea", "")
                areas = parse_affected_areas(affected_area, district)

                for v in areas:
                    await session.execute(
                        text("""
                            INSERT INTO wra_alert_thresholds
                                (county_name, district_name, area_name,
                                 threshold_1h_lv2, threshold_1h_lv1,
                                 threshold_3h_lv2, threshold_3h_lv1,
                                 threshold_6h_lv2, threshold_6h_lv1)
                            VALUES (
                                :county, :district, :area_name,
                                :t1_lv2, :t1_lv1,
                                :t3_lv2, :t3_lv1,
                                :t6_lv2, :t6_lv1
                            )
                            ON CONFLICT (county_name, district_name, area_name)
                            DO UPDATE SET
                                threshold_1h_lv2 = LEAST(wra_alert_thresholds.threshold_1h_lv2, EXCLUDED.threshold_1h_lv2),
                                threshold_1h_lv1 = LEAST(wra_alert_thresholds.threshold_1h_lv1, EXCLUDED.threshold_1h_lv1),
                                threshold_3h_lv2 = LEAST(wra_alert_thresholds.threshold_3h_lv2, EXCLUDED.threshold_3h_lv2),
                                threshold_3h_lv1 = LEAST(wra_alert_thresholds.threshold_3h_lv1, EXCLUDED.threshold_3h_lv1),
                                threshold_6h_lv2 = LEAST(wra_alert_thresholds.threshold_6h_lv2, EXCLUDED.threshold_6h_lv2),
                                threshold_6h_lv1 = LEAST(wra_alert_thresholds.threshold_6h_lv1, EXCLUDED.threshold_6h_lv1)
                        """),
                        {
                            "county": county,
                            "district": v["district"],
                            "area_name": v["area_name"],
                            "t1_lv2": item.get("AlertLevel2_H1"),
                            "t1_lv1": item.get("AlertLevel1_H1"),
                            "t3_lv2": item.get("AlertLevel2_H3"),
                            "t3_lv1": item.get("AlertLevel1_H3"),
                            "t6_lv2": item.get("AlertLevel2_H6"),
                            "t6_lv1": item.get("AlertLevel1_H6"),
                        },
                    )
                    count += 1

                if count % 100 == 0:
                    await session.commit()
                    print(f"已存入 {count} 筆...")

            except Exception as e:
                print(f"存入失敗：{e}")
                await session.rollback()
                continue

        await session.commit()
        print(f"全部完成，共存入 {count} 筆")


async def main():
    print("開始爬取水利署警戒門檻資料...")
    all_data = []
    for county in COUNTIES:
        data = fetch_county_thresholds(county)
        all_data.extend(data)

    print(f"\n總共取得 {len(all_data)} 筆原始資料")
    print("開始存入資料庫...")
    await save_thresholds(all_data)


if __name__ == "__main__":
    asyncio.run(main())
