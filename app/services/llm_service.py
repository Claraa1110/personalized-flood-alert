import json
import logging
import os
from openai import OpenAI

logger = logging.getLogger(__name__)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def get_llm_client():
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )


def extract_locations(title: str) -> list[str]:
    """從新聞標題抽取台灣地名"""
    client = get_llm_client()

    prompt = f"""你是地名抽取助理。請從以下新聞標題中，抽取所有台灣的縣市或鄉鎮市區地名。

回答規則：
- 只回答 JSON 格式，不要其他文字
- locations：地名陣列（只要台灣的行政區地名）
- 如果沒有地名，回傳空陣列

新聞標題：{title}

回答格式：
{{"locations": ["高雄市", "岡山區"]}}"""

    try:
        response = get_llm_client().chat.completions.create(
            model="openai/gpt-4o-mini",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        result_text = response.choices[0].message.content.strip()

        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]

        data = json.loads(result_text)
        return data.get("locations", [])

    except Exception as e:
        logger.error(f"地名抽取失敗：{e}")
        return []
