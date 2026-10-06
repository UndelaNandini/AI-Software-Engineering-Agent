import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

from app.agents.orchestrator import orchestrator
from app.core.event_stream import EventType, event_stream
from app.core.git_manager import GitManager
from app.main import app

client = TestClient(app)


def test_event_stream_emit_and_subscribe():
    async def _test():
        task_id = event_stream.create_task()
        queue = event_stream.subscribe(task_id)

        await event_stream.emit(task_id, EventType.THINKING, "Testing event stream emission")

        event = await queue.get()
        assert event.task_id == task_id
        assert event.event_type == EventType.THINKING
        assert "Testing event stream emission" in event.message

        event_stream.unsubscribe(task_id, queue)

    asyncio.run(_test())


def test_orchestrator_execution(tmp_path: Path):
    repo_dir = tmp_path / "orchestrator_repo"
    repo_dir.mkdir()
    GitManager.get_or_init_repo(repo_dir)

    # Simple working module
    mod_file = repo_dir / "math_mod.py"
    mod_file.write_text("def multiply(a: int, b: int) -> int:\n    return a * b\n", encoding="utf-8")

    test_file = repo_dir / "test_math_mod.py"
    test_file.write_text("from math_mod import multiply\ndef test_mult(): assert multiply(3, 4) == 12\n", encoding="utf-8")

    async def _test():
        result = await orchestrator.execute_task(
            repo_path=str(repo_dir),
            issue_title="Verify math module multiplication",
            issue_description="Verify that multiply function calculates product correctly.",
            auto_approve_plan=True,
        )

        assert result.status == "SUCCESS"
        assert result.task_id is not None
        assert result.final_test_result.passed is True
        assert result.review_report is not None

    asyncio.run(_test())


def test_websocket_stream_historical_and_live():
    task_id = event_stream.create_task()

    # Pre-emit an event
    asyncio.run(event_stream.emit(task_id, EventType.SYSTEM, "Task initialized"))
    asyncio.run(event_stream.emit(task_id, EventType.COMPLETE, "Task finished successfully"))

    with client.websocket_connect(f"/api/v1/tasks/{task_id}/stream") as websocket:
        data1 = websocket.receive_json()
        assert data1["event_type"] == "SYSTEM"
        assert "Task initialized" in data1["message"]

        data2 = websocket.receive_json()
        assert data2["event_type"] == "COMPLETE"
        assert "Task finished successfully" in data2["message"]
