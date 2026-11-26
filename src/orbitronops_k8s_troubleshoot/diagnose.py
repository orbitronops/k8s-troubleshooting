"""Diagnosis: run the checks in order, narrow to a probable cause.

The first decisive ``fail`` wins — that is the point of the ordering.
If no check fails decisively, the engine says it does not know, with a
low confidence, instead of guessing.
"""
from __future__ import annotations

from .checks import CHECK_ORDER, run_checks
from .models import Diagnosis, Symptom
from .runbooks import runbook_for

# check name -> (cause key, probable cause, confidence, severity)
CAUSES = {
    "image": (
        "image_pull",
        "ImagePullBackOff — image tag missing, or registry auth",
        0.90,
        "HIGH",
    ),
    "resources": (
        "oomkilled",
        "OOMKilled — container exceeded its memory limit",
        0.88,
        "HIGH",
    ),
    "probes": (
        "probe_failing",
        "Readiness / liveness probe failing — app not ready, or probe too strict",
        0.78,
        "MEDIUM",
    ),
    "config": (
        "config_error",
        "Bad config / missing env var — process exits on startup",
        0.72,
        "MEDIUM",
    ),
    "node_pressure": (
        "node_pressure",
        "Node pressure — disk / memory pressure evicting pods",
        0.80,
        "HIGH",
    ),
    "networking": (
        "networking",
        "Service not reachable — selector, endpoints, or NetworkPolicy",
        0.75,
        "MEDIUM",
    ),
    "scheduling": (
        "unschedulable",
        "Unschedulable — no node fits the pod's requests or constraints",
        0.82,
        "HIGH",
    ),
}


def diagnose(s: Symptom) -> Diagnosis:
    checks = run_checks(s)

    cause_key = "unknown"
    probable_cause = "Unknown — not enough evidence to name a cause"
    confidence = 0.30
    severity = "LOW"

    for check in checks:
        if check.outcome == "fail" and check.name in CAUSES:
            cause_key, probable_cause, confidence, severity = CAUSES[check.name]
            break

    # A CrashLoopBackOff with repeated restarts is at least MEDIUM even
    # when the cause is unknown — the pod is not serving traffic.
    if cause_key == "unknown" and s.status == "CrashLoopBackOff":
        severity = "MEDIUM"

    signals = [f"{c.name}: {c.evidence}" for c in checks if c.outcome == "fail"]
    if not signals:
        signals = ["no check failed decisively; evidence is incomplete"]

    commands, fix = runbook_for(cause_key)
    pod = s.pod_name or f"{s.service}-<pod>"
    node = s.node_name or "<node>"
    filled = [
        cmd.format(pod=pod, ns=s.namespace, node=node, service=s.service)
        for cmd in commands
    ]

    return Diagnosis(
        symptom_id=s.id,
        service=s.service,
        severity=severity,
        probable_cause=probable_cause,
        confidence=confidence,
        checks=checks,
        signals=signals,
        read_only_commands=filled,
        fix_suggestion=fix,
        requires_human_approval=True,
        action_executed=False,
    )
