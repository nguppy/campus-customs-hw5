"""Audit trail: every team run and human action is appended to output/audit_trail.json.

The file is a JSON list and is never wiped -- entries are only appended.
  - "agent_run" entries record, in order, every agent loop that executed
    (Boss and the specialists it delegated to), and for each loop every
    step: the model's tool calls with their arguments, the MCP tool results,
    text output and token usage. System prompts are recorded by file name +
    SHA-256 (not repeated in full) so it is clear which version ran.
  - "human_action" entries record approvals (who approved what, and the
    resulting payment) and database resets made through the backend routes.
"""

import hashlib
import json
import os
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from pydantic_ai.messages import FunctionToolCallEvent, FunctionToolResultEvent
from pydantic_core import to_jsonable_python

from backend.llm import MODEL_NAME, PROJECT_ROOT, PROMPTS_DIR

AUDIT_PATH = PROJECT_ROOT / "output" / "audit_trail.json"

_run: ContextVar[dict | None] = ContextVar("audit_run", default=None)
LIVE_RUN: dict | None = None  # the run in progress, visible to other requests (e.g. /events)
_agent_stack: ContextVar[tuple[str, ...]] = ContextVar("agent_stack", default=())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _sort_key(at: str | None) -> datetime:
    """Timestamps come as '...+00:00' or '...Z' with varying precision; compare as datetimes."""
    if not at:
        return datetime.min.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(at.replace("Z", "+00:00"))


def _jsonable(value: Any) -> Any:
    return to_jsonable_python(value, fallback=str)


def _prompt_fingerprint(role: str) -> dict:
    path = PROMPTS_DIR / f"{role}.md"
    return {"file": f"backend/prompts/{role}.md",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


# --- Run lifecycle ---------------------------------------------------------


def start_run(ticket_ids: list[int], db_reset: bool, run_id: str | None = None) -> dict:
    global LIVE_RUN
    run = {
        "type": "agent_run",
        "run_id": run_id or str(uuid.uuid4()),
        "started_at": _now(),
        "finished_at": None,
        "status": "running",
        "model": MODEL_NAME,
        "database": "data/campus_customs_new.db",
        "database_reset_before_run": db_reset,
        "tickets": ticket_ids,
        "agent_runs": [],
        "ticket_results": [],
        "total_usage": None,
        "error": None,
    }
    _run.set(run)
    LIVE_RUN = run
    return run


def finish_run(status: str, total_usage: Any = None, error: str | None = None) -> None:
    """Append the finished run to the audit file (never overwrites earlier runs)."""
    global LIVE_RUN
    run = _run.get()
    if run is None:
        return
    run.update(finished_at=_now(), status=status, error=error,
               total_usage=_jsonable(total_usage) if total_usage is not None else None)
    _append(run)
    _run.set(None)
    LIVE_RUN = None


def log_human_action(action: str, **details: Any) -> None:
    """Append a human action (approval, reset) made through the backend."""
    _append({"type": "human_action", "run_id": str(uuid.uuid4()), "at": _now(),
             "action": action, "tickets": None, **_jsonable(details)})


def _append(entry: dict) -> None:
    """Append one entry to the audit file, keeping every earlier entry."""
    history: list = []
    if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size > 0:
        try:
            history = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
            if not isinstance(history, list):
                raise ValueError("audit file is not a JSON list")
        except ValueError:
            # Never destroy old evidence: keep the unreadable file aside, start a new list.
            backup = AUDIT_PATH.with_suffix(f".unreadable-{datetime.now():%Y%m%d%H%M%S}.json")
            AUDIT_PATH.rename(backup)
            history = []
    history.append(entry)

    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = AUDIT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(history, indent=2), encoding="utf-8")
    os.replace(tmp, AUDIT_PATH)  # atomic: a crash mid-write cannot corrupt the trail


def record_ticket_result(ticket_id: int, result: Any, usage: Any = None) -> None:
    if (run := _run.get()) is not None:
        run["ticket_results"].append({"ticket_id": ticket_id, "result": _jsonable(result),
                                      "usage": _jsonable(usage) if usage is not None else None})


# --- Agent loops -----------------------------------------------------------


def _steps(messages) -> list[dict]:
    """Turn PydanticAI messages into numbered agent-loop steps.

    Step N = one model response (its tool calls / text) plus the tool results
    that went back to the model afterwards.
    """
    steps: list[dict] = []
    pending_inputs: list[dict] = []
    for msg in messages:
        parts = []
        for p in msg.parts:
            kind = getattr(p, "part_kind", type(p).__name__)
            if kind in ("system-prompt", "instruction"):
                continue  # recorded once per agent run as a fingerprint
            entry: dict = {"kind": kind}
            for attr in ("tool_name", "tool_call_id"):
                if getattr(p, attr, None):
                    entry[attr] = getattr(p, attr)
            if kind == "tool-call":
                entry["args"] = p.args_as_dict() if hasattr(p, "args_as_dict") else _jsonable(p.args)
            elif kind == "thinking":
                entry["chars"] = len(getattr(p, "content", "") or "")
            elif hasattr(p, "content"):
                entry["content"] = _jsonable(p.content)
            parts.append(entry)

        if msg.kind == "request":
            pending_inputs.extend(parts)
        else:  # model response closes a step
            usage = getattr(msg, "usage", None)
            steps.append({
                "step": len(steps) + 1,
                "inputs_to_model": pending_inputs,
                "model_response": parts,
                "model_name": getattr(msg, "model_name", None),
                "timestamp": _jsonable(getattr(msg, "timestamp", None)),
                "usage": {"input_tokens": getattr(usage, "input_tokens", None),
                          "output_tokens": getattr(usage, "output_tokens", None)} if usage else None,
            })
            pending_inputs = []
    if pending_inputs:  # e.g. tool results awaiting approval, not yet sent to the model
        steps.append({"step": len(steps) + 1, "inputs_to_model": pending_inputs, "model_response": None})
    return steps


