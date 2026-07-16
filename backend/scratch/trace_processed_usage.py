import os
import sys

root_dir = r"c:\108\AI-accounting-0.03"
backend_dir = os.path.join(root_dir, 'backend')
frontend_dir = os.path.join(root_dir, 'frontend', 'src')

import sys
sys.stdout.reconfigure(encoding='utf-8')

results = []

def search_files(directory, extensions):
    for root, dirs, files in os.walk(directory):
        if 'venv' in root or '.git' in root or '__pycache__' in root or 'node_modules' in root:
            continue
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for idx, line in enumerate(f, 1):
                            if 'processed' in line:
                                results.append({
                                    'file': os.path.relpath(filepath, root_dir),
                                    'line': idx,
                                    'content': line.strip()
                                })
                except Exception as e:
                    pass

search_files(backend_dir, ['.py'])
search_files(frontend_dir, ['.ts', '.tsx'])

print(f"Total occurrences of 'processed': {len(results)}")
# Write to a file for easy reading
out_path = os.path.join(backend_dir, 'scratch', 'processed_occurrences.txt')
with open(out_path, 'w', encoding='utf-8') as f:
    for r in results:
        f.write(f"File: {r['file']} | Line: {r['line']} | Content: {r['content']}\n")

# Print first 50 occurrences
for r in results[:50]:
    print(f"File: {r['file']} | Line: {r['line']} | Content: {r['content'][:120]}")
