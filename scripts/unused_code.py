
import os
import re
import sys

# Directories and files to exclude from search
EXCLUDE_DIRS = {'.git', '__pycache__', 'venv', 'migrations', 'node_modules', 'staticfiles', '.idea', '.vscode'}
EXCLUDE_FILES = {'manage.py'}

# Common methods in Django/DRF that are overridden but not explicitly called by user code
EXCLUDE_NAMES = {
    # Django Model/Form methods
    'clean', 'save', 'delete', 'get_absolute_url', '__str__',
    # DRF View methods
    'get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace',
    'get_queryset', 'get_serializer_class', 'perform_create', 'perform_update', 'perform_destroy',
    'get_object', 'filter_queryset', 'get_permissions', 'check_object_permissions',
    # Django View methods
    'dispatch', 'setup', 'get_context_data', 'form_valid', 'form_invalid',
    # Common test methods
    'setUp', 'tearDown', 'setUpTestData',
}

def get_definitions(root_dir):
    """
    Scans for function and class definitions in .py files.
    """
    definitions = []
    
    for root, dirs, files in os.walk(root_dir):
        # Filter directories inplace
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            if file in EXCLUDE_FILES:
                continue
            
            if not file.endswith('.py'):
                continue
            
            path = os.path.join(root, file)
            rel_path = os.path.relpath(path, root_dir)
            
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
            except Exception as e:
                print(f"Error reading {path}: {e}", file=sys.stderr)
                continue
                
            for i, line in enumerate(lines):
                # Python Function: async def or def
                # We need to capture the name
                match_func = re.search(r'^\s*(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', line)
                if match_func:
                    name = match_func.group(1)
                    if not name.startswith('__') and name not in EXCLUDE_NAMES:
                        definitions.append({'name': name, 'file': rel_path, 'line': i + 1, 'type': 'function'})
                        
                # Python Class
                match_class = re.search(r'^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[:\(]', line)
                if match_class:
                     name = match_class.group(1)
                     if not name.startswith('__'): # classes shouldn't start with __ usually
                        definitions.append({'name': name, 'file': rel_path, 'line': i + 1, 'type': 'class'})

    return definitions

def find_usages_count(root_dir, definitions):
    """
    Counts usages of each definition name across the entire codebase.
    Returns list of unused definitions (count <= 1).
    """
    all_content = []
    
    # Read all relevant file contents into memory once
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            if file in EXCLUDE_FILES:
                continue

            # extensions to search for usages in
            if not file.endswith(('.py', '.html', '.js', '.css', '.md', '.txt', '.json', '.xml', '.yaml', '.yml')):
                continue
                
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    all_content.append(f.read())
            except Exception as e:
                print(f"Error reading content of {path}: {e}", file=sys.stderr)

    full_text = "\n".join(all_content)
    
    unused = []
    for definition in definitions:
        name = definition['name']
        
        # Regex for whole word match
        # Escape name just in case
        pattern = re.compile(r'\b' + re.escape(name) + r'\b')
        
        # re.findall is expensive on huge text, but full_text here is manageable?
        # Let's count matches.
        # We expect at least 1 match (the definition itself).
        
        matches = pattern.findall(full_text)
        count = len(matches)
        
        if count <= 1:
            # Check edge case: maybe it's defined multiple times (e.g. overrides) but never called?
            # If defined twice and never called, count is 2.
            # But here we are iterating definitions.
            # If function `foo` is defined in A.py and B.py, we have 2 definitions.
            # total count in full_text will be >= 2.
            # So neither will be flagged as unused.
            # This is a limitation: unused overrides are not detected.
            # But the user asked for *unreferenced* functions.
            
            # If defined once and count is 1 -> unused.
            unused.append(definition)

    return unused

if __name__ == "__main__":
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = os.getcwd() # Default to current dir if not specified, or hardcode path
        
    root = "/home/kodex/Dev/dj-indoor-monitor" # force path for safety in this env

    print(f"Scanning {root} for unused code...", file=sys.stderr)
    
    defs = get_definitions(root)
    print(f"Found {len(defs)} definitions to check.", file=sys.stderr)
    
    unused_items = find_usages_count(root, defs)
    
    print(f"Found {len(unused_items)} potentially unused items:")
    for item in unused_items:
        print(f"[{item['type']}] {item['name']} ({item['file']}:{item['line']})")
