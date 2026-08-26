import os
import glob
import re

css_files = glob.glob('apps/web/src/**/*.module.css', recursive=True)

bg_pattern = re.compile(r'(background|background-color)\s*:\s*var\(--color-white\)\s*;')
border_pattern = re.compile(r'border-color\s*:\s*var\(--color-white\)\s*;')

changed_files = 0
for file in css_files:
    with open(file, 'r') as f:
        content = f.read()
    
    new_content = bg_pattern.sub(r'\1: var(--color-surface);', content)
    new_content = border_pattern.sub(r'border-color: var(--color-border);', new_content)
    
    if new_content != content:
        with open(file, 'w') as f:
            f.write(new_content)
        changed_files += 1

print(f"Changed {changed_files} files.")
