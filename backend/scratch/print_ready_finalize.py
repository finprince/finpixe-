import os
import sys

root_dir = r"c:\108\AI-accounting-0.03"
filepath = os.path.join(root_dir, 'frontend', 'src', 'components', 'SmartInvoiceUploadModal.tsx')

with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

import sys
sys.stdout.reconfigure(encoding='utf-8')

for idx, line in enumerate(lines, 1):
    if 'readyToFinalize' in line:
        print(f"Line {idx}: {line.strip()[:150]}")
