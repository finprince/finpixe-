import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

targets = [
    'ocr_pipeline/extraction.py',
    'ocr_pipeline/normalize.py',
    'ocr_pipeline/canonicalizer.py',
    'ocr_pipeline/pipeline.py',
    'ocr_pipeline/models.py',
    'ocr_pipeline/integrity_enforcer.py',
    'ocr_pipeline/forensic_merger.py',
    'ocr_pipeline/schema.py',
    'ocr_pipeline/views.py',
    'pending_purchases/views.py',
    'pending_purchases/serializers.py',
    'pending_purchases/models.py',
]

keywords = [
    'discount_percent',
    'discount_pct',
    'discount_percentage',
    'disc_percent',
    'disc_pct',
    'discount_amount',
    'discount_value',
    'discount',
    'disc',
]

for path in targets:
    hits = []
    try:
        if not os.path.exists(path):
            print(f'\n=== {path} === FILE NOT FOUND')
            continue
        lines = open(path, encoding='utf-8').readlines()
        for i, line in enumerate(lines, 1):
            low = line.lower()
            if any(k in low for k in keywords):
                hits.append((i, line.rstrip()))
    except Exception as e:
        hits = [(0, f'ERROR: {e}')]
    if hits:
        print(f'\n=== {path} ({len(hits)} hits) ===')
        for lno, l in hits[:40]:  # cap at 40 per file
            print(f'  {lno}: {l}')
        if len(hits) > 40:
            print(f'  ... ({len(hits) - 40} more lines not shown)')
    else:
        print(f'\n=== {path} === ** NO DISCOUNT MENTIONS **')
