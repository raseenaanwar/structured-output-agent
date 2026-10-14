# Structured Output AI Agent

A beginner-friendly Python project that uses the **Google Gemini API** and **Pydantic v2** to build an AI agent that always returns **validated, structured JSON responses**.

Built for a YouTube tutorial — every line is commented and explained.

---

## What This Project Does

You type a topic like `"Explain Python lists to a beginner"` and the agent:

1. Sends the question to **Google Gemini**
2. Receives a **JSON response** with a guaranteed structure
3. **Validates** the response using Pydantic (checks fields, types, and rules)
4. **Retries automatically** if the response is invalid (up to 3 attempts)
5. Displays the clean, validated result in your terminal

**Sample output:**

```json
{
  "topic": "Python Lists",
  "summary": "A list is an ordered, mutable collection of items in Python. You can store numbers, strings, or even other lists inside it.",
  "difficulty": "Beginner",
  "key_points": [
    "Lists are ordered — items keep their index position.",
    "Lists are mutable — you can add, remove, or change items.",
    "Lists can hold any data type, including mixed types."
  ],
  "example": "fruits = ['apple', 'banana', 'cherry']\nprint(fruits[0])  # Output: apple\nfruits.append('mango')\nprint(len(fruits))  # Output: 4",
  "next_steps": [
    "Learn list methods: .append(), .remove(), .sort(), .pop()",
    "Practice list slicing: my_list[1:3]",
    "Explore list comprehensions: [x*2 for x in my_list]"
  ]
}
```

---

## How the Workflow Works

```
User Input
    ↓
Build Prompt  →  Ask Gemini to return structured JSON
    ↓
Gemini API Call
    ↓
Extract JSON text from response
    ↓
json.loads()  →  Parse the text into a Python dictionary
    ↓                         ↑
  FAIL? ────────────────── Invalid JSON
    ↓
Pydantic Validation  →  Check fields, types, and rules
    ↓                         ↑
  FAIL? ────────────────── Wrong structure/values
    ↓                             └─── Retry with correction prompt (up to 3×)
  PASS
    ↓
Return validated TopicExplanation object
    ↓
Display formatted JSON in terminal
```

### JSON Parsing vs Pydantic Validation — What's the difference?

This is one of the most important concepts in this project:

| Step | Tool | What it checks |
|------|------|----------------|
| **JSON Parsing** | `json.loads()` | Is this valid JSON syntax? Can Python read it? |
| **Pydantic Validation** | `TopicExplanation(**data)` | Are all required fields present? Are the types correct? Do values pass the rules? |

**Example:** The string `{"topic": 123, "difficulty": "Easy"}` is *valid JSON* — `json.loads()` will parse it without error. But Pydantic will *reject* it because `topic` should be a non-empty string and `"Easy"` is not a valid difficulty level.

> ⚠️ **Important:** Schema validation checks the **structure and data types** of the response, not the factual accuracy of the AI's answer. The AI could say something factually wrong but still produce a perfectly valid JSON structure. Always review AI-generated content critically.

---

## Project Structure

```
structured-output-agent/
│
├── main.py              # Terminal interface — run this file
├── agent.py             # Gemini API calls, JSON parsing, Pydantic validation, retries
├── schemas.py           # Pydantic models (TopicExplanation, DifficultyLevel)
├── config.py            # Configuration and API key loading
│
├── requirements.txt     # Python dependencies (pinned versions)
├── .env.example         # Template for your .env file
├── .env                 # YOUR secrets — never commit this (in .gitignore)
├── .gitignore           # Files Git should ignore
├── agent.log            # Log file — created automatically on first run
│
└── tests/
    ├── conftest.py      # pytest setup — sets fake API key before imports
    ├── test_schemas.py  # Tests for Pydantic schema validation
    └── test_agent.py    # Tests for agent logic and retry behaviour
```

### What each file does

| File | Role |
|------|------|
| `schemas.py` | Defines the **contract** — what the AI response must look like |
| `config.py` | Loads settings from `.env` — one place for all configuration |
| `agent.py` | The **brain** — calls Gemini, parses JSON, validates, retries |
| `main.py` | The **face** — what the user interacts with in the terminal |
| `tests/` | Automated tests that run without any API key or internet |

---

## Prerequisites

