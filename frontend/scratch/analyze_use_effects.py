import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
content = open('src/pages/Vouchers/Vouchers.tsx', encoding='utf-8').read()

matches = re.finditer(r'useEffect\(\(\)\s*=>\s*\{', content)
print("=" * 80)
print("useEffect blocks referencing purchaseItems or setPurchaseItems")
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
                # read dependencies after the closing brace, e.g. , [dep1, dep2])
                end_pos = i + 1
                # scan up to next 100 chars to find the closing paren/dep array
                suffix = content[end_pos:end_pos+100]
                dep_match = re.search(r'\s*,\s*\[([^\]]*)\]\s*\)', suffix)
                dep_str = dep_match.group(0) if dep_match else ""
                end_pos += len(dep_str)
                break
            else:
                brace_count -= 1
    block = content[start_pos:end_pos]
    if 'purchaseItems' in block or 'setPurchaseItems' in block:
        line_num = content[:start_pos].count('\n') + 1
        block_lines = block.split('\n')
        print(f"Line {line_num}:")
        print(f"  Start: {block_lines[0]}")
        if len(block_lines) > 1:
            print(f"  First: {block_lines[1][:100]}")
        print(f"  Deps: {block_lines[-1] if block_lines else ''}")
        print("-" * 40)
