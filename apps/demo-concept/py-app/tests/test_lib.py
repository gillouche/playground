from lib import get_greeting

def test_get_greeting():
    result = get_greeting("Tester")
    assert result == "Hello, Tester! Welcome to the Playground."
