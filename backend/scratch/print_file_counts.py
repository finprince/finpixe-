import json
import os

root_dir = r"c:\108\AI-accounting-0.03"
results_file = os.path.join(root_dir, 'backend', 'scratch', 'grep_results.json')

with open(results_file, 'r') as f:
    matches = json.load(f)

# Find all unique files that matched and their counts
file_counts = {}
for m in matches:
    fpath = m['file'].replace('\\', '/')
    file_counts[fpath] = file_counts.get(fpath, 0) + 1

sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
print("Files with most matches in raw results:")
for f, c in sorted_files[:30]:
    print(f"  {f}: {c}")
