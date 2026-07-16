import json
import os
import re

root_dir = r"c:\108\AI-accounting-0.03"
results_file = os.path.join(root_dir, 'backend', 'scratch', 'grep_results.json')

with open(results_file, 'r') as f:
    matches = json.load(f)

print(f"Loaded {len(matches)} raw matches.")

# Filter and analyze
filtered = []
for m in matches:
    fpath = m['file']
    # Skip migrations, scratch files, and json dumps, or test files
    if 'migrations' in fpath or 'scratch' in fpath or 'test_' in fpath or fpath.endswith('.json') or fpath.endswith('.txt') or 'venv' in fpath:
        continue
    filtered.append(m)

print(f"Filtered down to {len(filtered)} matches in main code.")

# Group by file and line to get a good sense
by_file_line = {}
for m in filtered:
    key = (m['file'], m['line'])
    if key not in by_file_line:
        by_file_line[key] = []
    by_file_line[key].append(m['term'])

print(f"Unique lines: {len(by_file_line)}")

# Let's inspect some of the key files:
# 1. normalize.py
# 2. pipeline.py
# 3. inventory_validation.py
# 4. views.py
# 5. zoho_adapter.py
# 6. models.py (vouchers and accounting)

important_files = [
    'backend/ocr_pipeline/normalize.py',
    'backend/ocr_pipeline/pipeline.py',
    'backend/ocr_pipeline/inventory_validation.py',
    'backend/ocr_pipeline/views.py',
    'backend/ocr_pipeline/zoho_adapter.py',
    'backend/ocr_pipeline/models.py',
    'backend/pending_purchases/views.py',
    'frontend/src/pages/PendingPurchases/PendingPurchases.tsx',
    'frontend/src/components/GstCorrectionModal.tsx',
]

print("\nKey matches in critical files:")
for f in important_files:
    f_matches = [m for m in filtered if m['file'].replace('\\', '/') == f]
    print(f"  {f}: {len(f_matches)} matches")

# Let's write a python parser to extract function names using basic AST or regex for python, and display them.
def get_func_name_python(filepath, line_num):
    abs_path = os.path.join(root_dir, filepath)
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except:
        return "Unknown"
    
    # scan backwards from line_num to find the containing function
    for idx in range(line_num - 1, -1, -1):
        line = lines[idx]
        if line.startswith('def '):
            m = re.match(r'def\s+(\w+)', line.strip())
            if m:
                return m.group(1)
        elif line.startswith('class '):
            m = re.match(r'class\s+(\w+)', line.strip())
            if m:
                return f"Class {m.group(1)}"
    return "Global"

def get_func_name_ts(filepath, line_num):
    abs_path = os.path.join(root_dir, filepath)
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except:
        return "Unknown"
    
    # scan backwards from line_num to find the containing function
    for idx in range(line_num - 1, -1, -1):
        line = lines[idx]
        if 'const ' in line or 'function ' in line:
            m = re.search(r'(?:const|function)\s+(\w+)', line)
            if m:
                return m.group(1)
        elif 'class ' in line:
            m = re.search(r'class\s+(\w+)', line)
            if m:
                return m.group(1)
    return "Global"

final_report = []
for f in important_files:
    f_matches = [m for m in filtered if m['file'].replace('\\', '/') == f]
    # Deduplicate by line number
    seen_lines = set()
    for m in f_matches:
        if m['line'] in seen_lines:
            continue
        seen_lines.add(m['line'])
        
        filepath = m['file']
        line_num = m['line']
        if filepath.endswith('.py'):
            func = get_func_name_python(filepath, line_num)
        else:
            func = get_func_name_ts(filepath, line_num)
            
        content = m['content']
        
        # Classify Read/Write and Purpose
        read_or_write = "Read"
        purpose = "Query / Validation"
        if '=' in content:
            parts = content.split('=', 1)
            if m['term'] in parts[0]:
                read_or_write = "Write"
                purpose = "Initialization / Mutation"
        if 'get(' in content or 'getattr(' in content:
            read_or_write = "Read"
            purpose = "Data Retrieval"
            
        final_report.append({
            'file': filepath,
            'line': line_num,
            'function': func,
            'term': m['term'],
            'read_write': read_or_write,
            'purpose': purpose,
            'snippet': content
        })

print(f"\nAnalyzed {len(final_report)} unique lines in critical files.")
with open(os.path.join(root_dir, 'backend', 'scratch', 'analyzed_grep_results.json'), 'w') as out:
    json.dump(final_report, out, indent=2)
print("Saved analyzed results to backend/scratch/analyzed_grep_results.json")
