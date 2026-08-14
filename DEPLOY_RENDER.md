# Render da Deploy Qilish Bo'yicha To'liq Qo'llanma 🚀

Ushbu loyiha **Render** platformasida 100% moslashgan va qulay ishlaydigan qilib tuzilgan.

---

## 1-USUL: Render Blueprint (1-Click / Eng oson usul) 🌟

Loyihada `render.yaml` fayli mavjud. Bu fayl bitta tugma bilan quyidagilarni yaratadi:
1. **Web Service** (FastAPI + aiogram Telegram Webhook)
2. **Managed PostgreSQL** (pgvector bilan)
3. **Managed Redis**

### Qadamlar:
1. Loyihangizni **GitHub** yoki **GitLab** repozitoriyasiga yuklang (`git push`).
2. [Render Dashboard](https://dashboard.render.com/) ga kiring.
3. **"New"** -> **"Blueprint"** tugmasini bosing.
4. Repozitoriyangizni tanlang.
5. Render avtomatik ravishda `render.yaml` ni o'qiydi va quyidagi Environment Variablelarni so'raydi:
   - `TELEGRAM_BOT_TOKEN` — @BotFather dan olingan bot tokeni.
   - `GEMINI_API_KEY` — Google AI Studio dan olingan Gemini API kaliti.
   - `ADMIN_USER_IDS` — Sizning Telegram ID raqamingiz (masalan: `123456789`).
6. **"Apply"** tugmasini bosing.
7. Render barcha xizmatlarni (Web, Database, Redis) avtomatik ishga tushiradi.

---

## 2-USUL: Manual (Qo'lda sozlash) ⚙️

Agar barchasini alohida qo'lda ulamoqchi bo'lsangiz:

### 1. PostgreSQL Baza yaratish:
1. Renderda **"New" -> "PostgreSQL"** tanlang.
2. Nomi: `unicon-ai-db`
3. Region: `Frankfurt (EU Central)`
4. Plan: `Free` yoki `Starter`
5. Yaratilgandan so'ng, **"Internal Database URL"** dan nusxa oling.

### 2. Web Service yaratish:
1. Renderda **"New" -> "Web Service"** tanlang.
2. Repozitoriyangizni ulang.
3. Sozlamalar:
   - **Name:** `unicon-ai-assistant`
   - **Region:** `Frankfurt (EU Central)`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/healthz`

### 3. Environment Variables (Muhit o'zgaruvchilari):
Web Servicening **"Environment"** bo'limiga quyidagilarni kiriting:

| Kalit (Key) | Qiymat (Value) misoli | Izoh |
| :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | `1234567890:ABCdef...` | @BotFather dan |
| `GEMINI_API_KEY` | `AIzaSy...` | Google AI Studio dan |
| `ADMIN_USER_IDS` | `123456789` | Shaxsiy Telegram ID |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host/db` | Render Postgres Internal URL |
| `REDIS_URL` | `redis://...` | (Ixtiyoriy) Render Redis URL |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini modeli |
| `EMBEDDING_MODEL` | `text-embedding-004` | Vektor modeli |
| `WEBHOOK_URL` | `https://unicon-ai-assistant.onrender.com` | Web Service bergan URL |
| `WEBHOOK_PATH` | `/webhook/telegram` | Webhook endpointi |
| `WEBHOOK_SECRET` | `ixtiyoriy_maxfiy_soz` | Xavfsizlik kaliti |
| `ENVIRONMENT` | `production` | Production rejimi |

---

## 3. Webhook Tekshirish

Deploy yakunlangach, bot Render tomonidan berilgan URL bo'yicha Telegram Webhookni avtomatik sozlaydi.

Tekshirish uchun brauzerda oching:
```
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo
```

Sizda quyidagiga o'xshash javob chiqishi kerak:
```json
{
  "ok": true,
  "result": {
    "url": "https://unicon-ai-assistant.onrender.com/webhook/telegram",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

Endi Telegramda botingizga `/start` yozib bemalol ishlashingiz mumkin! 🚀
