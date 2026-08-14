# UNICON-SOFT AI Technical Assistant 🤖⚡

Senior darajadagi AI texnik yordamchi — UNICON-SOFT muhandislari uchun Telegram bot shaklida yaratilgan. U Telegram texnik guruhlaridagi suhbatlarni jim kuzatib, foydali tajriba va yechimlarni o'rganib boradi, shaxsiy ko'rsatmalarni yodda saqlaydi, screenshotlar va fayllarni tahlil qiladi hamda RAG (Retrieval-Augmented Generation) orqali tabiiy tilda yordam beradi.

---

## 🌟 Asosiy Xususiyatlar

1. **Tabiiy Muloqot (Human-like UX):**
   - Javoblar qisqa, do'stona, samimiy va professional (O'zbekcha / Lotin).
   - Sun'iy "AI Analysis", "Confidence" kabi robotcha bloklar yo'q.
   - Foydalanuvchining shaxsiy ko'rsatmalari (`Eslab qol: ...`) eng yuqori ustuvorlikka ega.

2. **Guruhlarni Jim Kuzatish (Silent Group Learning):**
   - Guruhlarga qo'shilganda default holatda **Learning = ON, Reply = OFF**.
   - Guruh suhbatlaridagi shovqin ("salom", "rahmat", reaksiyalar) filtrlanadi.
   - Muammo -> Sabab -> Yechim -> Ishtirokchilar -> Xabar havolasi shaklida avtomatik ajratib olinadi.
   - Guruhda faqat `@bot_username` bilan chaqirilgandagina javob beradi.

3. **Screenshot & Vision Tahlili:**
   - Xatolik skrinshotlarini (500, 502, Stack Trace, Postman, Terminal) Gemini Vision orqali tahlil qiladi.
   - OCR matni, tizim nomi va xatolik sababini ajratadi va bazada saqlaydi.
   - Kelgusida *"O'sha screenshotni tashlab ber"* deyilsa, topib beradi.

4. **Fayllarni O'rganish:**
   - PDF, DOCX, TXT, CSV, XLSX formatdagi hujjatlarni o'qib, bilimlar bazasiga indekslaydi.

5. **RAG & Hybrid Search:**
   - PostgreSQL + pgvector (vektorli semantik qidiruv) + matnli kalit so'zlar qidiruvi + manba ishonchliligi reytingi.

6. **Xavfsizlik & Boshqaruv:**
   - `ADMIN_USER_IDS` orqali faqat ruxsat berilgan muhandislarga shaxsiy chatdan foydalanish huquqi.
   - Destruktiv amallar (barcha bilimlarni o'chirish) uchun tasdiqlash tugmalari (`InlineKeyboardMarkup`).
   - `/settings` orqali interaktiv boshqaruv paneli.

---

## 🏗️ Arxitektura va Texnologiyalar

- **Til & Framework:** Python 3.12+, FastAPI, aiogram 3.x
- **AI & Vision:** Google Gemini API (`gemini-2.5-flash`, `text-embedding-004`)
- **Ma'lumotlar bazasi:** PostgreSQL 16 + pgvector
- **ORM & Migrations:** SQLAlchemy 2.0 (Asyncio), Alembic
- **Background Tasks:** Redis Queue / Asyncio In-Memory Queue
- **Deployment:** Render (Docker, Web Service, Webhook, Managed Postgres & Redis)

---

## 🚀 Tezkor Ishga Tushirish (Lokal)

### 1. Repozitoriyani klonlash va virtual muhit:
```bash
git clone <repo-url>
cd uniai
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. `.env` faylini sozlash:
`.env.example` dan nusxa olib `.env` yarating:
```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
GEMINI_API_KEY=AIzaSy...
ADMIN_USER_IDS=123456789,987654321
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/unicon_ai
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=development
```

### 3. Docker Compose orqali ishga tushirish (PostgreSQL + pgvector + Redis):
```bash
docker-compose up --build
```

Yoki to'g'ridan-to'g'ri Python orqali:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🌐 Render da Deploy Qilish

To'liq qo'llanma uchun [DEPLOY_RENDER.md](file:///c:/Users/naimi/Desktop/for cv/uniai/DEPLOY_RENDER.md) fayliga qarang.

---

## 🧪 Testlarni Ishga Tushirish

```bash
pytest tests/ -v
```
