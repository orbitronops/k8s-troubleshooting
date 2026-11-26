"""Data models for the troubleshooting agent. Plain dataclasses, no dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Symptom:
    """What is wrong, as reported by an alert, a pod status, or an operator.

    All fields are optional except ``service`` — a missing field means
    "not observed", never "assumed healthy". The engine says so plainly
    when it cannot tell.
    """

    id: str = "unknown"
    service: str = "unknown"
    namespace: str = "prod"
    pod_name: str = ""
    status: str = ""  # e.g. CrashLoopBackOff, ImagePullBackOff, Pending, Running
    restarts: int = 0
    restart_window_minutes: int = 10
    last_exit_code: int | None = None
    last_terminated_reason: str = ""  # e.g. OOMKilled, Error, Evicted
    image: str = ""
    image_pull_error: str = ""
    memory_usage_mi: int | None = None
    memory_limit_mi: int | None = None
    memory_request_mi: int | None = None
    cpu_usage_millicores: int | None = None
    cpu_limit_millicores: int | None = None
    log_snippet: str = ""
    events: list[str] = field(default_factory=list)
    node_condition: str = ""  # e.g. DiskPressure, MemoryPressure, Ready
    node_name: str = ""
    probe_failing: str = ""  # e.g. readiness, liveness, ""
    unschedulable_reason: str = ""  # e.g. Insufficient cpu, node selector, taints
    service_reachable: bool | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Symptom":
        return cls(
            id=str(data.get("id", "unknown")),
            service=str(data.get("service", "unknown")),
            namespace=str(data.get("namespace", "prod")),
            pod_name=str(data.get("pod_name", "")),
            status=str(data.get("status", "")),
            restarts=int(data.get("restarts", 0) or 0),
            restart_window_minutes=int(data.get("restart_window_minutes", 10) or 10),
            last_exit_code=data.get("last_exit_code"),
            last_terminated_reason=str(data.get("last_terminated_reason", "")),
            image=str(data.get("image", "")),
            image_pull_error=str(data.get("image_pull_error", "")),
            memory_usage_mi=data.get("memory_usage_mi"),
            memory_limit_mi=data.get("memory_limit_mi"),
            memory_request_mi=data.get("memory_request_mi"),
            cpu_usage_millicores=data.get("cpu_usage_millicores"),
            cpu_limit_millicores=data.get("cpu_limit_millicores"),
            log_snippet=str(data.get("log_snippet", "")),
            events=list(data.get("events", []) or []),
            node_condition=str(data.get("node_condition", "")),
            node_name=str(data.get("node_name", "")),
            probe_failing=str(data.get("probe_failing", "")),
            unschedulable_reason=str(data.get("unschedulable_reason", "")),
            service_reachable=data.get("service_reachable"),
        )


@dataclass
class CheckResult:
    """One step of the diagnosis, in the order it was run."""

    name: str
    outcome: str  # "pass" | "fail" | "inconclusive"
    evidence: str
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "outcome": self.outcome,
            "evidence": self.evidence,
            "detail": self.detail,
        }


@dataclass
class Diagnosis:
    """The agent's assessment. Advisory only — a human decides what happens next."""

    symptom_id: str
    service: str
    severity: str  # LOW | MEDIUM | HIGH | CRITICAL
    probable_cause: str
    confidence: float  # 0.0 – 1.0
    checks: list[CheckResult] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    read_only_commands: list[str] = field(default_factory=list)
    fix_suggestion: str = ""
    requires_human_approval: bool = True
    action_executed: bool = False

    def to_dict(self) -> dict:
        return {
            "symptom_id": self.symptom_id,
            "service": self.service,
            "severity": self.severity,
            "probable_cause": self.probable_cause,
            "confidence": self.confidence,
            "checks": [c.to_dict() for c in self.checks],
            "signals": self.signals,
            "read_only_commands": self.read_only_commands,
            "fix_suggestion": self.fix_suggestion,
            "requires_human_approval": self.requires_human_approval,
            "action_executed": self.action_executed,
        }
