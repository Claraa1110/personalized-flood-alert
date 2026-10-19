import math
from datetime import datetime
from zoneinfo import ZoneInfo

TAIPEI = ZoneInfo("Asia/Taipei")


def now_taipei_naive() -> datetime:
    """
    取得臺北當地時間（naive，不帶時區）。

    資料庫中 rainfall_observations.observed_at、codis_raw_rainfall.obs_time
    等欄位為 timestamp without time zone，存的是臺北牆上時鐘的值。
    寫入或比較這類欄位時一律使用本函式，不要用 datetime.now()——
    後者取的是容器本機時間，Fly.io 容器未設 TZ 時為 UTC，會差 8 小時。
    """
    return datetime.now(TAIPEI).replace(tzinfo=None)


def normalize_place_name(name: str | None) -> str | None:
    """
    地名異體字正規化：「台」→「臺」。

    內政部行政區界圖資與水利署門檻皆採正式寫法「臺」（臺北市、臺南市、臺東縣），
    但 LLM 萃取、使用者輸入等來源常用俗寫「台」。兩者字元不同，
    直接比對會失敗，故所有寫入帶地名欄位之前都應先通過本函式。
    """
    if name is None:
        return None
    return name.replace("台", "臺")


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """計算兩點之間的球面距離（公里）"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))
