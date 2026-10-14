"""
config.py — Application configuration and environment variable loading.

This file is responsible for:
1. Loading the .env file (which holds your secret API key)
2. Reading environment variables
3. Providing a single Config object that the rest of the app uses

Why a separate config file?
  - One place to change settings instead of hunting through multiple files
  - The API key is loaded here and NEVER printed or logged anywhere
  - Easy to see all configurable options at a glance
"""

import os
import sys

from dotenv import load_dotenv

# Load variables from the .env file into the environment.
# This must happen before we try to read os.environ below.
# If .env doesn't exist, load_dotenv() does nothing silently — that's fine
# for production environments that set variables another way.
load_dotenv()


def _require_env(name: str) -> str:
    """
    Read a required environment variable. Exit with a helpful message if missing.

    We use sys.exit() instead of raising an exception because a missing API key
    is a configuration problem, not a bug — no stack trace needed.
    """
    value = os.environ.get(name)
    if not value:
        print(f"\n[ERROR] Required environment variable '{name}' is not set.")
        print("  1. Copy .env.example to .env")
        print("  2. Open .env and replace 'your_gemini_api_key_here' with your real key")
        print("  3. Get a free key at: https://aistudio.google.com/app/apikey\n")
        sys.exit(1)
    return value


class Config:
    """
    Central configuration object for the application.

    All settings live here. Import this class wherever you need a setting.

    Usage:
        from config import Config
        client = genai.Client(api_key=Config.GEMINI_API_KEY)
    """

    # --- Required ---
    # The Gemini API key. Loaded from .env — never hardcoded, never logged.
    GEMINI_API_KEY: str = _require_env("GEMINI_API_KEY")

    # --- Optional with defaults ---
    # Which Gemini model to use. Can be overridden in .env with GEMINI_MODEL=...
    # gemini-2.0-flash is fast, affordable, and supports structured output.
    GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    # How many total attempts to make (1 initial + up to 2 retries = 3 total)
    MAX_RETRIES: int = int(os.environ.get("MAX_RETRIES", "3"))

    # Path to the log file. Automatically created on first run.
    LOG_FILE: str = os.environ.get("LOG_FILE", "agent.log")
