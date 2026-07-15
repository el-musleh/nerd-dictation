import os
import sys

# Ensure the repo root (containing backends.py, filters.py, etc.) is importable.
REPO = os.path.dirname(os.path.abspath(__file__))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
