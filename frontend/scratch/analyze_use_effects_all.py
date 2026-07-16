import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
content = open('src/pages/Vouchers/Vouchers.tsx', encoding='utf-8').read()

# Pattern to find all useEffects
matches = re.finditer(r'useEffect\(\s*\(\s*\)\s*=>\s*\{', content)
print("=" * 80)
print("All useEffect blocks with their dependency arrays")
print("=" * 80)

for m in matches:
    start_pos = m.start()
    brace_count = 0
    end_pos = start_pos
    for i in range(start_pos + 9, len(content)):
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            if brace_count == 0:
                end_pos = i + 1
                break
            else:
                brace_count -= 1
                
    # Now scan forward from end_pos to find the dependency array
    suffix = content[end_pos:end_pos+200]
    dep_match = re.search(r'\s*,\s*\[([^\]]*)\]\s*\)', suffix, re.DOTALL)
    
    line_num = content[:start_pos].count('\n') + 1
    dep_str = dep_match.group(1).replace('\n', ' ').strip() if dep_match else "NONE"
    
    # Check if party, vendorId, isInterState, or purchaseItems is in block or deps
    block = content[start_pos:end_pos]
    if any(k in block or k in dep_str for k in ['party', 'vendorId', 'isInterState', 'purchaseItems']):
        print(f"Line {line_num}:")
        print(f"  Deps: {dep_str}")
        print(f"  Snippet: {content[start_pos:start_pos+120].strip()}")
        print("-" * 40)
