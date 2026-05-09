import asyncio
from app.services.news_service import fetch_news, classify_unclassified_news


async def main():
    print("=== Step 1：抓取新聞 ===")
    total = await fetch_news()
    print(f"新增 {total} 則新聞\n")

    print("=== Step 2：LLM 分類 ===")
    classified = await classify_unclassified_news()
    print(f"已分類 {classified} 則\n")


if __name__ == "__main__":
    asyncio.run(main())
