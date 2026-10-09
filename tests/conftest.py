"""pytest configuration: ensure the repo root is importable as the package base.

Lets tests do `from config import ...` and `from src.X import ...` regardless of
the directory pytest is invoked from.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
