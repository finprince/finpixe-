import os

filepath = r"c:\108\AI-accounting-0.03\frontend\src\pages\Vouchers\Vouchers.tsx"

with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print(f"Total lines in Vouchers.tsx: {len(lines)}")

# Search for what components/tabs are rendered in Vouchers.tsx
for idx, line in enumerate(lines, 1):
    if idx > 12500:
        if '<' in line and ('Voucher' in line or 'Scanner' in line or 'Upload' in line or 'Tab' in line):
            print(f"Line {idx}: {line.strip()}")
