"""Read-only runbooks: the next commands to run, and the fix to propose.

Every command here is read-only: ``get``, ``describe``, ``logs`` and
``top`` only. Nothing in this file is ever executed by the agent —
``action_executed`` stays False and a human approves any change.

The fix suggestion is prose for a human to review. It is never run.
"""
from __future__ import annotations

# Cause key -> (read-only commands, fix suggestion). Commands are
# templates; {pod}, {ns} and {service} are filled in by diagnose.py.
RUNBOOKS: dict[str, tuple[list[str], str]] = {
    "oomkilled": (
        [
            "kubectl describe pod {pod} -n {ns}",
            "kubectl logs {pod} -n {ns} --previous",
            "kubectl top pod {pod} -n {ns}",
        ],
        "Raise the container memory limit (and the request, so the scheduler "
        "places it honestly), then validate under load before calling it fixed.",
    ),
    "image_pull": (
        [
            "kubectl describe pod {pod} -n {ns}",
            "kubectl get events -n {ns} --sort-by=.lastTimestamp",
            "kubectl get secret -n {ns}",
        ],
        "Fix the image reference or the registry credentials, then let the "
        "pod be recreated by its controller — check the tag exists first.",
    ),
    "unschedulable": (
        [
            "kubectl describe pod {pod} -n {ns}",
            "kubectl get nodes --show-labels",
            "kubectl top nodes",
        ],
        "Match the pod's requests, node selector and tolerations to the "
        "nodes that actually exist, or add capacity — do not lower the "
        "requests just to make it fit.",
    ),
    "probe_failing": (
        [
            "kubectl describe pod {pod} -n {ns}",
            "kubectl logs {pod} -n {ns}",
            "kubectl get endpoints {service} -n {ns}",
        ],
        "Check what the probe actually hits: the path, the port, and the "
        "startup time. Loosen the probe only if the app is genuinely slow "
        "to start; fix the app if it is not responding.",
    ),
    "node_pressure": (
        [
            "kubectl describe node {node}",
            "kubectl top node {node}",
            "kubectl get pods --all-namespaces --field-selector spec.nodeName={node}",
        ],
        "Relieve the node — find what is consuming disk or memory there — "
        "and check whether the evicted workloads have somewhere healthy to land.",
    ),
    "config_error": (
        [
            "kubectl describe pod {pod} -n {ns}",
            "kubectl logs {pod} -n {ns} --previous",
            "kubectl get configmap -n {ns}",
        ],
        "Correct the missing or wrong configuration value, then verify the "
        "new value in a non-production environment first.",
    ),
    "networking": (
        [
            "kubectl get svc {service} -n {ns}",
            "kubectl get endpoints {service} -n {ns}",
            "kubectl describe pod {pod} -n {ns}",
        ],
        "Trace the path: Service selector, endpoints, NetworkPolicy, and "
        "the pod's listening port — in that order.",
    ),
    "unknown": (
        [
            "kubectl describe pod {pod} -n {ns}",
            "kubectl logs {pod} -n {ns} --previous",
            "kubectl get events -n {ns} --sort-by=.lastTimestamp",
        ],
        "Gather more evidence before changing anything: describe, logs, and "
        "events, then re-run the diagnosis with the fuller picture.",
    ),
}


def runbook_for(cause_key: str) -> tuple[list[str], str]:
    return RUNBOOKS.get(cause_key, RUNBOOKS["unknown"])
