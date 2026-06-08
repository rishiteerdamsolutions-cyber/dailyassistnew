from aha.user_messages import rest_cooldown_message


def test_rest_cooldown_singular():
    assert "1 hour" in rest_cooldown_message(1)
    assert "using computer" in rest_cooldown_message(1).lower()


def test_rest_cooldown_plural():
    msg = rest_cooldown_message(3)
    assert "3 hours" in msg
    assert "assistant time" not in msg.lower()
