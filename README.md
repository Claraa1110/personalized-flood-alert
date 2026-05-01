# Personalized Flood Alert System｜個人化淹水預警系統

基於 AI 與多源資料融合的個人化淹水風險預警 app。

## 技術棧

- **前端**：React Native + Expo (TypeScript)
- **後端**：FastAPI (Python)
- **資料庫**：PostgreSQL + PostGIS（Supabase 雲端）
- **LLM**：Anthropic Claude API

## 本地開發

```bash
# 1. Clone repo
git clone https://github.com/Claraa1110/personalized-flood-alert.git
cd personalized-flood-alert

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env 填入真實 key

# 3. 啟動後端
docker-compose up

# 4. 啟動前端
cd MobileApp
npx expo start
```

## 主要功能

- 財產管理：新增並管理個人財產位置
- 即時雨量監測：串接 CWA 自動雨量站 API
- 新聞 NLP：分析淹水相關新聞
- 風險評估：結合雨量、地形、財產位置計算風險
- 推播通知：風險達閾值時主動通知

## 專案結構

```
FF/
├── app/                # FastAPI 後端
│   ├── main.py
│   ├── api/
│   ├── models/
│   └── services/
├── MobileApp/          # Expo 前端
│   └── src/
│       ├── navigation/
│       └── screens/
├── Dockerfile
├── docker-compose.yml
└── .env.example
```
