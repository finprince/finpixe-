import os
import sys

root_dir = r"c:\108\AI-accounting-0.03"
filepath = os.path.join(root_dir, 'backend', 'ocr_pipeline', 'views.py')

with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

import sys
sys.stdout.reconfigure(encoding='utf-8')

in_class = False
for idx, line in enumerate(lines, 1):
    if 'class CleanOCRStagingView' in line:
        in_class = True
    elif in_class and line.startswith('class '):
        in_class = False
    
    if in_class and ('def get' in line or 'def post' in line or 'def patch' in line or 'def delete' in line):
        print(f"Line {idx}: {line.strip()}")
