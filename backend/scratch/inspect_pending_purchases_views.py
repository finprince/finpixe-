import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

filepath = r"c:\108\AI-accounting-0.03\backend\pending_purchases\views.py"

with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print(f"Total lines in pending_purchases/views.py: {len(lines)}")

# Find resolve or finalize_all methods and print their body
in_func = False
func_lines = []
for idx, line in enumerate(lines, 1):
    if 'def resolve' in line or 'def finalize_all' in line:
        in_func = True
        func_lines.append(f"Line {idx}: {line.strip()}")
    elif in_func and line.startswith('    def '):
        in_func = False
    
    if in_func:
        func_lines.append(f"  Line {idx}: {line.strip()}")

for fl in func_lines[:100]:
    print(fl)
