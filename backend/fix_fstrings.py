# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

"""
Fix Python 3.11 f-string quote mismatch errors across the backend.

In Python 3.11, you cannot reuse the same quote character inside an f-string expression.
e.g., f"hello {d['key']}" is invalid. Must be f"hello {d['key']}" instead.

This script finds all f'...' strings that contain a ' inside {}, and rewrites them
as f"..." strings. It skips lines where the f-string already uses double quotes
or would introduce double-quote conflicts.
"""

import os
import re

SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'migrations'}


def needs_fix(line):
    """Return True if the line contains an f'...' with a quote conflict inside {}."""
    # Quick pre-check
    if "f'" not in line:
        return False
    # Look for f"...{...'...}..." patterns
    # The inner ' breaks the f-string on Python 3.11
    # We check if there's a single quote inside braces within an f-string
    i = 0
    while i < len(line):
        if line[i:i+2] == "f'":
            # Find the content of this f-string
            start = i + 2
            depth = 0
            j = start
            has_inner_quote = False
            while j < len(line):
                c = line[j]
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                elif c == "'" and depth > 0:
                    has_inner_quote = True
                elif c == "'" and depth == 0:
                    # End of f-string
                    if has_inner_quote:
                        return True
                    break
                j += 1
        i += 1
    return False


def fix_line(line):
    """
    Replace f'...' with f"..." when there's a quote conflict.
    Only acts on f-strings that use single quotes as the outer delimiter
    and contain single quotes inside {} expressions.
    Skips if the inner content contains double quotes (would create a new conflict).
    """
    result = []
    i = 0
    while i < len(line):
        if line[i:i+2] == "f'":
            # Find the full extent of this f-string
            start = i + 2
            depth = 0
            j = start
            has_inner_quote = False
            inner_has_double_quote = False
            end = None
            while j < len(line):
                c = line[j]
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                elif c == "'" and depth > 0:
                    has_inner_quote = True
                elif c == '"' and depth > 0:
                    inner_has_double_quote = True
                elif c == "'" and depth == 0:
                    end = j
                    break
                j += 1

            if has_inner_quote and not inner_has_double_quote and end is not None:
                # Safe to swap: change outer quotes from ' to "
                inner_content = line[start:end]
                result.append('f"')
                result.append(inner_content)
                result.append('"')
                i = end + 1
                continue
        result.append(line[i])
        i += 1
    return ''.join(result)


def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original = f.read()
    except Exception as e:
        print(f"  [SKIP] Cannot read {filepath}: {e}")
        return 0

    lines = original.splitlines(keepends=True)
    new_lines = []
    changes = 0
    for lineno, line in enumerate(lines, 1):
        if needs_fix(line):
            fixed = fix_line(line)
            if fixed != line:
                print(f"  Line {lineno}: {line.rstrip()}")
                print(f"        -> {fixed.rstrip()}")
                new_lines.append(fixed)
                changes += 1
                continue
        new_lines.append(line)

    if changes > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(''.join(new_lines))
        print(f"  => Fixed {changes} line(s) in {filepath}\n")
    return changes


def main(root):
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip dirs
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if not fname.endswith('.py'):
                continue
            fpath = os.path.join(dirpath, fname)
            count = fix_file(fpath)
            total += count

    print(f"\n=== Done. Fixed {total} line(s) total. ===")


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    main(root)
