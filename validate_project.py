#!/usr/bin/env python3
"""Validate project files without hardcoding Unicode paths."""
import glob
import json
import sys
import os
def validate_json(filepath):
    """Validate JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        return True
    except Exception as e:
        print(f"Invalid JSON {filepath}: {e}")
        return False
def find_dirs(base, prefix):
    """Find directories starting with prefix."""
    pattern = os.path.join(base, f'{prefix}*')
    dirs = glob.glob(pattern)
    return [d for d in dirs if os.path.isdir(d)]
def list_files_in_dir(directory):
    """List all files in a directory recursively."""
    files = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            rel_root = os.path.relpath(root, os.path.dirname(directory))
            if rel_root == '.':
                files.append(f)
            else:
                files.append(os.path.join(rel_root, f))
    return files
def find_file_in_dirs(dirs, filename):
    """Find file in list of directories."""
    for d in dirs:
        filepath = os.path.join(d, filename)
        if os.path.isfile(filepath):
            return filepath
    return None
def main():
    base = os.getcwd()
    print(f"Base directory: {base}")
    
    # Find directories by numeric prefix
    dirs_03 = find_dirs(base, '03-')
    dirs_04 = find_dirs(base, '04-')
    dirs_05 = find_dirs(base, '05-')
    dirs_06 = find_dirs(base, '06-')
    
    print(f"03- dirs: {dirs_03}")
    print(f"04- dirs: {dirs_04}")
    print(f"05- dirs: {dirs_05}")
    print(f"06- dirs: {dirs_06}")
    
    # List ALL files in 05- and 06- directories for debugging
    if dirs_05:
        print(f"\nFiles in 05- directory:")
        for f in list_files_in_dir(dirs_05[0]):
            print(f"  {f}")
    
    if dirs_06:
        print(f"\nFiles in 06- directory:")
        for f in list_files_in_dir(dirs_06[0]):
            print(f"  {f}")
    
    # Find files
    dirs_03 = find_dirs(base, '03-')
    dirs_04 = find_dirs(base, '04-')
    dirs_05 = find_dirs(base, '05-')
    dirs_06 = find_dirs(base, '06-')
    
    schedule = find_file_in_dirs(dirs_03, 'schedule.json')
    readiness = find_file_in_dirs(dirs_04, 'readiness.json')
    current_state = find_file_in_dirs(dirs_05, 'current-state-mt5.json')
    readiness_check = find_file_in_dirs(dirs_06, 'mt5_readiness_check.py')
    
    all_ok = True
    for name, filepath in [
        ('schedule', schedule),
        ('readiness', readiness),
        ('current_state', current_state),
        ('readiness_check', readiness_check),
    ]:
        if filepath:
            print(f"FOUND: {name} -> {filepath}")
            if name != 'readiness_check':
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        json.load(f)
                except Exception as e:
                    print(f"Invalid JSON {filepath}: {e}")
                    all_ok = False
        else:
            print(f"NOT FOUND: {name}")
            all_ok = False
    
    if all_ok:
        print("All project files validated successfully")
        sys.exit(0)
    else:
        print("Validation failed")
        sys.exit(1)
def find_dirs(base, prefix):
    """Find directories starting with prefix."""
    pattern = os.path.join(base, f'{prefix}*')
    dirs = glob.glob(pattern)
    return [d for d in dirs if os.path.isdir(d)]
def find_file_in_dirs(dirs, filename):
    """Find file in list of directories."""
    for d in dirs:
        filepath = os.path.join(d, filename)
        if os.path.isfile(filepath):
            return filepath
    return None
if __name__ == '__main__':
    import glob
    import json
    import sys
    import os
    main()
