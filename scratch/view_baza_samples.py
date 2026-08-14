import json
import random
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"c:\Users\naimi\Desktop\for cv\uniai\scratch\baza_knowledge.json", "r", encoding="utf-8") as f:
    items = json.load(f)

print(f"Total curated knowledge records: {len(items):,}")
random.seed(42)
sample = random.sample(items, 6)

for i, it in enumerate(sample, 1):
    print(f"\n=== [{i}] {it['title']} ===")
    print(f"Tizim: {it['system_name']} | Kategoriya: {it['category']}")
    print(f"Muammo: {it['problem']}")
    print(f"Yechim: {it['solution']}")
