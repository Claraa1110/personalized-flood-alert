import httpx
import asyncio
import os
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

CWA_API_KEY = os.getenv("CWA_API_KEY")
NS = {"cwa": "urn:cwa:gov:tw:cwacommon:0.1"}


async def test_qpe():
    url = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/O-B0045-001"
    params = {
        "Authorization": CWA_API_KEY,
    }

    async with httpx.AsyncClient(
        timeout=60, verify=False, follow_redirects=True
    ) as client:
        response = await client.get(url, params=params)
        print(f"Status: {response.status_code}")
        print(f"Content-Length: {len(response.content)} bytes")

        root = ET.fromstring(response.text)

        dataset = root.find("cwa:dataset", NS)
        info = dataset.find("cwa:datasetInfo", NS)
        params_set = info.find("cwa:parameterSet", NS)

        print("\n=== 網格參數 ===")
        for child in params_set:
            print(f"  {child.tag.split('}')[-1]}: {child.text}")

        contents = dataset.find("cwa:contents", NS)
        content = contents.find("cwa:content", NS)
        data_str = content.text.strip() if content is not None else ""
        values = [float(v) for v in data_str.split(",") if v.strip()]
        nonzero = [v for v in values if v > 0]

        print("\n=== 網格資料 ===")
        print(f"  總格點數：{len(values)}")
        print(f"  有降雨格點：{len(nonzero)}")
        if values:
            print(f"  最大雨量：{max(values):.2f} mm")
        if nonzero:
            print(f"  前 10 個非零值：{nonzero[:10]}")


if __name__ == "__main__":
    asyncio.run(test_qpe())
