import os

filepath = r"c:\108\AI-accounting-0.03\frontend\src\pages\Vouchers\Vouchers.tsx"

with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print(f"Total lines in Vouchers.tsx: {len(lines)}")

# Search for any occurrences of "purchase_scan" in Vouchers.tsx
for idx, line in enumerate(lines, 1):
    if 'purchase_scan' in line:
        print(f"Line {idx}: {line.strip()}")
