"""
Trace System for AI Agent Platform & Sandbox.
Full observability into agent execution with waterfall timing.
"""

from backend.models import TraceEntry, AgentStep
from datetime import datetime
import json
import uuid


class TraceSystem:
    """Records and queries execution traces for observability."""

    def __init__(self):
        self.traces: dict[str, list[TraceEntry]] = {}  # conversation_id -> traces

    def record(self, conversation_id: str, step: AgentStep, parent_id: str | None = None):
        entry = TraceEntry(
            conversation_id=conversation_id,
            step=step,
            parent_trace_id=parent_id,
        )
        if conversation_id not in self.traces:
            self.traces[conversation_id] = []
        self.traces[conversation_id].append(entry)
        return entry

    def get_traces(self, conversation_id: str) -> list[dict]:
        entries = self.traces.get(conversation_id, [])
        return [
            {
                "trace_id": e.trace_id,
                "step_number": e.step.step_number,
                "step_type": e.step.step_type.value,
                "content": e.step.content,
                "tool_call": e.step.tool_call.model_dump() if e.step.tool_call else None,
                "tool_result": e.step.tool_result,
                "timestamp": e.step.timestamp.isoformat(),
                "latency_ms": e.step.latency_ms,
                "tokens_used": e.step.tokens_used,
                "parent_trace_id": e.parent_trace_id,
            }
            for e in entries
        ]

    def get_waterfall(self, conversation_id: str) -> dict:
        """Generate waterfall timing data for visualization."""
        entries = self.traces.get(conversation_id, [])
        if not entries:
            return {"spans": [], "total_ms": 0}

        start_time = entries[0].step.timestamp
        spans = []
        for e in entries:
            offset = (e.step.timestamp - start_time).total_seconds() * 1000
            spans.append({
                "id": e.trace_id,
                "label": f"{e.step.step_type.value}: {e.step.content[:50]}",
                "type": e.step.step_type.value,
                "start_ms": offset,
                "duration_ms": e.step.latency_ms,
                "parent": e.parent_trace_id,
            })

        total = sum(s["duration_ms"] for s in spans)
        return {"spans": spans, "total_ms": total}

    def export_json(self, conversation_id: str) -> str:
        return json.dumps(self.get_traces(conversation_id), indent=2, default=str)

    def get_summary(self, conversation_id: str) -> dict:
        entries = self.traces.get(conversation_id, [])
        if not entries:
            return {}
        total_latency = sum(e.step.latency_ms for e in entries)
        total_tokens = sum(e.step.tokens_used for e in entries)
        step_types = {}
        for e in entries:
            t = e.step.step_type.value
            step_types[t] = step_types.get(t, 0) + 1
        return {
            "total_steps": len(entries),
            "total_latency_ms": round(total_latency, 2),
            "total_tokens": total_tokens,
            "step_breakdown": step_types,
        }
