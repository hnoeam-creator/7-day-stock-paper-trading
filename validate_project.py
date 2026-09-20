#!/usr/bin/env python3
"""Validate project files without hardcoding Unicode paths."""
import glob
import json
import sys
import os
def find_file(pattern):
    """Find first file matching pattern."""
    matches = glob.glob(pattern)
    if not matches:
        return None
    return matches[0]
def validate_json(filepath):
    """Validate JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        return True
    except Exception as e:
        print(f"Invalid JSON {filepath}: {e}")
        return False
def main():
    base = os.getcwd()
    
    # Find directories by numeric prefix
    dirs = {
        'schedule': glob.glob(os.path.join(base, '03-*', 'schedule.json')),
        'readiness': glob.glob(os.path.join(base, '04-*', 'readiness.json')),
        'current_state': glob.glob(os.path.join(base, '05-*', 'current-state-mt5.json')),
        'readiness_check': glob.glob(os.path.join(base, '06-*', 'mt5_readiness_check.py')),
    }
    
    all_ok = True
    for name, files in dirs.items():
        if not files:
            print(f"NOT FOUND: {name}")
            all_ok = False
        else:
            filepath = files[0]
            print(f"FOUND: {name} -> {filepath}")
            if name != 'readiness_check':
                if not validate_json(filepath):
                    all_ok = False
    
    if all_ok:
        print("All project files validated successfully")
        sys.exit(0)
    else:
        print("Validation failed")
        sys.exit(1)
if __name__ == '__main__':
    main()
