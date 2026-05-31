from hypothesis import given
from hypothesis import strategies as st
from services.book_service import (
    _decode_continuation_token,
    _encode_continuation_token,
    _escape_like,
)


@given(st.text())
def test_escape_like_never_contains_unescaped_metacharacters(s):
    escaped = _escape_like(s)
    i = 0
    while i < len(escaped):
        if escaped[i] == "\\" and i + 1 < len(escaped):
            i += 2
            continue
        assert escaped[i] not in ("%", "_"), (
            f"Unescaped '{escaped[i]}' at position {i} in '{escaped}'"
        )
        i += 1


@given(st.integers(min_value=0, max_value=1_000_000))
def test_continuation_token_roundtrip(offset):
    token = _encode_continuation_token(offset)
    assert _decode_continuation_token(token) == offset


@given(st.text(min_size=1))
def test_escape_like_is_idempotent_on_safe_strings(s):
    safe = s.replace("\\", "").replace("%", "").replace("_", "")
    if safe:
        assert _escape_like(safe) == safe
