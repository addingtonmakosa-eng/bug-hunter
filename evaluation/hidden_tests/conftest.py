"""Make the demo app under test importable.

BUG_HUNTER_TARGET must point at a demo-app directory (see test_acceptance.py).
"""

import os
import sys

TARGET = os.path.abspath(os.environ.get("BUG_HUNTER_TARGET", ""))
if not os.path.isfile(os.path.join(TARGET, "transaction_service.py")):
    raise RuntimeError("Set BUG_HUNTER_TARGET to a demo-app directory")
sys.path.insert(0, TARGET)
