import os
import sys
import re

KEYWORDS = ['gst_rate', 'cgst_rate', 'sgst_rate', 'igst_rate', 'combined_rate', 'tax_rate', 'effective_rate']
exclude_dirs = ['venv', '.git', '__pycache__', 'scratch', 'node_modules']

def find_keywords_in_file(filepath):
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        return results

    current_func = "Module Level"
    func_pattern = re.compile(r'^\s*def\s+(\w+)\s*\(|^\s*class\s+(\w+)')

    for idx, line in enumerate(lines, 1):
        # Track function/class scope
        func_match = func_pattern.match(line)
        if func_match:
            current_func = func_match.group(1) or func_match.group(2)

        # Check if line contains keyword
        for kw in KEYWORDS:
            # We want to match whole words for keyword, e.g. not "success_rate" unless it's in the list
            if re.search(r'\b' + kw + r'\b', line):
                # Classify as Assignment (write) vs Read
                is_assignment = False
                # Simple check if keyword is on LHS of assignment
                # Match: keyword = ... or keyword: type = ... or item['keyword'] = ...
                assignment_patterns = [
                    r'\b' + kw + r'\s*=[^=]',
                    r'\b' + kw + r'\s*:[^=]+=[^=]',
                    r'\[\s*[\'"]' + kw + r'[\'"]\s*\]\s*=[^=]'
                ]
                for pat in assignment_patterns:
                    if re.search(pat, line):
                        is_assignment = True
                        break

                purpose = "Assignment (Write)" if is_assignment else "Access (Read)"
                
                # Context clues
                snippet = line.strip()
                
                results.append({
                    "file": os.path.relpath(filepath, start=os.getcwd()),
                    "function": current_func,
                    "line": idx,
                    "keyword": kw,
                    "purpose": purpose,
                    "snippet": snippet
                })
    return results

def main():
    all_results = []
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Also look at frontend for completeness, but request is "Repository Investigation"
    for root, dirs, files in os.walk(root_dir):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith('.py') or file.endswith('.tsx') or file.endswith('.ts'):
                filepath = os.path.join(root, file)
                all_results.extend(find_keywords_in_file(filepath))

    print(f"Total keyword occurrences found: {len(all_results)}")
    
    # Save the occurrences to a temporary json file
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'processed_occurrences.txt')
    with open(out_path, 'w', encoding='utf-8') as f:
        for r in all_results:
            f.write(f"File: {r['file']}\n")
            f.write(f"Function: {r['function']}\n")
            f.write(f"Line Number: {r['line']}\n")
            f.write(f"Snippet: {r['snippet']}\n")
            f.write(f"Purpose: {r['purpose']} of {r['keyword']}\n")
            f.write("-" * 80 + "\n")
            
    print(f"Occurrences compiled to {out_path}")

if __name__ == '__main__':
    main()
