"""Tests for SqliteCheckpointSaver."""

import tempfile
from pathlib import Path
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

from app.checkpoint import SqliteCheckpointSaver, get_sqlite_checkpointer


class CounterState(TypedDict):
    count: int
    history: list[str]


def increment_node(state: CounterState) -> CounterState:
    c = state["count"] + 1
    return {"count": c, "history": state.get("history", []) + [f"step_{c}"]}


def test_sqlite_checkpoint_saver_multi_turn_and_restart():
    builder = StateGraph(CounterState)
    builder.add_node("inc", increment_node)
    builder.add_edge(START, "inc")
    builder.add_edge("inc", END)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_ckpt.sqlite3"
        saver1 = SqliteCheckpointSaver(db_path=db_file)
        graph1 = builder.compile(checkpointer=saver1)

        # Turn 1
        res1 = graph1.invoke({"count": 0, "history": []}, {"configurable": {"thread_id": "thread_abc"}})
        assert res1["count"] == 1
        assert res1["history"] == ["step_1"]

        # Turn 2
        res2 = graph1.invoke({"count": res1["count"]}, {"configurable": {"thread_id": "thread_abc"}})
        assert res2["count"] == 2
        assert res2["history"] == ["step_1", "step_2"]

        # Simulate backend restart: new checkpointer instance pointing to same file
        saver2 = SqliteCheckpointSaver(db_path=db_file)
        graph2 = builder.compile(checkpointer=saver2)
        saved_state = graph2.get_state({"configurable": {"thread_id": "thread_abc"}})
        assert saved_state.values["count"] == 2
        assert saved_state.values["history"] == ["step_1", "step_2"]

        # Delete thread
        saver2.delete_thread("thread_abc")
        deleted_state = graph2.get_state({"configurable": {"thread_id": "thread_abc"}})
        assert not deleted_state.values

        saver1.close()
        saver2.close()
