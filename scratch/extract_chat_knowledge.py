import os
import glob
import re
import json
from html import unescape
from html.parser import HTMLParser
from typing import Dict, List, Any, Optional

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


TECHNICAL_KEYWORDS = [
    "e-imzo", "eri", "kalit", "dsq", "parol", "sertifikat", "12111", "12112",
    "xato", "xatolik", "ochilmayapti", "ishlamayapti", "kirib bo'lmayapti",
    "imzolanmayapti", "502", "504", "500", "403", "401", "oneid", "id.egov",
    "jshshir", "pinfl", "stir", "inn", "rezolyutsiya", "muddat", "kadr", "shtat",
    "ariza", "xulosa", "buyruq", "qaror", "sud", "ijro", "edo", "mahalla",
    "lawyer", "yurist", "tavsiyanoma", "pdf", "qr", "browser", "kesh", "cache",
    "qanday", "nima qilish", "yechimi", "qilsa bo'ladi", "qayerdan"
]

NON_TECHNICAL_WORDS = [
    "salom", "assalomu alaykum", "raxmat", "rahmat", "ok", "xa", "yo'q", "ha",
    "kimsiz", "bayram", "tabrik"
]

def is_technical_text(text: str) -> bool:
    t = text.lower()
    if len(t) < 15:
        return False
    # Check if contains technical keyword
    return any(kw in t for kw in TECHNICAL_KEYWORDS)

def analyze_and_extract_qa():
    baza_dir = r"c:\Users\naimi\Desktop\for cv\uniai\baza"
    html_files = sorted(set(
        glob.glob(os.path.join(baza_dir, "*.html")) +
        glob.glob(os.path.join(baza_dir, "**", "*.html"), recursive=True)
    ))

    all_messages_by_id = {}
    messages_by_chat = {}

    for f in html_files:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                raw_html = fp.read()
                m = re.search(r'<div class="text bold">\s*([^<]+)\s*</div>', raw_html[:4000])
                chat_title = unescape(m.group(1).strip()) if m else "edo.ijro.uz"
                
                parser = TelegramHTMLParser()
                parser.feed(raw_html)
                
                if chat_title not in messages_by_chat:
                    messages_by_chat[chat_title] = []
                
                for msg in parser.messages:
                    msg["chat"] = chat_title
                    all_messages_by_id[msg["id"]] = msg
                    messages_by_chat[chat_title].append(msg)
        except Exception as e:
            print(f"Error {f}: {e}")

    print(f"Total parsed unique messages across all chats: {len(all_messages_by_id):,}")

    qa_pairs = []
    announcements = []

    for msg in all_messages_by_id.values():
        text = msg["text"]
        
        # 1. Check if this is a reply to another message
        reply_to_id = msg.get("reply_to")
        if reply_to_id and reply_to_id in all_messages_by_id:
            parent_msg = all_messages_by_id[reply_to_id]
            parent_text = parent_msg["text"]
            
            # If parent was a question/problem and reply is a substantial solution
            if is_technical_text(parent_text) and len(text) > 20:
                qa_pairs.append({
                    "chat": msg["chat"],
                    "question_id": parent_msg["id"],
                    "question_author": parent_msg["author"],
                    "question": parent_text,
                    "answer_id": msg["id"],
                    "answer_author": msg["author"],
                    "answer": text
                })
        
        # 2. Long instructional / informative single messages
        if len(text) > 100 and is_technical_text(text):
            if any(w in text.lower() for w in ["qo'llanma", "diqqat", "yo'riqnoma", "tartibi", "bo'yicha", "qiling", "tekshiring", "kerak"]):
                announcements.append({
                    "chat": msg["chat"],
                    "author": msg["author"],
                    "text": text
                })

    print(f"Extracted valid Q&A pairs: {len(qa_pairs):,}")
    print(f"Extracted standalone technical guides: {len(announcements):,}")

    # Save to a structured JSON file for LLM knowledge synthesis
    out_file = r"c:\Users\naimi\Desktop\for cv\uniai\scratch\extracted_raw_qa.json"
    with open(out_file, "w", encoding="utf-8") as out:
        json.dump({
            "qa_pairs": qa_pairs[:500], # Top high quality pairs
            "announcements": announcements[:200]
        }, out, ensure_ascii=False, indent=2)

    print(f"Saved extracted data to {out_file}")

if __name__ == "__main__":
    analyze_and_extract_qa()
