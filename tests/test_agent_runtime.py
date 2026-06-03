"""Agent runtime lock and session helpers."""

import threading

from aha import agent_runtime


def test_agent_step_uses_lock():
    calls = []

    class FakeAgent:
        def step(self, user_message=None, is_native_app=False):
            calls.append(threading.current_thread().ident)
            return {"status": "success"}

    agent = FakeAgent()
    result = agent_runtime.agent_step(agent, user_message="hi")
    assert result["status"] == "success"
    assert len(calls) == 1


def test_agent_clear_session():
    class FakeAgent:
        def __init__(self):
            self.chat_history = ["x"]
            self.current_plan = [1]
            self.current_plan_step = 3

    agent = FakeAgent()
    agent_runtime.agent_clear_session(agent)
    assert agent.chat_history == []
    assert agent.current_plan is None
    assert agent.current_plan_step == 0
