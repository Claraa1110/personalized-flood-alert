import logging
import httpx

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


async def send_push_notifications(
    tokens: list[str],
    title: str,
    body: str,
    badge: int | None = None,
    sound: str | None = "default",
) -> None:
    """對一批 Expo Push Token 發送推播，失敗不拋例外。"""
    valid = [t for t in tokens if t.startswith("ExponentPushToken[")]
    if not valid:
        return

    def make_msg(token: str) -> dict:
        m: dict = {
            "to": token,
            "title": title,
            "body": body,
            "sound": sound,
            "channelId": "flood-alerts",
        }
        if badge is not None:
            m["badge"] = badge
        return m

    messages = [make_msg(token) for token in valid]

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                EXPO_PUSH_URL,
                json=messages,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
        if resp.status_code == 200:
            logger.info("推播已送出 %d 個 token", len(valid))
        else:
            logger.warning("Expo Push API 回傳 %s: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.warning("推播發送失敗（不影響警報記錄）: %s", e)
