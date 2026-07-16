with open('../frontend/src/components/SmartInvoiceUploadModal.tsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== SEARCH RESULTS ===")
for i, line in enumerate(lines):
    if 'setStep' in line or 'step' in line:
        if 'console' not in line:
            print(f"Line {i+1}: {line.strip().encode('ascii', 'replace').decode('ascii')}")
