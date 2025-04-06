"""
Main entry point for running as a package.

This allows running the application directly as a package:
    python -m pricing_engine
"""

import sys
from cli import main

if __name__ == "__main__":
    sys.exit(main())
