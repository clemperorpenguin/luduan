#!/usr/bin/env python3
"""
Luduan GUI Launcher
Convenient script to start the Luduan graphical interface.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt6.QtWidgets import QApplication
except ImportError:
    print("PyQt6 is not installed. Please install it with:")
    print("  pip install -r requirements_gui.txt")
    sys.exit(1)

from gui import main

if __name__ == "__main__":
    main()
