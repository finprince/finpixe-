import os

root_dir = r"c:\108\AI-accounting-0.03"
filepath = os.path.join(root_dir, 'frontend', 'src', 'components', 'SmartInvoiceUploadModal.tsx')

with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Search for api calls or finalize triggers
terms = ['api/ocr-staging', 'finalize', 'save', 'submit', 'post', 'auto_save']
import sys
sys.stdout.reconfigure(encoding='utf-8')

for idx, line in enumerate(lines, 1):
    for term in terms:
        if term in line.lower():
            # print first few matches
            print(f"Line {idx}: {line.strip()[:120]}")
            break