async def audited_run(agent, role: str, prompt: str | None, **run_kwargs):
    """Run one agent loop and record it in the current audit run.

    The loop is added to the run as soon as it starts, and every tool call /
    tool result is appended to its "activity" list the moment it happens, so
    the dashboard (GET /events) can show agents working live. When the loop
    ends, its full step-by-step record is added. Errors (including usage-limit
    stops) are recorded, then re-raised.
    """
    parent = _agent_stack.get()[-1] if _agent_stack.get() else None
    token = _agent_stack.set(_agent_stack.get() + (role,))
    entry = {
        "sequence": None,
        "agent": role,
        "delegated_by": parent,
        "prompt": _prompt_fingerprint(role),
        "task": prompt,
        "status": "running",
        "started_at": _now(),
        "finished_at": None,
        "activity": [],
        "steps": None,
        "output": None,
        "error": None,
    }
    if (run := _run.get()) is not None:
        entry["sequence"] = len(run["agent_runs"]) + 1
        run["agent_runs"].append(entry)

    async def on_events(ctx, stream) -> None:
        async for event in stream:
            if isinstance(event, FunctionToolCallEvent):
                entry["activity"].append({
                    "at": _now(), "type": "tool_call",
                    "tool": event.part.tool_name.removeprefix("campus-customs_"),
                    "args": _jsonable(event.part.args_as_dict()),
                })
            elif isinstance(event, FunctionToolResultEvent):
                entry["activity"].append({
                    "at": _now(), "type": "tool_result",
                    "tool": event.part.tool_name.removeprefix("campus-customs_"),
                    "result": _brief(_jsonable(getattr(event.part, "content", None))),
                })

    try:
        result = await agent.run(prompt, event_stream_handler=on_events, **run_kwargs)
    except Exception as exc:
        entry.update(status="error", finished_at=_now(), error=f"{type(exc).__name__}: {exc}")
        raise
    else:
        entry.update(
            status="done",
            finished_at=_now(),
            steps=_steps(result.new_messages()),
            output=_jsonable(result.output),
            usage_this_loop=_jsonable(result.usage),
        )
        return result
    finally:
        _agent_stack.reset(token)


# --- Event feed (for the dashboard) ----------------------------------------


def load_runs() -> list[dict]:
    """All finished runs from the audit file, plus the run in progress (if any)."""
    runs: list[dict] = []
    if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size > 0:
        try:
            runs = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        except ValueError:
            runs = []
    if LIVE_RUN is not None:
        runs = runs + [LIVE_RUN]
    return runs


def _brief(value: Any, limit: int = 400) -> Any:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + "..."


def run_events(run: dict) -> list[dict]:
    """Flatten one run into events: what each agent said and which tools it used.

    Types: started (agent picked up a task), tool_call, tool_result, said
    (agent text), report (the agent's final typed report), error,
    human_action (approval / reset).
    """
    if run.get("type") == "human_action":
        return [{"run_id": run["run_id"], "tickets": None, "agent": "human", "delegated_by": None,
                 "loop": None, "at": run["at"], "type": "human_action",
                 "action": run["action"], "board_id": run.get("board_id"),
                 "approved_by": run.get("approved_by")}]
    events: list[dict] = []
    for loop in run.get("agent_runs", []):
        base = {"run_id": run["run_id"], "tickets": run.get("tickets"), "agent": loop["agent"],
                "delegated_by": loop.get("delegated_by"), "loop": loop["sequence"]}
        events.append({**base, "at": loop["started_at"], "type": "started", "text": loop.get("task")})
        for act in loop.get("activity") or []:
            events.append({**base, **act})
        if "activity" not in loop:  # runs recorded before live activity existed
            for step in loop.get("steps") or []:
                at = step.get("timestamp") or loop.get("finished_at")
                for part in step.get("inputs_to_model", []) + (step.get("model_response") or []):
                    tool = (part.get("tool_name") or "").removeprefix("campus-customs_")
                    if part["kind"] == "tool-call" and tool != "final_result":
                        events.append({**base, "at": at, "type": "tool_call", "tool": tool, "args": part.get("args")})
                    elif part["kind"] == "tool-return" and tool != "final_result":
                        events.append({**base, "at": at, "type": "tool_result", "tool": tool,
                                       "result": _brief(part.get("content"))})
        for step in loop.get("steps") or []:
            for part in step.get("model_response") or []:
                if part["kind"] == "text" and part.get("content"):
                    events.append({**base, "at": step.get("timestamp") or loop["finished_at"],
                                   "type": "said", "text": part["content"]})
        if loop.get("error"):
            events.append({**base, "at": loop.get("finished_at"), "type": "error", "text": loop["error"]})
        elif loop.get("output") is not None:
            events.append({**base, "at": loop["finished_at"], "type": "report", "report": loop["output"]})
    events.sort(key=lambda e: _sort_key(e["at"]))
    return events


def recent_events(limit: int = 50, ticket_id: int | None = None) -> list[dict]:
    """The most recent events across runs, oldest first, optionally for one ticket."""
    events: list[dict] = []
    for run in load_runs():
        if ticket_id is not None and ticket_id not in (run.get("tickets") or []):
            continue
        events.extend(run_events(run))
    return events[-limit:]
