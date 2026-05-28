import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://codis.cwa.gov.tw/",
}

# 測試：台北站（466920）2024-07-25 歷史雨量
url = "https://codis.cwa.gov.tw/api/station?"
payload = {
    "date": "2024-07-25T00:00:00+08:00",
    "type": "report_date",
    "stn_ID": "466920",
    "stn_type": "cwb",
    "more": "",
    "start": "2024-07-25T00:00:00",
    "end": "2024-07-25T23:59:59",
    "item": "",
}

res = httpx.post(url, data=payload, timeout=30, verify=False, headers=HEADERS)
print(f"Status: {res.status_code}")
print("回傳前 1000 字：")
print(res.text[:1000])
