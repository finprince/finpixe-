import os

filepath = r"c:\108\AI-accounting-0.03\backend\ocr_pipeline\views.py"

with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
for idx, line in enumerate(lines, 1):
    if 'django' in line.lower():
        print(f"Line {idx}: {line.strip()}")
