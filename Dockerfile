# Python 版本必須符合 pyproject.toml 的 requires-python (>=3.13)。
# 先前為 3.11，靠 uv 自動下載相容直譯器才能建置，是脆弱的依賴。
FROM python:3.13-slim

WORKDIR /app

# 鎖定 uv 版本，不用 :latest。
# latest 會隨上游發布改變，可能在程式碼完全沒動的情況下讓建置失敗。
COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app/ ./app/

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
