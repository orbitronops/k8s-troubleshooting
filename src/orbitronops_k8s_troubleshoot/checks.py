"""Ordered diagnostic checks.

The order is deliberate and mirrors how a platform engineer works a
failing pod: image first (nothing else matters if the image never
arrived), then resources, probes, config, node pressure, networking,
and scheduling last — because a scheduling problem only shows when
everything else looks fine.

Each check returns a CheckResult. ``fail`` means the check found the
problem; ``pass`` means that area looks healthy; ``inconclusive``
means the symptom file did not contain enough evidence to tell.
"""
from __future__ import annotations

from .models import CheckResult, Symptom

# The canonical check order. diagnose.py runs them in this order and
# stops narrowing once a decisive failure is found.
CHECK_ORDER = [
    "image",
    "resources",
    "probes",
    "config",
    "node_pressure",
    "networking",
    "scheduling",
]


def check_image(s: Symptom) -> CheckResult:
    if s.status in ("ImagePullBackOff", "ErrImagePull") or s.image_pull_error:
        return CheckResult(
            "image",
            "fail",
            f"status={s.status or 'unknown'}; pull error: {s.image_pull_error or 'image could not be pulled'}",
            f"Image {s.image or '(unknown)'} never reached the node.",
        )
    if s.image:
        return CheckResult("image", "pass", f"image {s.image} pulled successfully", "")
    return CheckResult("image", "inconclusive", "no image information in symptom", "")


def check_resources(s: Symptom) -> CheckResult:
    if s.last_terminated_reason == "OOMKilled" or s.last_exit_code == 137:
        usage = f"{s.memory_usage_mi}Mi" if s.memory_usage_mi is not None else "unknown"
        limit = f"{s.memory_limit_mi}Mi" if s.memory_limit_mi is not None else "unknown"
        return CheckResult(
            "resources",
            "fail",
            f"terminated reason=OOMKilled, exit code 137, memory {usage} / {limit}",
            "Container was killed for exceeding its memory limit.",
        )
    if (
        s.memory_usage_mi is not None
        and s.memory_limit_mi is not None
        and s.memory_limit_mi > 0
        and s.memory_usage_mi / s.memory_limit_mi >= 0.9
    ):
        return CheckResult(
            "resources",
            "fail",
            f"memory {s.memory_usage_mi}Mi / {s.memory_limit_mi}Mi (over 90% of limit)",
            "Memory is at the limit; the next spike will kill the container.",
        )
    if s.memory_limit_mi is not None or s.cpu_limit_millicores is not None:
        return CheckResult(
            "resources",
            "pass",
            "no OOM signal; usage is inside the configured limits",
            "",
        )
    return CheckResult("resources", "inconclusive", "no resource usage in symptom", "")


def check_probes(s: Symptom) -> CheckResult:
    if s.probe_failing:
        return CheckResult(
            "probes",
            "fail",
            f"{s.probe_failing} probe failing; status={s.status or 'unknown'}",
            "The pod is up but Kubernetes does not consider it ready (or alive).",
        )
    if s.status == "Running":
        return CheckResult("probes", "pass", "pod Running, no probe reported failing", "")
    return CheckResult("probes", "inconclusive", "no probe information in symptom", "")


def check_config(s: Symptom) -> CheckResult:
    snippet = (s.log_snippet or "").lower()
    config_markers = [
        "config",
        "missing env",
        "environment variable",
        "file not found",
        "no such file",
        "invalid",
        "connection refused",
    ]
    if s.last_exit_code == 1 and any(m in snippet for m in config_markers):
        return CheckResult(
            "config",
            "fail",
            f"exit code 1; log: {s.log_snippet[:120]}",
            "The process started and then died on a configuration problem.",
        )
    if s.status == "CrashLoopBackOff" and s.last_exit_code == 1:
        return CheckResult(
            "config",
            "fail",
            "exit code 1 with repeated crashes and no resource signal",
            "A code or config fault is the most likely explanation for exit 1.",
        )
    if s.log_snippet:
        return CheckResult("config", "pass", "logs show no config error", "")
    return CheckResult("config", "inconclusive", "no log snippet in symptom", "")


def check_node_pressure(s: Symptom) -> CheckResult:
    if s.node_condition in ("DiskPressure", "MemoryPressure", "PIDPressure"):
        return CheckResult(
            "node_pressure",
            "fail",
            f"node {s.node_name or '(unknown)'} reports {s.node_condition}",
            "The node is under pressure and is evicting or refusing pods.",
        )
    if s.last_terminated_reason == "Evicted":
        return CheckResult(
            "node_pressure",
            "fail",
            "pod was evicted",
            "Eviction is a node-pressure or node-failure signal, not an app fault.",
        )
    if s.node_condition == "Ready":
        return CheckResult("node_pressure", "pass", "node reports Ready, no pressure", "")
    return CheckResult("node_pressure", "inconclusive", "no node condition in symptom", "")


def check_networking(s: Symptom) -> CheckResult:
    # A pod that never started (Pending, crash-looping, image never
    # pulled) is unreachable as a consequence, not as a cause. Only
    # blame networking when the pod is actually up and serving.
    if s.status in ("Pending", "CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
        return CheckResult(
            "networking",
            "inconclusive",
            "pod is not serving; unreachability is a consequence, not a cause",
            "",
        )
    if s.service_reachable is False:
        return CheckResult(
            "networking",
            "fail",
            "service is not reachable from inside the cluster",
            "The pod may be healthy while traffic never reaches it.",
        )
    if s.service_reachable is True:
        return CheckResult("networking", "pass", "service is reachable", "")
    return CheckResult("networking", "inconclusive", "no reachability information in symptom", "")


def check_scheduling(s: Symptom) -> CheckResult:
    if s.status == "Pending" or s.unschedulable_reason:
        return CheckResult(
            "scheduling",
            "fail",
            f"status=Pending; scheduler: {s.unschedulable_reason or 'no node fits'}",
            "The pod has never been placed on a node.",
        )
    if s.pod_name:
        return CheckResult("scheduling", "pass", "pod is scheduled on a node", "")
    return CheckResult("scheduling", "inconclusive", "no scheduling information in symptom", "")


CHECKS = {
    "image": check_image,
    "resources": check_resources,
    "probes": check_probes,
    "config": check_config,
    "node_pressure": check_node_pressure,
    "networking": check_networking,
    "scheduling": check_scheduling,
}


def run_checks(s: Symptom) -> list[CheckResult]:
    """Run every check, in order. Nothing is skipped."""
    return [CHECKS[name](s) for name in CHECK_ORDER]
