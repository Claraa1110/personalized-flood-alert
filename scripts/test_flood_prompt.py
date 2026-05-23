import json
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

PROMPT_TEMPLATE = """你是一個新聞資訊抽取助理。請從以下台灣淹水新聞標題中，
抽取關鍵資訊。只回答 JSON，不要其他文字。

抽取規則：
- is_flood_event：這是否描述台灣當下發生的淹水事件（true/false）
- county：縣市名稱（如：「高雄市」），找不到填 null
- district：鄉鎮市區（如：「岡山區」），找不到填 null
- village：村里名稱（如：「岡山里」），找不到填 null
- event_time：新聞提到的時間（ISO 格式），找不到填 null
- confidence：必須是字串 "high"、"medium" 或 "low" 之一
  - "high"：county + district + event_time 三者都找到
  - "medium"：有 county 或 district，但 event_time 為 null
  - "low"：連縣市都找不到，或根本不是淹水事件

回傳格式範例：
{{"is_flood_event": true, "county": "高雄市", "district": "岡山區", "village": null, "event_time": null, "confidence": "medium"}}

新聞標題：{title}"""


def test_prompt(title: str) -> dict:
    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        max_tokens=200,
        messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(title=title)}],
    )
    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


test_cases = [
    "高雄市岡山區大雨 多處道路積水嚴重居民叫苦",
    "政府編列預算整治全台易淹水地區 明年完工",
    "台南市學甲區午後大雨積水 部分農田受損",
]

for title in test_cases:
    print(f"\n標題：{title}")
    result = test_prompt(title)
    print(f"結果：{json.dumps(result, ensure_ascii=False, indent=2)}")
