"""Bounded in-memory chat history keyed by (user_id, session_id).

Swap for a DB table or Redis if you run more than one worker.
"""

from __future__ import annotations

from collections import OrderedDict, deque

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

MAX_SESSIONS = 500
MAX_MESSAGES = 12  # 6 turns

_sessions: OrderedDict[tuple[int, str], deque[BaseMessage]] = OrderedDict()


def get_messages(user_id: int, session_id: str) -> list[BaseMessage]:
    key = (user_id, session_id)
    if key not in _sessions:
        return []
    _sessions.move_to_end(key)
    return list(_sessions[key])


def add_turn(user_id: int, session_id: str, user_text: str, ai_text: str) -> None:
    key = (user_id, session_id)
    buf = _sessions.setdefault(key, deque(maxlen=MAX_MESSAGES))
    buf.append(HumanMessage(content=user_text))
    buf.append(AIMessage(content=ai_text))
    _sessions.move_to_end(key)
    while len(_sessions) > MAX_SESSIONS:
        _sessions.popitem(last=False)


def clear_user(user_id: int) -> None:
    """Forget all in-memory chat sessions for a user."""
    for key in [k for k in _sessions if k[0] == user_id]:
        del _sessions[key]
