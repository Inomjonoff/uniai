import os
import glob
import re
from html import unescape

baza_dir = r"c:\Users\naimi\Desktop\for cv\uniai\baza"
html_files = sorted(set(
    glob.glob(os.path.join(baza_dir, "*.html")) +
    glob.glob(os.path.join(baza_dir, "**", "*.html"), recursive=True)
))

print(f"Total HTML files found: {len(html_files)}")

chats = {}
for f in html_files:
    try:
        with open(f, "r", encoding="utf-8", errors="ignore") as fp:
            content = fp.read(4000)
            m = re.search(r'<div class="text bold">\s*([^<]+)\s*</div>', content)
            title = unescape(m.group(1).strip()) if m else "Unknown"
            chats[title] = chats.get(title, 0) + 1
    except Exception as e:
        print(f"Error reading {f}: {e}")

for title, count in chats.items():
    print(f"Group/Chat: {title} -> {count} HTML files")
