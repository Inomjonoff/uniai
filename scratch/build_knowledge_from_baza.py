import os
import glob
import re
import json
import sys
from html import unescape
from html.parser import HTMLParser
from typing import Dict, List, Any

sys.stdout.reconfigure(encoding='utf-8')

class TelegramHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.messages = []
        self.current_msg = None
        self.in_from_name = False
        self.in_text = False
        self.in_reply = False
        self.current_text = []
        self.current_from = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "").split()
        
        if tag == "div" and "message" in classes and "default" in classes:
            msg_id = attrs_dict.get("id", "")
            self.current_msg = {
                "id": msg_id,
                "author": "",
                "text": "",
                "reply_to": None,
                "date": ""
            }
        elif tag == "div" and "from_name" in classes and self.current_msg:
            self.in_from_name = True
            self.current_from = []
        elif tag == "div" and "reply_to" in classes and self.current_msg:
            self.in_reply = True
        elif tag == "a" and self.in_reply and self.current_msg:
            href = attrs_dict.get("href", "")
            if "#go_to_message" in href:
                m_id = href.split("#go_to_message")[-1]
                self.current_msg["reply_to"] = f"message{m_id}"
        elif tag == "div" and "text" in classes and self.current_msg:
            self.in_text = True
            self.current_text = []

    def handle_endtag(self, tag):
        if tag == "div":
            if self.in_from_name:
                self.in_from_name = False
                if self.current_msg:
                    self.current_msg["author"] = "".join(self.current_from).strip()
            elif self.in_reply:
                self.in_reply = False
            elif self.in_text:
                self.in_text = False
                if self.current_msg:
                    self.current_msg["text"] = unescape("".join(self.current_text)).strip()
            elif self.current_msg and self.current_msg.get("text"):
                self.messages.append(self.current_msg)
                self.current_msg = None

    def handle_data(self, data):
        if self.in_from_name:
            self.current_from.append(data)
        elif self.in_text:
            self.current_text.append(data)


def clean_text(t: str) -> str:
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def extract_knowledge_from_baza():
    baza_dir = r"c:\Users\naimi\Desktop\for cv\uniai\baza"
    html_files = sorted(set(
        glob.glob(os.path.join(baza_dir, "*.html")) +
        glob.glob(os.path.join(baza_dir, "**", "*.html"), recursive=True)
    ))

    print(f"Reading {len(html_files)} HTML files from baza...")
    all_messages_by_id = {}
    chat_by_msg_id = {}

    for f in html_files:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                raw_html = fp.read()
                m = re.search(r'<div class="text bold">\s*([^<]+)\s*</div>', raw_html[:4000])
                chat_title = unescape(m.group(1).strip()) if m else "edo.ijro.uz"
                
                parser = TelegramHTMLParser()
                parser.feed(raw_html)
                
                for msg in parser.messages:
                    msg["chat"] = chat_title
                    all_messages_by_id[msg["id"]] = msg
                    chat_by_msg_id[msg["id"]] = chat_title
        except Exception as e:
            print(f"Error {f}: {e}")

    print(f"Total messages parsed: {len(all_messages_by_id):,}")

    # Build High-Value Knowledge Entries
    knowledge_items = []
    seen_problems = set()

    # 1. Process Official Announcements & Manuals
    for msg in all_messages_by_id.values():
        text = msg["text"]
        chat = msg["chat"]
        
        # Determine system
        if "huquqshunos" in chat.lower() or "lawyer" in text.lower():
            sys_name = "lawyer.ijro.uz"
        elif "mahalla" in text.lower() or "yettilik" in text.lower():
            sys_name = "mahalla.ijro.uz"
        else:
            sys_name = "edo.ijro.uz"

        # Check for valuable technical manuals / guides
        if len(text) >= 80:
            is_manual = any(w in text.lower() for w in [
                "yo'riqnoma", "qo'llanma", "diqqat", "tartibi", "tizimda yangi",
                "sozlash", "qoidasi", "e-imzo", "call markaz", "71 200", "adliya"
            ])
            if is_manual:
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                title = lines[0][:120]
                problem = f"Foydalanuvchilar uchun {sys_name} tizimi bo'yicha muhim qo'llanma / tartib"
                
                # Deduplication key
                dedup_key = re.sub(r'[^a-zA-Z0-9]', '', title.lower()[:50])
                if dedup_key not in seen_problems and len(dedup_key) > 10:
                    seen_problems.add(dedup_key)
                    knowledge_items.append({
                        "title": f"[{sys_name}] {title}",
                        "system_name": sys_name,
                        "category": "rasmiy_yoriqnoma",
                        "problem": problem,
                        "possible_cause": "Tizim qoidalari va standart ishlash tartibi",
                        "solution": text,
                        "tags": [sys_name.split(".")[0], "qo'llanma", "tartib"]
                    })

    # 2. Process QA Pairs
    for msg in all_messages_by_id.values():
        reply_to_id = msg.get("reply_to")
        if not reply_to_id or reply_to_id not in all_messages_by_id:
            continue
        
        parent = all_messages_by_id[reply_to_id]
        q_text = clean_text(parent["text"])
        a_text = clean_text(msg["text"])
        chat = msg["chat"]

        if len(q_text) < 25 or len(a_text) < 25:
            continue

        # Check if question is technical
        has_tech_kw = any(w in q_text.lower() for w in [
            "qanday", "qilsa bo'ladi", "xato", "ochilmayapti", "ishlamayapti",
            "imzolanmayapti", "kirish", "yuborish", "buyruq", "xulosa",
            "502", "504", "403", "401", "muddat", "rezolyutsiya", "kadr",
            "e-imzo", "eri", "dsq", "parol", "sertifikat", "devonxona",
            "stavka", "rad", "salbiy", "ijobiy", "sud", "ariza", "oneid"
        ])

        # Check if answer is explanatory (not just "ha", "yo'q", "salom")
        is_good_answer = len(a_text) >= 30 and not any(a_text.lower().startswith(x) for x in ["assalom", "salom", "raxmat", "rahmat", "ok"])

        if has_tech_kw and is_good_answer:
            if "huquqshunos" in chat.lower() or "lawyer" in q_text.lower() or "xulosa" in q_text.lower():
                sys_name = "lawyer.ijro.uz"
            elif "mahalla" in q_text.lower() or "yettilik" in q_text.lower():
                sys_name = "mahalla.ijro.uz"
            else:
                sys_name = "edo.ijro.uz"

            dedup_key = re.sub(r'[^a-zA-Z0-9]', '', q_text.lower()[:60])
            if dedup_key not in seen_problems and len(dedup_key) > 15:
                seen_problems.add(dedup_key)
                title = f"[{sys_name}] {q_text[:90]}"
                knowledge_items.append({
                    "title": title,
                    "system_name": sys_name,
                    "category": "foydalanuvchi_murojaati",
                    "problem": q_text,
                    "possible_cause": f"Foydalanuvchi {sys_name} tizimida duch kelgan muammo / savol",
                    "solution": a_text,
                    "tags": [sys_name.split(".")[0], "chat_baza", "yechim"]
                })

    print(f"Total curated high-value knowledge items built from baza: {len(knowledge_items)}")

    # Save to JSON
    out_file = r"c:\Users\naimi\Desktop\for cv\uniai\scratch\baza_knowledge.json"
    with open(out_file, "w", encoding="utf-8") as out:
        json.dump(knowledge_items, out, ensure_ascii=False, indent=2)

    print(f"Saved to {out_file}")

if __name__ == "__main__":
    extract_knowledge_from_baza()
