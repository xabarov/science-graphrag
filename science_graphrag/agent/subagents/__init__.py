"""Agent v3 subagent runtime package (foundation)."""

from science_graphrag.agent.subagents import lifecycle as _lifecycle
from science_graphrag.agent.subagents import notification as _notification
from science_graphrag.agent.subagents import runtime as _runtime
from science_graphrag.agent.subagents import sidechain_transcript as _sidechain

RoutingSubagentLegLedger = _runtime.RoutingSubagentLegLedger
SubagentRuntime = _runtime.SubagentRuntime
SubagentSpawnCapacityError = _runtime.SubagentSpawnCapacityError
SubagentTaskSpec = _runtime.SubagentTaskSpec
TerminalState = _runtime.TerminalState
build_subagent_runs_from_routing_log = _runtime.build_subagent_runs_from_routing_log
merge_subagent_run_rows = _runtime.merge_subagent_run_rows

merge_routing_leg_notifications_into_update = _lifecycle.merge_routing_leg_notifications_into_update
messages_for_completed_routing_leg = _lifecycle.messages_for_completed_routing_leg
subagent_lifecycle_enhanced_enabled = _lifecycle.subagent_lifecycle_enhanced_enabled
append_subagent_sidechain_event = _sidechain.append_subagent_sidechain_event
subagent_sidechain_jsonl_path = _sidechain.subagent_sidechain_jsonl_path
task_notification_human_message = _notification.task_notification_human_message
sse_payload_from_human_message = _notification.sse_payload_from_human_message

__all__ = [
    *_runtime.__all__,
    "append_subagent_sidechain_event",
    "merge_routing_leg_notifications_into_update",
    "messages_for_completed_routing_leg",
    "sse_payload_from_human_message",
    "subagent_lifecycle_enhanced_enabled",
    "subagent_sidechain_jsonl_path",
    "task_notification_human_message",
]
