import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

import inspect
import ocr_pipeline.pipeline as pipeline_mod

lines, start = inspect.getsourcelines(pipeline_mod.run_ocr_pipeline)
for i, l in enumerate(lines[35:120], start=35):
    print(f"{i+start}: {l}", end='')
