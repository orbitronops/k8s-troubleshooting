"""Tests for the Kubernetes troubleshooting agent."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from orbitronops_k8s_troubleshoot.checks import CHECK_ORDER, run_checks  # noqa: E402
from orbitronops_k8s_troubleshoot.diagnose import diagnose  # noqa: E402
from orbitronops_k8s_troubleshoot.models import Symptom  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "orbitronops_k8s_troubleshoot"


def _symptom(**overrides):
    base = {"id": "T-1", "service": "svc", "namespace": "prod", "pod_name": "svc-abc"}
    base.update(overrides)
    return Symptom.from_dict(base)


def test_crashloop_oom_is_diagnosed():
    s = _symptom(
        status="CrashLoopBackOff", restarts=12, last_exit_code=137,
        last_terminated_reason="OOMKilled", memory_usage_mi=511,
        memory_limit_mi=512, log_snippet="OutOfMemoryError",
    )
    d = diagnose(s)
    assert "OOMKilled" in d.probable_cause
    assert d.confidence >= 0.85
    assert d.severity == "HIGH"
    assert d.action_executed is False
    assert d.requires_human_approval is True


def test_imagepull_is_diagnosed():
    s = _symptom(
        status="ImagePullBackOff", image="registry.example.com/app:9.9.9",
        image_pull_error="manifest unknown",
    )
    d = diagnose(s)
    assert "ImagePullBackOff" in d.probable_cause
    assert d.confidence >= 0.85


def test_pending_unschedulable_is_diagnosed():
    s = _symptom(
        status="Pending",
        unschedulable_reason="Insufficient memory: 0/4 nodes are available",
    )
    d = diagnose(s)
    assert "Unschedulable" in d.probable_cause
    assert d.confidence >= 0.8


def test_probe_failing_is_diagnosed():
    s = _symptom(status="Running", probe_failing="readiness")
    d = diagnose(s)
    assert "probe" in d.probable_cause.lower()
    assert d.confidence >= 0.7


def test_node_pressure_eviction_is_diagnosed():
    s = _symptom(
        status="Evicted", last_terminated_reason="Evicted",
        node_condition="DiskPressure", node_name="node-1",
    )
    d = diagnose(s)
    assert "Node pressure" in d.probable_cause


def test_check_order_is_canonical():
    assert CHECK_ORDER == [
        "image", "resources", "probes", "config",
        "node_pressure", "networking", "scheduling",
    ]
    # Image failure wins over a later scheduling failure: the first
    # decisive failure decides the cause.
    s = _symptom(
        status="ImagePullBackOff", image_pull_error="manifest unknown",
        unschedulable_reason="Insufficient cpu",
    )
    assert diagnose(s).probable_cause.startswith("ImagePullBackOff")


def test_unknown_symptom_is_honest():
    s = _symptom(status="Running")
    d = diagnose(s)
    assert "Unknown" in d.probable_cause
    assert d.confidence <= 0.35


def test_no_mutating_commands_anywhere():
    forbidden = [
        "kubectl delete", "kubectl scale", "kubectl apply", "kubectl drain",
        "kubectl cordon", "kubectl exec", "kubectl rollout restart",
    ]
    for path in SRC.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for bad in forbidden:
            assert bad not in text, f"{bad} found in {path.name}"
    # And every command the agent actually emits is read-only.
    for name in ("crashloop.json", "pending.json", "imagepull.json"):
        data = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
        for cmd in diagnose(Symptom.from_dict(data)).read_only_commands:
            verb = cmd.split()[1]
            assert verb in ("get", "describe", "logs", "top"), cmd


def test_empty_and_missing_fields_handled():
    d = diagnose(Symptom.from_dict({}))
    assert d.service == "unknown"
    assert d.confidence <= 0.35
    assert d.action_executed is False
    d2 = diagnose(Symptom.from_dict({"service": "svc", "status": "CrashLoopBackOff"}))
    assert d2.probable_cause  # never empty


def test_json_output_is_valid():
    s = _symptom(status="CrashLoopBackOff", last_exit_code=137,
                 last_terminated_reason="OOMKilled")
    payload = json.loads(json.dumps(diagnose(s).to_dict()))
    assert payload["action_executed"] is False
    assert payload["requires_human_approval"] is True
    assert len(payload["checks"]) == len(CHECK_ORDER)


def test_examples_all_diagnose():
    expected = {
        "crashloop.json": "OOMKilled",
        "pending.json": "Unschedulable",
        "imagepull.json": "ImagePullBackOff",
    }
    for name, cause in expected.items():
        data = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
        d = diagnose(Symptom.from_dict(data))
        assert cause in d.probable_cause, (name, d.probable_cause)


def test_cli_text_and_json_run():
    for fmt in ("text", "json"):
        r = subprocess.run(
            [sys.executable, "-m", "orbitronops_k8s_troubleshoot", "diagnose",
             str(ROOT / "examples" / "crashloop.json"), "--format", fmt],
            cwd=ROOT, capture_output=True, text=True, env={"PYTHONPATH": "src"},
        )
        assert r.returncode == 0, r.stderr
        if fmt == "json":
            json.loads(r.stdout)
        else:
            assert "OOMKilled" in r.stdout
            assert "no action was executed" in r.stdout.lower()
