#!/usr/bin/env python3
"""
neohiro/news — standalone news fetcher
Can be run standalone without installing: curl ... | python3 - --all
"""

import sys
from pathlib import Path

# Add src/ to path for standalone use
_src = Path(__file__).parent / "src"
if _src.exists():
    sys.path.insert(0, str(_src.parent))

from news.cli import main

if __name__ == "__main__":
    sys.exit(main())
