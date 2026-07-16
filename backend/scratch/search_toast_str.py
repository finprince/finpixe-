import json
import os

root_dir = r"c:\108\AI-accounting-0.03"
results_file = os.path.join(root_dir, 'backend', 'scratch', 'grep_results.json')

with open(results_file, 'r') as f:
    matches = json.load(f)

# Find matches containing "already saved" or similar
for m in matches:
    content = m['content'].lower()
    if 'already saved' in content or 'duplicates skipped' in content or 'all invoices were' in content:
        print(f"File: {m['file']} Line: {m['line']} Content: {m['content']}")
