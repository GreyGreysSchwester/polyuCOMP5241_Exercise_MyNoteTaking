"""Vercel serverless entry point.

Vercel's Python runtime looks for a module-level WSGI callable named ``app``.
The real application lives in ``src/main.py``; this file only makes it
importable from the location Vercel expects.

It is never used during local development -- run ``python src/main.py`` there.
"""

import os
import sys

# This file sits in api/, so the project root is one level up. Adding it to
# sys.path is what makes `import src.main` resolve.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from src.main import app  # noqa: E402  (must come after the sys.path tweak)

__all__ = ["app"]
