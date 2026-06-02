import os
import re

def replace_in_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return False  # Skip binary files or unreadable files

    new_content = content
    # Case-sensitive replacements to preserve casing
    new_content = new_content.replace('ArcWarden', 'Sigui')
    new_content = new_content.replace('arcwarden', 'sigui')
    new_content = new_content.replace('ARCWARDEN', 'SIGUI')

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    exclude_dirs = {'.git', 'node_modules', 'venv', '.venv', '__pycache__', '.next', 'db'}

    count = 0
    for root, dirs, files in os.walk(script_dir):
        # Modify dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            # Skip this script
            if file == 'rename.py':
                continue
            
            filepath = os.path.join(root, file)
            if replace_in_file(filepath):
                count += 1
                print(f"Updated: {filepath}")

    print(f"Total files updated: {count}")

if __name__ == '__main__':
    main()
