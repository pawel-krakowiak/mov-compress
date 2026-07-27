"""Allow running the app with ``python -m mov_compress``."""

import sys

from .app import main

if __name__ == "__main__":
    sys.exit(main())
