import os

filepath = r"c:\108\AI-accounting-0.03\frontend\src\pages\Vouchers\Vouchers.tsx"

with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print(f"Total lines in Vouchers.tsx: {len(lines)}")

# Search for matches containing "scan" case-insensitive
results = []
for idx, line in enumerate(lines, 1):
    if 'scan' in line.lower():
        results.append((idx, line.strip()))

print(f"Found {len(results)} occurrences containing 'scan'.")
for idx, content in results[:30]:
    print(f"Line {idx}: {content[:120]}")
