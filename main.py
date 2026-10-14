"""
main.py — Beginner-friendly terminal interface for the Structured Output AI Agent.

This file is the entry point. Run it with:  python main.py

It handles everything the user sees:
- Welcome message
- Input prompt
- Calling the agent
- Displaying the result
- Asking if the user wants another question
- Exiting cleanly
"""

import json
import sys

from google.genai import errors as genai_errors

from agent import get_topic_explanation


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def print_banner() -> None:
    """Print a friendly welcome banner when the app starts."""
    print("\n" + "=" * 60)
    print("  🤖  Structured Output AI Agent")
    print("  Powered by Google Gemini + Pydantic")
    print("=" * 60)
    print("\nThis agent answers topic questions and returns a")
    print("structured, validated response every time.\n")
    print("Type a topic like:  Python lists")
    print("                    How does HTTP work?")
    print("                    What is a binary search tree?\n")
    print("Type 'quit' or 'exit' to leave.\n")
    print("-" * 60)


def print_result(result) -> None:
    """
    Display the validated TopicExplanation as neatly formatted JSON.

    We call result.model_dump() to convert the Pydantic model to a plain
    Python dictionary, then json.dumps() to format it with indentation.
    """
    print("\n" + "=" * 60)
    print("  ✅  Validated Response")
    print("=" * 60)

    # model_dump() turns the Pydantic object into a plain dict
    data = result.model_dump()
    print(json.dumps(data, indent=2))

    print("\n" + "-" * 60)
    print(f"  Topic     : {result.topic}")
    print(f"  Difficulty: {result.difficulty}")
    print(f"  Key Points: {len(result.key_points)} items")
    print(f"  Next Steps: {len(result.next_steps)} items")
    print("-" * 60 + "\n")


def print_error(message: str) -> None:
    """Print a user-friendly error message."""
    print("\n" + "!" * 60)
    print("  ❌  Something went wrong")
    print("!" * 60)
    print(f"\n{message}\n")
    print("Check agent.log for more details.\n")
    print("!" * 60 + "\n")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Main application loop.

    Keeps running until the user types 'quit' or 'exit'.
    Each iteration asks for a topic, calls the agent, and shows the result.
    """
    print_banner()

    while True:
        # --- Get user input ---
        try:
            user_input = input("Enter a topic: ").strip()
        except (KeyboardInterrupt, EOFError):
            # Ctrl+C or Ctrl+D — exit gracefully
            print("\n\nGoodbye! Happy learning. 👋\n")
            sys.exit(0)

        # --- Handle empty input ---
        if not user_input:
            print("  ⚠  Please enter a topic. Try: 'Python functions'\n")
            continue

        # --- Handle exit commands ---
        if user_input.lower() in {"quit", "exit", "q", "bye"}:
            print("\nGoodbye! Happy learning. 👋\n")
            sys.exit(0)

        # --- Call the agent ---
        print(f"\n⏳ Asking Gemini about: '{user_input}' ...\n")

        try:
            result = get_topic_explanation(user_input)
            print_result(result)

        except genai_errors.ClientError as exc:
            code = getattr(exc, "code", None)
            if code == 401:
                print_error(
                    "Authentication failed (HTTP 401).\n\n"
                    "Your GEMINI_API_KEY is invalid or expired.\n"
                    "  1. Visit https://aistudio.google.com/app/apikey\n"
                    "  2. Generate a new API key\n"
                    "  3. Update the GEMINI_API_KEY value in your .env file"
                )
                sys.exit(1)
            elif code == 403:
                print_error(
                    "Permission denied (HTTP 403).\n\n"
                    "Your API key does not have access to the requested model.\n"
                    "Check that GEMINI_MODEL in your .env is a valid model name."
                )
                sys.exit(1)
            else:
                print_error(f"API client error (HTTP {code}): {exc}")

        except RuntimeError as exc:
            # This is raised when MAX_RETRIES is exceeded
            print_error(str(exc))
            # Don't exit — let the user try a different topic

        except ConnectionError as exc:
            print_error(
                f"Network error: {exc}\n\n"
                "Check your internet connection and try again."
            )

        except Exception as exc:
            print_error(f"Unexpected error: {type(exc).__name__}: {exc}")

        # --- Ask if the user wants to continue ---
        print("Press Enter to ask another question, or type 'quit' to exit.")


if __name__ == "__main__":
    main()
