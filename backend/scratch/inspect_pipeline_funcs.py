import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

import inspect
import ocr_pipeline.pipeline as pipeline_mod

funcs = [f for f in dir(pipeline_mod) if inspect.isfunction(getattr(pipeline_mod, f))]
print("Functions in pipeline.py:", funcs)

if hasattr(pipeline_mod, 'run_ocr_pipeline'):
    lines, start = inspect.getsourcelines(pipeline_mod.run_ocr_pipeline)
    print(f"\nrun_ocr_pipeline starts at line {start}, length {len(lines)}")
    print("First 40 lines of run_ocr_pipeline:")
    for l in lines[:40]:
        print(l, end='')
