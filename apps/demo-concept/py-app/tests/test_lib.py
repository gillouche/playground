import sys
from pathlib import Path

# Add src to path so we can import lib
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lib import get_greeting

def test_get_greeting():
    result = get_greeting("Tester")
    assert result == "Hello, Tester! Welcome to the Playground."
