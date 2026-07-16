import os

filepath = r"c:\108\AI-accounting-0.03\frontend\src\pages\Vouchers\Vouchers.tsx"

with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print(f"Total lines in Vouchers.tsx: {len(lines)}")

# Search for any functions declared in VouchersPage starting with const or function
for idx, line in enumerate(lines, 1):
    if line.strip().startswith('const fetch') or line.strip().startswith('function fetch'):
        print(f"Line {idx}: {line.strip()}")
    elif 'fetch' in line and '(' in line and 'const ' in line:
        if idx > 89 and idx < 1000:
            print(f"Line {idx}: {line.strip()}")
