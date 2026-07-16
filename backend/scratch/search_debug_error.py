import os

root_dir = r"c:\108\AI-accounting-0.03\backend"

for root, dirs, files in os.walk(root_dir):
    if 'venv' in root or '.git' in root or '__pycache__' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for idx, line in enumerate(f, 1):
                        if 'DEBUG:' in line:
                            print(f"{os.path.relpath(filepath, root_dir)}:{idx}: {line.strip()}")
            except Exception:
                pass
