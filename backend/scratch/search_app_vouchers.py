import os

filepath = r"c:\108\AI-accounting-0.03\frontend\src\app\App.tsx"

with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print(f"Total lines in App.tsx: {len(lines)}")

# Search for vouchers state and fetch function
for idx, line in enumerate(lines, 1):
    if 'vouchers' in line and ('const ' in line or 'function ' in line or 'setVouchers' in line or 'fetch' in line):
        print(f"Line {idx}: {line.strip()}")
