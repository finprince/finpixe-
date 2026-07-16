import os

filepath = r"c:\108\AI-accounting-0.03\frontend\src\pages\Vouchers\Vouchers.tsx"

with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print(f"Total lines in Vouchers.tsx: {len(lines)}")

# Search for api calls, queries, or fetching logic at the top levels
for idx, line in enumerate(lines, 1):
    if 'reload' in line.lower() or 'refresh' in line.lower():
        print(f"Line {idx}: {line.strip()}")
