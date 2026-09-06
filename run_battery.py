#!/usr/bin/env python3
"""Root shim, mirroring run_eval.py.  python3 run_battery.py --member <name>"""
from evals.run_battery import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
