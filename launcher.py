#!/usr/bin/env python3
"""
Sotto Launcher
Entry point for PyInstaller bundle.
"""

import sys
import os

# Add the package directory to path if running from bundle
if getattr(sys, 'frozen', False):
    # Running in a bundle
    bundle_dir = os.path.dirname(sys.executable)
    sys.path.insert(0, bundle_dir)

# Import and run the main function
from sotto.main import main

if __name__ == "__main__":
    main()
