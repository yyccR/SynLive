"""直播 Session 管理器（内存版）。

本阶段用进程内字典 + 锁顶替；后续接入 Redis / PostgreSQL 后换实现即可，
对外保持 create/get/set_livetalking_session/to_dict 接口不变。
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import asdict, dataclass


@dataclass
class LiveSession:
    id: str
    title: str
    avatar: str | None
    voice: str | None
    lang: str
    livetalking_session_id: str | None
    created_at: float
    status: str = "created"  # created | streaming | stopped


class SessionStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, LiveSession] = {}

    def create(
        self,
        title: str = "未命名直播",
        avatar: str | None = None,
        voice: str | None = None,
        lang: str = "zh",
    ) -> LiveSession:
        session = LiveSession(
            id=str(uuid.uuid4()),
            title=title,
            avatar=avatar,
            voice=voice,
            lang=lang,
            livetalking_session_id=None,
            created_at=time.time(),
        )
        with self._lock:
            self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> LiveSession | None:
        return self._sessions.get(session_id)

    def set_livetalking_session(self, session_id: str, livetalking_session_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            session.livetalking_session_id = livetalking_session_id
            return True

    def set_status(self, session_id: str, status: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            session.status = status
            return True

    @staticmethod
    def to_dict(session: LiveSession) -> dict:
        return asdict(session)


session_store = SessionStore()
