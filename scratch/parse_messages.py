import os
import glob
import re
from html import unescape
from html.parser import HTMLParser

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


def parse_all_chats():
    baza_dir = r"c:\Users\naimi\Desktop\for cv\uniai\baza"
    html_files = sorted(set(
        glob.glob(os.path.join(baza_dir, "*.html")) +
        glob.glob(os.path.join(baza_dir, "**", "*.html"), recursive=True)
    ))

    all_parsed_by_chat = {}

    for f in html_files:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                raw_html = fp.read()
                m = re.search(r'<div class="text bold">\s*([^<]+)\s*</div>', raw_html[:4000])
                chat_title = unescape(m.group(1).strip()) if m else "Unknown"
                
                parser = TelegramHTMLParser()
                parser.feed(raw_html)
                
                if chat_title not in all_parsed_by_chat:
                    all_parsed_by_chat[chat_title] = []
                all_parsed_by_chat[chat_title].extend(parser.messages)
        except Exception as e:
            print(f"Error parsing {f}: {e}")

    for title, msgs in all_parsed_by_chat.items():
        print(f"Chat '{title}': Total text messages extracted: {len(msgs):,}")
        # Print a couple samples
        print("--- Sample messages ---")
        sample_count = 0
        for m in msgs:
            if len(m['text']) > 40:
                print(f"[{m['author']}]: {m['text'][:120]}...")
                sample_count += 1
                if sample_count >= 3:
                    break
        print("========================================")

if __name__ == "__main__":
    parse_all_chats()
