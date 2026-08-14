"""
Comprehensive knowledge seeder for UNICON-SOFT platforms:
- mahalla.ijro.uz (Mahalla yettiligi va fuqarolar arizalari)
- edo.ijro.uz (Elektron hujjat aylanish tizimi va ijro intizomi)
- lawyer.ijro.uz (e-huquqshinos yuridik xizmat portali)
- E-IMZO & OneID umumiy texnik yechimlari
"""
import asyncio
from typing import List, Dict, Any
from sqlalchemy import text, select

from app.db.session import async_session_factory
from app.db.models import Knowledge, KnowledgeSource, KnowledgeEmbedding, SourceType
from app.ai.gemini_client import gemini_client
from app.utils.logger import logger


KNOWLEDGE_DATA: List[Dict[str, Any]] = [
    # ==========================================
    # 1. MAHALLA.IJRO.UZ PLATFORMASI
    # ==========================================
    {
        "title": "mahalla.ijro.uz: E-IMZO moduli ulanmadi yoki xatolik (12111/12112 port)",
        "system_name": "mahalla.ijro.uz",
        "category": "e_imzo_eri",
        "problem": "mahalla.ijro.uz saytida ERI kalit orqali kirishda 'E-IMZO moduli bilan aloqa yo'q' yoki 'Connection refused :12111 / :12112' xatoligi chiqishi.",
        "possible_cause": "Kompyuterda E-IMZO dasturi ishga tushirilmagan, antivirus portni bloklagan yoki brauzer xavfsizlik sertifikatini qabul qilmagan.",
        "solution": (
            "1. Kompyuterning pastki o'ng burchagida (tray) E-IMZO belgisi (yashil) borligini tekshiring. Agar bo'lmasa, 'Pusk' menyusidan E-IMZO dasturini ishga tushiring.\n"
            "2. Brauzerda yangi oyna ochib https://127.0.0.1:12111 yoki https://127.0.0.1:12112 manziliga kiring va 'Kengaytirilgan' (Advanced) -> 'Saytga o'tish' (Proceed) tugmasini bosing.\n"
            "3. E-IMZO dasturini eng so'nggi versiyaga yangilang (e-imzo.uz yoki eri.yt.uz dan yuklab oling).\n"
            "4. Brauzerni qayta ishga tushiring (Ctrl+F5)."
        ),
        "tags": ["mahalla", "e-imzo", "kirish", "eri", "port12111", "port12112"]
    },
    {
        "title": "mahalla.ijro.uz: Mahalla yettiligi a'zosiga rol yoki lavozim biriktirilmagan",
        "system_name": "mahalla.ijro.uz",
        "category": "tizimga_kirish",
        "problem": "mahalla.ijro.uz ga ERI yoki OneID bilan kirganda 'Foydalanuvchiga rol biriktirilmagan' yoki 'Ruxsat etilmagan' deb chiqishi.",
        "possible_cause": "Xodimning JSHSHIR (PINFL) raqamiga tuman hokimligi yoki mas'ul administrator tomonidan tegishli mahalla va lavozim roli biriktirilmagan.",
        "solution": (
            "1. Tuman hokimligi EDO/Mahalla tizim mas'ul administratoriga yoki viloyat boshqarmasi moderatoriga murojaat qiling.\n"
            "2. Xodimning JSHSHIR raqami, F.I.SH va lavozimga tayinlash haqidagi buyruq nusxasini taqdim eting.\n"
            "3. Admin tomonidan xodim 'Mahalla tuzilmasi' reyestridan qidirilib, unga tegishli mahalla kodi va faol lavozim roli (Rais, Hokim yordamchisi, Xotin-qizlar faoli, Yoshlar yetakchisi va h.k.) biriktiriladi.\n"
            "4. Rol biriktirilgach, tizimdan chiqib qayta kiring."
        ),
        "tags": ["mahalla", "rol", "lavozim", "yettilik", "kirish", "ruxsat"]
    },
    {
        "title": "mahalla.ijro.uz: Fuqaro arizasi yoki tavsiyanomasini imzolashda 502/500 xatosi",
        "system_name": "mahalla.ijro.uz",
        "category": "texnik_nosozlik",
        "problem": "mahalla.ijro.uz da fuqaro arizasini ko'rib chiqib, ijobiy/salbiy tavsiyanomani ERI bilan imzolash tugmasi bosilganda 502 Bad Gateway yoki 500 Server Error chiqishi.",
        "possible_cause": "Yuklangan biriktirilgan fayl hajmi juda kattaligi (20MB dan ortiq), noto'g'ri format yoki serverdagi vaqtinchalik yuklama.",
        "solution": (
            "1. Biriktirilayotgan xulosa va hujjat fayllarini faqat PDF yoki JPG formatda, hajmini 5 MB dan kichik qilib yuklang.\n"
            "2. Fayl nomida o'zbekcha maxsus harflar (o', g', q, h) va belgilar o'rniga faqat lotin harflaridan foydalaning (masalan: tavsiyanoma_ariza.pdf).\n"
            "3. Agar 502 Bad Gateway chiqsa, 5-10 daqiqa kutib sahifani Ctrl+Shift+R bilan yangilang va qayta imzolang."
        ),
        "tags": ["mahalla", "ariza", "tavsiyanoma", "imzolash", "502", "fayl"]
    },
    {
        "title": "mahalla.ijro.uz: OneID orqali kirishda ma'lumotlar mos kelmadi xatoligi",
        "system_name": "mahalla.ijro.uz",
        "category": "tizimga_kirish",
        "problem": "OneID (id.egov.uz) orqali kirish tugmasi bosilganda 'OneID ma'lumotlari mos kelmadi' yoki profil ochilmasligi.",
        "possible_cause": "Foydalanuvchi pasportini yangilagan (ID karta olgan) lekin OneID dagi shaxsiy ma'lumotlar yangilanmagan, yoki telefon raqam tasdiqlanmagan.",
        "solution": (
            "1. Yangi oynada https://id.egov.uz portaliga kiring.\n"
            "2. Shaxsiy kabinetga kirib, 'Mening profilim' bo'limiga o'ting.\n"
            "3. 'Passport ma'lumotlarini yangilash' (IIV bazasidan yangilash) tugmasini bosing.\n"
            "4. Telefon raqamingiz va JSHSHIR to'g'riligini tekshiring.\n"
            "5. Shundan so'ng mahalla.ijro.uz ga qaytib, qayta kiring."
        ),
        "tags": ["mahalla", "oneid", "kirish", "id.egov.uz", "passport", "jshshir"]
    },
    {
        "title": "mahalla.ijro.uz: Ijtimoiy himoya yagona reyestri bilan integratsiya xatosi",
        "system_name": "mahalla.ijro.uz",
        "category": "integratsiya",
        "problem": "Moddiy yordam yoki subsidiya tayinlashda 'Ijtimoiy himoya reyestri servisi javob bermadi' xabari chiqishi.",
        "possible_cause": "'Inson' agentligi integratsiya shlyuzida vaqtinchalik texnik profilaktika ishlari olib borilayotgani.",
        "solution": (
            "1. Bu tashqi vazirlik servisi kechikishi bo'lib, odatda 15-30 daqiqada avtomatik tiklanadi.\n"
            "2. Fuqaroning JSHSHIR raqami to'g'ri kiritilganini qayta tekshiring.\n"
            "3. Agar muammo 2 soatdan ortiq davom etsa, tuman 'Inson' ijtimoiy xizmatlar markazi IT mutaxassisiga yoki ijro.uz qo'llab-quvvatlash xizmatiga xabar bering."
        ),
        "tags": ["mahalla", "inson", "ijtimoiy_himoya", "integratsiya", "subsidiya"]
    },

    # ==========================================
    # 2. EDO.IJRO.UZ PLATFORMASI
    # ==========================================
    {
        "title": "edo.ijro.uz: Hujjatga rezolyutsiya qo'yish va ijro muddatini belgilash xatolari",
        "system_name": "edo.ijro.uz",
        "category": "hujjat_aylanishi",
        "problem": "edo.ijro.uz da hujjatga rezolyutsiya qo'yganda yoki xodimga yo'naltirganda 'Muddat asosiy topshiriq muddatidan katta bo'lishi mumkin emas' xatosi.",
        "possible_cause": "Oraliq ijrochiga belgilangan sana nazorat kartasidagi yakuniy topshiriq muddatidan keyingi sanaga qo'yilgan.",
        "solution": (
            "1. Nazorat kartochkasidagi yakuniy ijro muddatini (Nazorat sanasi) tekshiring.\n"
            "2. Barcha quyi ijrochilar uchun belgilangan ijro muddati asosiy muddatdan kamida 1-2 kun oldin bo'lishi kerak.\n"
            "3. Agar umumiy muddatni uzaytirish zarur bo'lsa, yuqori turuvchi organga 'Muddat uzaytirish so'rovi' (Prodlenniya) yuboring."
        ),
        "tags": ["edo", "rezolyutsiya", "muddat", "ijro_nazorati", "topshiriq"]
    },
    {
        "title": "edo.ijro.uz: QR-kodli hujjat shakllanmasligi yoki imzo blankada ko'rinmasligi",
        "system_name": "edo.ijro.uz",
        "category": "hujjat_aylanishi",
        "problem": "Yuborilgan xat yoki buyruqning yakuniy PDF nusxasida QR-kod bo'sh chiqishi yoki barcha rahbarlar imzosi tushmasligi.",
        "possible_cause": "Hujjat hali barcha viza qo'yuvchilar tomonidan to'liq imzolanib yakunlanmagan yoki PDF-generator xizmati navbatda turibdi.",
        "solution": (
            "1. Hujjat kartochkasidagi 'Vizalar va imzolar' (Istoriya soglasovaniya) bo'limini ochib, barcha mas'ullarning E-IMZO imzosi qo'yilganini tekshiring.\n"
            "2. Agar barcha imzolar qo'yilgan bo'lsa, 'PDFni qayta shakllantirish' (Peregenerirovat PDF) tugmasini bosing.\n"
            "3. Brauzer keshini tozalab (Ctrl+F5), hujjatni qayta yuklab oling."
        ),
        "tags": ["edo", "qr-kod", "pdf", "imzo", "viza", "blank"]
    },
    {
        "title": "edo.ijro.uz: Tashkilotlararo hujjat yuborishda tashkilot qidiruvda topilmadi",
        "system_name": "edo.ijro.uz",
        "category": "tizimga_kirish",
        "problem": "edo.ijro.uz da chiquvchi xatni boshqa davlat organiga yuborishda tashkilot nomi bo'yicha qidiruvda chiqmasligi.",
        "possible_cause": "Tashkilot nomi o'zgargan, qayta tashkil qilingan yoki tashkilotning EDO ID (STIR / INN) raqami noto'g'ri kiritilmoqda.",
        "solution": (
            "1. Tashkilotni nomi bo'yicha emas, balki rasmiy STIR (INN) raqami bo'yicha qidiring.\n"
            "2. Agar tashkilot yangi tashkil etilgan bo'lsa, tashkilot administratori UNICON-SOFT qo'llab-quvvatlash xizmatiga EDO tizimida ro'yxatdan o'tish arizasini berishi kerak.\n"
            "3. Vaqtinchalik muammo bo'lsa, qabul qiluvchi tashkilot EDO admini bilan bog'lanib, ularning tizim holatini tekshirib oling."
        ),
        "tags": ["edo", "tashkilot", "stir", "inn", "chiquvchi_xat", "qidiruv"]
    },
    {
        "title": "edo.ijro.uz: Sessiya tugashi yoki 401/403 Xatolik (Foydalanuvchi bloklangan)",
        "system_name": "edo.ijro.uz",
        "category": "tizimga_kirish",
        "problem": "Tizimda ishlayotganda '401 Unauthorized' yoki '403 Forbidden' chiqib, sahifadan chiqarib yuborishi.",
        "possible_cause": "Bir xil hisob yozuviga bir vaqtning o'zida bir nechta kompyuter yoki brauzerdan kirilgan, yoki sessiya muddati (30 daqiqa) tugagan.",
        "solution": (
            "1. Boshqa kompyuter yoki ochiq brauzer oynalaridan tizimdan chiqing.\n"
            "2. Brauzeringizning kesh va cookie fayllarini tozalang (Ctrl+Shift+Delete -> Cookie va keshni o'chirish).\n"
            "3. E-IMZO orqali qayta avtorizatsiyadan o'ting."
        ),
        "tags": ["edo", "401", "403", "sessiya", "xavfsizlik", "kirish"]
    },
    {
        "title": "edo.ijro.uz: Xodimga hujjat yo'naltirishda (Pereadresatsiya) xodim ismi chiqmasligi",
        "system_name": "edo.ijro.uz",
        "category": "hujjat_aylanishi",
        "problem": "Hujjatni boshqa xodimga ijro uchun yo'naltirishda xodimlar ro'yxatida kerakli mutaxassis ko'rinmasligi.",
        "possible_cause": "Kadrlar reyestrida xodim mehnat ta'tilida, xizmat safarida yoki boshqa bo'limga o'tkazilgan deb belgilangan.",
        "solution": (
            "1. Tashkilotingiz kadrlar bo'limi mas'uli (Kadr moderatori)ga murojaat qiling.\n"
            "2. Kadrlar bo'limi EDO da 'Tashkiliy tuzilma' (Struktura) bo'limidan xodimning holatini (Status: Faol) tekshirishi kerak.\n"
            "3. Agar xodim yangi ishga olingan bo'lsa, unga EDO tizimida shtat birligi va kerakli huquqlar (ijrochi, viza qo'yuvchi) biriktiriladi."
        ),
        "tags": ["edo", "xodim", "kadr", "pereadresatsiya", "topshiriq", "struktura"]
    },

    # ==========================================
    # 3. LAWYER.IJRO.UZ (E-HUQUQSHINOS) PLATFORMASI
    # ==========================================
    {
        "title": "lawyer.ijro.uz: Yuridik xulosani E-IMZO bilan tasdiqlashda xatolik",
        "system_name": "lawyer.ijro.uz",
        "category": "e_imzo_eri",
        "problem": "e-huquqshinos portalida buyruq yoki shartnoma loyihasiga yuridik xulosa berib, imzolash tugmasi bosilganda imzo qabul qilinmasligi.",
        "possible_cause": "Yuristning E-IMZO kalitidagi JSHSHIR yoki STIR raqami e-huquqshinos tizimidagi yurist profiliga to'g'ri biriktirilmagan.",
        "solution": (
            "1. E-IMZO kalitingiz aynan yuridik xizmat ko'rsatish markazi (YXKM) yoki tashkilot yuristi nomiga olinganini tekshiring.\n"
            "2. Shaxsiy kabinetda JSHSHIR va sertifikat ma'lumotlari to'g'riligini solishtiring.\n"
            "3. Agar kalit yangilangan bo'lsa, Adliya vazirligi yoki tuman YXKM mas'ul adminiga murojaat qilib, yangi E-IMZO sertifikatini profilga biriktiring.\n"
            "4. E-IMZO dasturini qayta ishga tushirib, imzolashni takrorlang."
        ),
        "tags": ["lawyer", "e-huquqshinos", "yurist", "xulosa", "imzolash", "eri"]
    },
    {
        "title": "lawyer.ijro.uz: Loyihani rad etishda (Salbiy xulosa) qonunchilik asosini kiritish talabi",
        "system_name": "lawyer.ijro.uz",
        "category": "foydalanuvchi_xatosi",
        "problem": "e-huquqshinos da qonunchilikka zid loyihaga rad javobi berishda tizim xatolik berishi yoki saqlanmasligi.",
        "possible_cause": "Rad etish sababi maydonida qonunchilik hujjati nomi, moddasi va Lex.uz havolasi to'liq to'ldirilmagan.",
        "solution": (
            "1. Tizim talabiga ko'ra, rad etish sababi kamida 20 ta belgidan iborat asosli matn bo'lishi shart.\n"
            "2. Aniq buzilgan qonun hujjati (Masalan: 'O'zbekiston Respublikasi Mehnat kodeksining 161-moddasi talablariga zid') ko'rsatilishi kerak.\n"
            "3. Kamchiliklar bandma-band yozilgach, 'Salbiy xulosa berish' tugmasi bosiladi."
        ),
        "tags": ["lawyer", "e-huquqshinos", "rad_etish", "salbiy_xulosa", "qonun", "lex.uz"]
    },
    {
        "title": "lawyer.ijro.uz: e-huquqshinos va EDO o'rtasida hujjat sinxronizatsiyasi kechikishi",
        "system_name": "lawyer.ijro.uz",
        "category": "integratsiya",
        "problem": "e-huquqshinos da ijobiy xulosa berilgan buyruq yoki qaror loyihasi edo.ijro.uz tizimida ko'rinmay qolishi.",
        "possible_cause": "Tizimlararo integratsiya shlyuzida (API Gateway) navbat hosil bo'lgani yoki hujjat raqami duplikatsiyasi.",
        "solution": (
            "1. e-huquqshinos portalida hujjat kartochkasini oching.\n"
            "2. Hujjat holati (Status) 'EDO ga yuborildi' (Otpravleno v EDO) ekanligini tekshiring.\n"
            "3. Agar 'Xatolik' bo'lsa, 'Qayta yuborish' (Povtorit otpravku) tugmasini bosing.\n"
            "4. 5 daqiqa ichida hujjat edo.ijro.uz tizimining 'Kelishuvda' (Na soglasovanii) bo'limida paydo bo'ladi."
        ),
        "tags": ["lawyer", "edo", "integratsiya", "sinxronizatsiya", "buyruq", "xulosa"]
    },
    {
        "title": "lawyer.ijro.uz: Sudga da'vo arizasi shakllantirishda sud instansiyasi xatosi",
        "system_name": "lawyer.ijro.uz",
        "category": "hujjat_aylanishi",
        "problem": "Sudga da'vo arizasi yoki shikoyat tayyorlashda 'Sud klassifikatori yuklanmadi' yoki da'vo arizasini jo'natib bo'lmasligi.",
        "possible_cause": "E-XSUD integratsiyasida tuman/shahar sudi kodi noto'g'ri tanlangan yoki davlat boji rekvizitlari kiritilmagan.",
        "solution": (
            "1. Sud turi (Fuqarolik, Iqtisodiy, Ma'muriy yoki Jinoyat ishlari sudi) to'g'ri tanlanganini tekshiring.\n"
            "2. Sud joylashgan hudud (Viloyat va tuman sudi) klassifikatordan qayta tanlang.\n"
            "3. Davlat boji to'langanligi haqidagi to'lov topshirig'i (Kvitansiya) PDF shaklida biriktirilishi shart."
        ),
        "tags": ["lawyer", "sud", "davo_arizasi", "e-xsud", "davlat_boji"]
    },

    # ==========================================
    # 4. UMUMIY E-IMZO VA BROWSER SOZLAMALARI
    # ==========================================
    {
        "title": "Umumiy: E-IMZO kalit paroli bloklangan yoki unutilgan holatda nima qilish kerak?",
        "system_name": "barcha_tizimlar",
        "category": "e_imzo_eri",
        "problem": "E-IMZO kalit paroli ketma-ket 3 marta noto'g'ri terilib bloklanganda yoki parol esdan chiqqanda.",
        "possible_cause": "Xavfsizlik tizimi ERI kalitni avtomatik bloklagan.",
        "solution": (
            "1. ERI kalit parolini masofadan tiklab bo'lmaydi (xavfsizlik talabi).\n"
            "2. Agar kalit jismoniy shaxs yoki yakka tartibdagi tadbirkorga tegishli bo'lsa, my.gov.uz yoki e-imzo.uz orqali yangi ERI kalit olinadi (Face-ID orqali 2 daqiqada).\n"
            "3. Agar yuridik shaxs yoki davlat organi ERI kaliti bo'lsa, Davlat xizmatlari markaziga (DXM) yoki Soliq inspeksiyasiga yangi kalit olish uchun murojaat qilinadi."
        ),
        "tags": ["e-imzo", "parol", "blok", "eri", "my.gov.uz", "dsq"]
    },
    {
        "title": "Umumiy: Fleshka (USB) dagi DSQ kaliti E-IMZO dasturida ko'rinmayapti",
        "system_name": "barcha_tizimlar",
        "category": "e_imzo_eri",
        "problem": "Fleshkadagi DSQ kaliti E-IMZO ro'yxatida ko'rinmasligi.",
        "possible_cause": "Fleshkadagi kalit fayllari 'DSQ' nomli jildda (papka) joylashmagan yoki fleshka formati o'zgargan.",
        "solution": (
            "1. Fleshkaning asosiy ildizida 'DSQ' nomli papka oching (katta harflar bilan: DSQ).\n"
            "2. Barcha kalit fayllarini (.pfx yoki pfx bo'lmagan raqamli fayllar) shu 'DSQ' papkasi ichiga joylashtiring.\n"
            "3. E-IMZO dasturida 'Fleshkadan yangilash' (Obnovit) tugmasini bosing."
        ),
        "tags": ["e-imzo", "fleshka", "usb", "dsq", "pfx", "kalit"]
    },
    {
        "title": "Umumiy: Brauzerda ijro.uz saytlari '504 Gateway Timeout' yoki sekin ishlaganda",
        "system_name": "barcha_tizimlar",
        "category": "texnik_nosozlik",
        "problem": "Sahifalar juda sekin yuklanishi yoki 504 Gateway Timeout xatosi berishi.",
        "possible_cause": "Brauzer keshining to'lib ketishi, provayder DNS kechikishi yoki platformada yuqori yuklama payti.",
        "solution": (
            "1. Google Chrome yoki Yandex brauzerida keshni tozalash: Ctrl+Shift+Delete -> 'Barcha vaqt uchun kesh fayllari'ni tanlang va tozalang.\n"
            "2. DNS keshini tozalash: Windows buyruqlar satrida (cmd): `ipconfig /flushdns` buyrug'ini bajaring.\n"
            "3. Brauzer kengaytmalarida ortiqcha VPN yoki proxy plaginlarini o'chirib qo'ying."
        ),
        "tags": ["504", "timeout", "kesh", "brauzer", "flushdns", "tezlik"]
    }
]


