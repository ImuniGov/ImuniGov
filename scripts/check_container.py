"""Run API tests against isolated temporary PostgreSQL schemas; never truncate app tables."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pytest

os.environ["TEST_DATABASE_URL"] = os.environ["DATABASE_URL"]
raise SystemExit(pytest.main(["-q", "-p", "no:cacheprovider", "tests"]))
