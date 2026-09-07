"""Pytest configuration: makes `src/` importable as top-level modules
(e.g. `import extract`) without needing an installable package layout.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
