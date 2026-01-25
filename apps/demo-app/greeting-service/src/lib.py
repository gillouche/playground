import os
import html

def get_greeting(name: str) -> str:
    env = os.environ.get("ENVIRONMENT", "unknown")
    return f"Hello, {name}! Welcome to the Playground ({env})."

def sanitize(input_str: str | None) -> str:
    if not input_str:
        return ""
    return html.escape(input_str.strip())