- **Python 3.10 or higher** — [Download Python](https://www.python.org/downloads/)
- **A Gemini API key** — free at [Google AI Studio](https://aistudio.google.com/app/apikey)

Check your Python version:
```powershell
python --version
```

---

## Setup (Windows PowerShell)

Follow these steps in order. Every command is for **Windows PowerShell**.

### Step 1 — Navigate to the project folder

```powershell
cd c:\projects\TESTIGN\structured-output-agent
```

### Step 2 — Create a virtual environment

A virtual environment keeps this project's dependencies separate from other Python projects on your machine.

```powershell
python -m venv .venv
```

### Step 3 — Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

Your prompt will change to show `(.venv)` — this means the virtual environment is active.

> **Troubleshooting:** If you see a permissions error, run this first:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### Step 4 — Install dependencies

```powershell
pip install -r requirements.txt
```

This installs: `google-generativeai`, `pydantic`, `python-dotenv`, `pytest`, and `pytest-mock`.

### Step 5 — Configure your API key

Copy the example file:
```powershell
Copy-Item .env.example .env
```

Open `.env` in a text editor (Notepad, VS Code, etc.) and replace the placeholder:
```
GEMINI_API_KEY=your_gemini_api_key_here
```
with your real key:
```
GEMINI_API_KEY=AIzaSy...your_actual_key_here
```

> **Where to get a key:** Visit [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey), sign in, and click "Create API key". The free tier is sufficient for this project.

> **Never share your key** — it's like a password. The `.gitignore` file already excludes `.env` from Git.

---

## Running the Application

Make sure your virtual environment is active (you see `(.venv)` in the prompt), then:

```powershell
python main.py
```

You'll see:

```
============================================================
  🤖  Structured Output AI Agent
  Powered by Google Gemini + Pydantic
============================================================

This agent answers topic questions and returns a
structured, validated response every time.

Type a topic like:  Python lists
                    How does HTTP work?
                    What is a binary search tree?

Type 'quit' or 'exit' to leave.

------------------------------------------------------------
Enter a topic:
```

Type any topic and press Enter. Try:
- `Python lists`
- `What is recursion?`
- `How does DNS work?`
- `Explain machine learning to a beginner`

Type `quit` to exit.

---

## Running the Tests

The tests use **mocked** Gemini responses — they do **not** make real API calls and do **not** require your API key to be set.

### Run all tests

```powershell
pytest tests/ -v
```

### Run only schema tests

```powershell
pytest tests/test_schemas.py -v
```

### Run only agent tests

```powershell
pytest tests/test_agent.py -v
```

### Run with a summary of what passed and failed

```powershell
pytest tests/ -v --tb=short
```

**Expected output (all tests passing):**

```
tests/test_schemas.py::TestValidData::test_valid_data_creates_model PASSED
tests/test_schemas.py::TestValidData::test_all_difficulty_levels_are_accepted PASSED
tests/test_schemas.py::TestMissingFields::test_missing_field_raises_validation_error[topic] PASSED
... (all tests) ...
tests/test_agent.py::TestSuccessOnFirstAttempt::test_returns_topic_explanation PASSED
tests/test_agent.py::TestRetryAfterInvalidJson::test_retries_on_invalid_json PASSED
...

============ 35+ passed in X.XXs ============
```

---

## Viewing Logs

Every request is logged to `agent.log` (created automatically). Open it in any text editor to see exactly what happened:

```powershell
Get-Content agent.log
```

**Sample log entries:**

```
2026-10-14 09:15:02 | INFO     | Request started | topic='Python lists' | model='gemini-2.0-flash'
2026-10-14 09:15:04 | DEBUG    | Attempt 1 | Raw response received (512 chars)
2026-10-14 09:15:04 | INFO     | Validation succeeded on attempt 1 | topic='Python lists' | difficulty='Beginner'
```

**If a retry happens:**

```
2026-10-14 09:15:02 | INFO     | Request started | topic='HTTP' | model='gemini-2.0-flash'
2026-10-14 09:15:04 | WARNING  | Attempt 1 | Validation failed: Field 'difficulty': Input should be 'Beginner', 'Intermediate' or 'Advanced'
2026-10-14 09:15:04 | WARNING  | Retry 2/3 | Previous error: Pydantic validation errors: ...
2026-10-14 09:15:06 | INFO     | Validation succeeded on attempt 2 | topic='HTTP' | difficulty='Intermediate'
```

---

## Configuration Reference

All settings are controlled via your `.env` file:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | ✅ Yes | — | Your Gemini API key from Google AI Studio |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Which Gemini model to use |
| `MAX_RETRIES` | No | `3` | Total attempts including the first one |
| `LOG_FILE` | No | `agent.log` | Path to the log file |

**Supported Gemini models:**

| Model | Speed | Notes |
|-------|-------|-------|
| `gemini-2.0-flash` | Fast ⚡ | Default — recommended for this project |
| `gemini-1.5-flash` | Fast ⚡ | Alternative flash model |
| `gemini-1.5-pro` | Slower | Higher capability, more expensive |

---

## Error Reference

| Error | Cause | Fix |
|-------|-------|-----|
| `GEMINI_API_KEY is not set` | `.env` missing or key not set | Copy `.env.example` to `.env` and add your key |
| `Authentication failed` | API key is invalid or expired | Generate a new key at [AI Studio](https://aistudio.google.com/app/apikey) |
| `Permission denied` | Key doesn't have model access | Check `GEMINI_MODEL` in `.env` is a valid model name |
| `Failed to get a valid response after 3 attempts` | Gemini kept returning invalid JSON | Check `agent.log` for details; try rephrasing the question |
| `Network error` | No internet connection | Check your connection |
| `ModuleNotFoundError` | Dependencies not installed | Run `pip install -r requirements.txt` |

---

## How the Retry Logic Works

The agent tries up to `MAX_RETRIES` times (default: 3). Here's exactly what happens on each attempt:

```
Attempt 1:  Send initial prompt → Gemini returns response
              ├── JSON invalid?  → Log warning → go to Attempt 2
              └── Pydantic fails? → Log warning → go to Attempt 2

Attempt 2:  Send CORRECTION prompt (includes the error message from attempt 1)
              ├── JSON invalid?  → Log warning → go to Attempt 3
              └── Pydantic fails? → Log warning → go to Attempt 3

Attempt 3:  Send CORRECTION prompt (includes the error message from attempt 2)
              ├── JSON invalid?  → Log error → raise RuntimeError
              └── Pydantic fails? → Log error → raise RuntimeError

Any attempt:  API auth error?   → raise immediately (don't retry)
              Rate limit error? → wait, then retry
```

The correction prompt tells Gemini exactly what went wrong, so it can fix the specific issue rather than just guessing again.

---

## Understanding the Code (for beginners)

### Why Pydantic?

When you ask an AI a question, you get back text. Even if that text looks like JSON, you can't trust it without checking. Pydantic lets you define the exact shape of data you expect and automatically checks every field.

```python
# This might look fine...
data = {"topic": "Lists", "difficulty": "Easy", "key_points": []}

# But Pydantic catches the problems:
result = TopicExplanation(**data)
# ❌ ValidationError:
#   difficulty: 'Easy' is not a valid DifficultyLevel (must be Beginner/Intermediate/Advanced)
#   key_points: must have at least 3 items
#   summary: field required
#   example: field required
#   next_steps: field required
```

### Why an Enum for difficulty?

```python
class DifficultyLevel(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"
```

Without an Enum, Gemini might return `"easy"`, `"BEGINNER"`, `"beginner"`, `"novice"` — all different strings for the same concept. The Enum enforces exactly one accepted spelling, making the data consistent and reliable.

### Why separate the config?

```python
# Without config.py — scattered and risky:
api_key = os.environ.get("GEMINI_API_KEY")  # in agent.py
model = "gemini-2.0-flash"                   # hardcoded in agent.py

# With config.py — one place, validated at startup:
from config import Config
# Config.GEMINI_API_KEY — loaded from .env, exits with helpful message if missing
# Config.GEMINI_MODEL   — configurable without changing code
```

---

## Deactivating the Virtual Environment

When you're done working on the project:

```powershell
deactivate
```

To reactivate later:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## Tech Stack

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Programming language |
| google-generativeai | 0.8.3 | Official Gemini API client |
| pydantic | 2.10.6 | Data validation |
| python-dotenv | 1.0.1 | Load `.env` files |
| pytest | 8.3.5 | Test runner |
| pytest-mock | 3.14.0 | Mocking for unit tests |

---

## License

MIT — free to use, modify, and share.
