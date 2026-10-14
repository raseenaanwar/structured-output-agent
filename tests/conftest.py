"""
conftest.py — pytest configuration loaded automatically before any test.

The most important job of this file is to set a fake GEMINI_API_KEY in the
environment BEFORE config.py is imported.

Why this is necessary:
  config.py calls _require_env("GEMINI_API_KEY") at module load time.
  If no key is found, it calls sys.exit(1) — which would kill the test runner.
  By setting a dummy key here (before any import of config or agent), we
  allow the modules to load without hitting sys.exit().

  Tests that call agent functions mock the Gemini client, so the fake key
  is never sent to any real API.
"""

import os
import sys

# Add the project root to sys.path so that `import agent`, `import schemas`,
# etc. work regardless of how pytest is invoked.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Set fake credentials BEFORE any project module is imported.
# This must happen here, at module level, not inside a fixture.
os.environ.setdefault("GEMINI_API_KEY", "test-fake-key-for-unit-tests")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.0-flash")
os.environ.setdefault("MAX_RETRIES", "3")
os.environ.setdefault("LOG_FILE", "test_agent.log")
