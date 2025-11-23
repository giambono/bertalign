import sys
from bertalign.utils import load_jsonl

jsonl_path = sys.argv[1]
data = load_jsonl(jsonl_path)

# Check structure
src_data = [r for r in data if r["language"] == "en" and r["part"] == "001"]
tgt_data = [r for r in data if r["language"] == "it" and r["part"] == "001"]

print(f"English: {len(src_data)} chunks")
print(f"Italian: {len(tgt_data)} chunks")
print()

# Check page distribution
from collections import Counter
src_pages = Counter(r["page"] for r in src_data)
tgt_pages = Counter(r["page"] for r in tgt_data)

print(f"English pages: {sorted(src_pages.keys())[:10]}... (total: {len(src_pages)})")
print(f"Italian pages: {sorted(tgt_pages.keys())[:10]}... (total: {len(tgt_pages)})")
print()

# Show first 5 from each
print("First 5 English chunks:")
for i, r in enumerate(src_data[:5]):
    print(f"  [{i}] page={r['page']}, chunk_id={r['chunk_id']}: {r['text'][:80]}...")
print()

print("First 5 Italian chunks:")
for i, r in enumerate(tgt_data[:5]):
    print(f"  [{i}] page={r['page']}, chunk_id={r['chunk_id']}: {r['text'][:80]}...")
print()

# Check if there's alignment by page
print("Checking page-by-page alignment:")
for page in ["002", "003", "004"]:
    src_page = [r["text"] for r in src_data if r["page"] == page]
    tgt_page = [r["text"] for r in tgt_data if r["page"] == page]
    print(f"  Page {page}: EN={len(src_page)} chunks, IT={len(tgt_page)} chunks")