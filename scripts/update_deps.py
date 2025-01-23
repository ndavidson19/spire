#!/usr/bin/env python3
import json
import tomlkit
from pathlib import Path

def load_current_deps():
    """Load dependencies from pip list JSON output"""
    with open('current_deps.json', 'r') as f:
        deps = json.load(f)
    return {pkg['name']: pkg['version'] for pkg in deps}

def update_pyproject(deps):
    """Update pyproject.toml with current dependencies"""
    pyproject_path = Path('pyproject.toml')
    
    with open(pyproject_path, 'r') as f:
        pyproject = tomlkit.parse(f.read())
    
    # Create dependencies section if it doesn't exist
    if 'project' not in pyproject:
        pyproject['project'] = {}
    if 'dependencies' not in pyproject['project']:
        pyproject['project']['dependencies'] = []
    
    # Update dependencies
    current_deps = []
    for name, version in deps.items():
        # Skip Python itself and pip
        if name.lower() in ('python', 'pip'):
            continue
        # Format the dependency string
        dep_str = f"{name}>={version}"
        current_deps.append(dep_str)
    
    pyproject['project']['dependencies'] = current_deps
    
    # Write back to file
    with open(pyproject_path, 'w') as f:
        f.write(tomlkit.dumps(pyproject))

def main():
    print("Loading current dependencies...")
    deps = load_current_deps()
    
    print("Updating pyproject.toml...")
    update_pyproject(deps)
    
    print("Done! Please review the changes in pyproject.toml")

if __name__ == '__main__':
    main()