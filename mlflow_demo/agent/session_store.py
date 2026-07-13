"""Per-session conversation state for multi-turn DC Assistant chats.

Keeps conversation history keyed by session_id instead of on a shared
ToolCallingAgent singleton, so concurrent conversations (different users,
different tabs) never clobber each other's state.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4


@dataclass
class ConversationState:
    session_id: str
    user_id: Optional[str] = None
    history: list[dict] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    last_active: float = field(default_factory=time.time)


class SessionStore:
    """In-memory store of ConversationState keyed by session_id.

    Single-process only: state is lost on restart/scale-out. Acceptable for
    this demo app (app.yaml runs a single uvicorn worker); revisit with
    external storage (e.g. Redis) if this app is ever scaled to multiple
    workers/replicas.
    """

    def __init__(self, max_age_seconds: float = 6 * 3600):
        self._sessions: dict[str, ConversationState] = {}
        self._store_lock = threading.Lock()
        self._max_age_seconds = max_age_seconds

    def get_or_create(
        self, session_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> ConversationState:
        """Look up a session by id, or create a fresh one.

        Passing session_id=None (or an id this process has never seen, e.g.
        after a restart) always creates fresh state rather than raising.
        """
        with self._store_lock:
            self._evict_stale()

            if session_id and session_id in self._sessions:
                state = self._sessions[session_id]
                state.last_active = time.time()
                if user_id:
                    state.user_id = user_id
                return state

            new_id = session_id or str(uuid4())
            state = ConversationState(session_id=new_id, user_id=user_id)
            self._sessions[new_id] = state
            return state

    def _evict_stale(self) -> None:
        """Drop sessions untouched for longer than max_age_seconds.

        Must be called with _store_lock held.
        """
        now = time.time()
        stale = [
            sid
            for sid, state in self._sessions.items()
            if now - state.last_active > self._max_age_seconds
        ]
        for sid in stale:
            del self._sessions[sid]
