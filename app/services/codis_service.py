import re
import httpx
from datetime import datetime

from app.utils import haversine


async def find_nearby_stations(lat: float, lng: float,
                                radius_km: float, session) -> list[dict]:
    """從 rainfall_observations 找附近 radius_km 公里內的測站"""
    from sqlalchemy import text

    result = await session.execute(text("""
        SELECT DISTINCT ON (station_id)
            station_id, station_name, latitude, longitude
        FROM rainfall_observations
        WHERE station_id IS NOT NULL
        AND latitude IS NOT NULL
        AND longitude IS NOT NULL
    """))
    all_stations = result.fetchall()

    nearby = []
    for s in all_stations:
        dist = haversine(lat, lng, s.latitude, s.longitude)
        if dist <= radius_km:
            nearby.append({
                'station_id': s.station_id,
                'station_name': s.station_name,
                'lat': s.latitude,
                'lng': s.longitude,
                'distance_km': round(dist, 2),
            })

    return sorted(nearby, key=lambda x: x['distance_km'])


def _get_stn_type(station_id: str) -> str:
    """根據測站 ID 判斷 stn_type（依 CODIS DevTools 確認）
    C0V660 → auto_C0, CAP020 → auto_CAP, 466920 → cwb
    """
    if station_id[:1].isdigit():
        return 'cwb'
    # 一個字母後接數字 → 字母+數字為前綴（如 C0）；否則取連續字母（如 CAP）
    m = re.match(r'^([A-Z])(\d)', station_id)
    if m:
        prefix = m.group(1) + m.group(2)
    else:
        prefix = re.match(r'^([A-Z]+)', station_id).group(1)
    return f'auto_{prefix}'


def download_hourly_rainfall(station_id: str,
                              start: datetime,
                              end: datetime) -> list[dict]:
    """從 CODIS 下載指定測站的逐小時雨量"""
    url = 'https://codis.cwa.gov.tw/api/station?'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://codis.cwa.gov.tw/',
    }
    payload = {
        'date': start.strftime('%Y-%m-%dT%H:%M:%S+08:00'),
        'type': 'report_date',
        'stn_ID': station_id,
        'stn_type': _get_stn_type(station_id),
        'more': '',
        'start': start.strftime('%Y-%m-%dT%H:%M:%S'),
        'end': end.strftime('%Y-%m-%dT%H:%M:%S'),
        'item': '',
    }
    try:
        res = httpx.post(url, data=payload, headers=headers, timeout=30, verify=False)
        data = res.json()

        # CODIS 回傳格式：data[0]["dts"][i]["Precipitation"]["Accumulation"]
        dts = data.get('data', [{}])[0].get('dts', [])

        result = []
        for record in dts:
            rain = 0.0
            precip = record.get('Precipitation', {})
            if precip:
                rain = precip.get('Accumulation') or 0.0

            # 過濾 CODIS 缺值代碼（通常是 -999 或更小的負數）
            if rain < 0:
                rain = 0.0

            result.append({
                'time': record.get('DataTime'),
                'rainfall_mm': float(rain),
            })
        return result

    except Exception as e:
        print(f'  CODIS 下載失敗 {station_id}：{e}')
        return []


def calculate_max_rainfall(hourly_data: list[dict]) -> dict:
    """
    計算 1H/3H/6H 最大累積雨量
    策略：以 news_time 往前 6 小時為區間，取各時間尺度最大值
    """
    rainfalls = [r['rainfall_mm'] for r in hourly_data]
    n = len(rainfalls)

    if n == 0:
        return {'1h': 0.0, '3h': 0.0, '6h': 0.0}

    # 1H 最大值（任意一小時最大）
    max_1h = max(rainfalls)

    # 3H 最大連續累積
    max_3h = 0.0
    for i in range(max(0, n - 2)):
        total = sum(rainfalls[i:i+3])
        if total > max_3h:
            max_3h = total

    # 6H 總累積
    max_6h = sum(rainfalls)

    return {
        '1h': round(max_1h, 1),
        '3h': round(max_3h, 1),
        '6h': round(max_6h, 1),
    }
