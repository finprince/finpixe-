import os
import sys

root_dir = r"c:\108\AI-accounting-0.03"
filepath = os.path.join(root_dir, 'backend', 'ocr_pipeline', 'models.py')

with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print(f"Total lines in models.py: {len(lines)}")

# Find InvoiceTempOCR class and print its fields definitions
in_class = False
for idx, line in enumerate(lines, 1):
    if 'class InvoiceTempOCR' in line:
        in_class = True
        print(f"Line {idx}: {line.strip()}")
    elif in_class and line.startswith('class '):
        in_class = False
    
    if in_class:
        if 'models.' in line or 'status' in line or 'processed' in line:
            print(f"  Line {idx}: {line.strip()}")
