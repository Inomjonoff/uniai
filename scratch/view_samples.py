import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"c:\Users\naimi\Desktop\for cv\uniai\scratch\extracted_raw_qa.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total QA pairs loaded: {len(data['qa_pairs'])}")
print(f"Total announcements: {len(data['announcements'])}")

for i, qa in enumerate(data["qa_pairs"][:8], 1):
    q = qa["question"].replace("\n", " ")[:120]
    a = qa["answer"].replace("\n", " ")[:140]
    print(f"\n--- Sample {i} [{qa['chat']}] ---")
    print(f"Savol ({qa['question_author']}): {q}")
    print(f"Javob ({qa['answer_author']}): {a}")
