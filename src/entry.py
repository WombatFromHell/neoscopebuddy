#!/usr/bin/env python3
"""Entry point for the NeoscopeBuddy application when packaged as zipapp."""

import sys

from nscb.application import main

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