async def seed_knowledge_base(clear_existing: bool = True) -> int:
    """Clears existing knowledge and seeds comprehensive technical problems & solutions."""
    logger.info("Starting knowledge base seeding...")

    async with async_session_factory() as session:
        if clear_existing:
            logger.info("Clearing old knowledge base records...")
            # Cascading deletion via raw SQL for clean wipe
            await session.execute(text("DELETE FROM knowledge_embeddings;"))
            await session.execute(text("DELETE FROM knowledge_sources;"))
            await session.execute(text("DELETE FROM attachments;"))
            await session.execute(text("DELETE FROM knowledge;"))
            await session.commit()
            logger.info("Existing knowledge base wiped cleanly.")

        inserted_count = 0

        for item in KNOWLEDGE_DATA:
            # Generate embedding using Gemini
            full_text = f"{item['title']} {item['problem']} {item['possible_cause']} {item['solution']}"
            try:
                emb = await gemini_client.generate_embedding(full_text)
            except Exception as e:
                logger.warning(f"Embedding generation error for {item['title']}: {e}")
                emb = None

            knowledge = Knowledge(
                title=item["title"],
                problem=item["problem"],
                possible_cause=item["possible_cause"],
                solution=item["solution"],
                raw_content=full_text,
                category=item["category"],
                system_name=item["system_name"],
                confidence=1.0,
                confidence_score=1.0,
                trust_score=1.0,
                verified_by_user=True,
                is_active=True,
                is_deleted=False,
                tags=item["tags"],
                tags_list=item["tags"]
            )
            session.add(knowledge)
            await session.flush()

            source = KnowledgeSource(
                knowledge_id=knowledge.id,
                source_type=SourceType.USER,
                source_id="official_knowledge_base",
                author="UNICON-SOFT Texnik Hujjatlari",
                source_group_name="Official Documentation",
                metadata_json={"source": "official_manual", "system": item["system_name"]}
            )
            session.add(source)

            if emb:
                emb_record = KnowledgeEmbedding(
                    knowledge_id=knowledge.id,
                    embedding=emb,
                    embedding_json=emb,
                    model_name="gemini-embedding-001"
                )
                session.add(emb_record)

            inserted_count += 1
            logger.info(f"Seeded [{inserted_count}/{len(KNOWLEDGE_DATA)}]: {item['title']}")

        await session.commit()
        logger.info(f"Successfully seeded {inserted_count} knowledge records!")
        return inserted_count


if __name__ == "__main__":
    asyncio.run(seed_knowledge_base(clear_existing=True))
