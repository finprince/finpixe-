import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

filepath = r"c:\108\AI-accounting-0.03\backend\scratch\processed_occurrences.txt"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

blocks = content.split("-" * 80 + "\n")

filtered_results = []
for b in blocks:
    if not b.strip():
        continue
    lines = b.strip().split('\n')
    meta = {}
    for line in lines:
        if line.startswith('File: '):
            meta['file'] = line[len('File: '):].strip()
        elif line.startswith('Function: '):
            meta['function'] = line[len('Function: '):].strip()
        elif line.startswith('Line Number: '):
            meta['line'] = line[len('Line Number: '):].strip()
        elif line.startswith('Snippet: '):
            meta['snippet'] = line[len('Snippet: '):].strip()
        elif line.startswith('Purpose: '):
            meta['purpose'] = line[len('Purpose: '):].strip()

    if not meta.get('file'):
        continue

    # Exclude scripts, tests, validation tools
    fpath = meta['file'].replace('\\', '/')
    if any(x in fpath for x in ['scratch/', 'sprint3_validation/', 'venv/', 'tests/', 'generate_reports', 'compare_ocr', 'forensic_e2e_validation']):
        continue
        
    filtered_results.append(meta)

print(f"Production matches: {len(filtered_results)}")
print("\n| File | Function | Line Number | Snippet | Purpose |")
print("|---|---|---|---|---|")
for r in filtered_results:
    print(f"| {r['file']} | {r['function']} | {r['line']} | `{r['snippet']}` | {r['purpose']} |")
