#!/usr/bin/env python
"""
Check if the required dependencies for the Nexagent API server are installed.
"""

import importlib
import sys

def check_dependency(module_name, package_name=None):
    """Check if a dependency is installed"""
    if package_name is None:
        package_name = module_name
    
    try:
        importlib.import_module(module_name)
        print(f"✅ {package_name} is installed")
        return True
    except ImportError:
        print(f"❌ {package_name} is not installed. Install it with: pip install {package_name}")
        return False

def main():
    """Check all required dependencies"""
    dependencies = [
        ("fastapi", None),
        ("uvicorn", None),
        ("pydantic", None),
        ("websocket", "websocket-client"),  # For the test script
        ("requests", None),  # For the test script
    ]
    
    all_installed = True
    
    print("Checking dependencies for Nexagent API server...")
    
    for module_name, package_name in dependencies:
        if not check_dependency(module_name, package_name):
            all_installed = False
    
    if all_installed:
        print("\nAll required dependencies are installed! 🎉")
        return 0
    else:
        print("\nSome dependencies are missing. Please install them with pip.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
