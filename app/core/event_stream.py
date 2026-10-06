import asyncio
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    SYSTEM = "SYSTEM"
    THINKING = "THINKING"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    TEST_OUTPUT = "TEST_OUTPUT"
    REPAIR_ATTEMPT = "REPAIR_ATTEMPT"
    REVIEW = "REVIEW"
    ERROR = "ERROR"
    COMPLETE = "COMPLETE"


class AgentEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_id: str
    event_type: EventType
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EventStream:
    """Manages real-time event broadcasting for agent execution tasks."""

    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._task_logs: Dict[str, List[AgentEvent]] = {}

    def create_task(self) -> str:
        task_id = str(uuid.uuid4())
        self._task_logs[task_id] = []
        return task_id

    async def emit(self, task_id: str, event_type: EventType, message: str, data: Optional[Dict] = None):
        event = AgentEvent(
            task_id=task_id,
            event_type=event_type,
            message=message,
            data=data,
        )

        # Store in log
        if task_id not in self._task_logs:
            self._task_logs[task_id] = []
        self._task_logs[task_id].append(event)

        # Broadcast to all WebSocket subscribers
        if task_id in self._subscribers:
            for queue in self._subscribers[task_id]:
                await queue.put(event)

    def subscribe(self, task_id: str) -> asyncio.Queue:
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[task_id].append(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue):
        if task_id in self._subscribers:
            self._subscribers[task_id] = [q for q in self._subscribers[task_id] if q is not queue]

    def get_task_log(self, task_id: str) -> List[AgentEvent]:
        return self._task_logs.get(task_id, [])


# Global singleton
event_stream = EventStream()
