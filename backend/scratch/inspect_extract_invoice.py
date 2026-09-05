import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

import inspect
import ocr_pipeline.pipeline as pipeline_mod

lines, start = inspect.getsourcelines(pipeline_mod.extract_invoice)
print(f"extract_invoice starts at line {start}, length {len(lines)}")
for i, l in enumerate(lines[:100]):
    # encode safely
    safe_l = l.encode('ascii', 'replace').decode('ascii')
    print(f"{i+start}: {safe_l}", end='')
