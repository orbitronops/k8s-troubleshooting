# Architecture

## Flow

```
Symptom JSON → Checks (in order) → Probable cause + confidence
                              → Read-only runbook + fix suggestion
                              → Human approval gate (nothing executed)
```

## The check order

The checks run in a fixed order, and the first decisive failure wins:

| # | Check | What it looks at |
|---|-------|------------------|
| 1 | image | Pod status `ImagePullBackOff` / `ErrImagePull`, pull errors |
| 2 | resources | Exit 137 / `OOMKilled`, memory at or over the limit |
| 3 | probes | Readiness / liveness probe failing |
| 4 | config | Exit 1 plus a config marker in the logs |
| 5 | node_pressure | `DiskPressure` / `MemoryPressure` / `PIDPressure`, eviction |
| 6 | networking | Service not reachable from inside the cluster |
| 7 | scheduling | `Pending`, scheduler reason (insufficient CPU/memory, taints) |

The order matters: an image that never arrived makes every later
check meaningless, and a pod that was never scheduled has no logs to
read. A check that finds nothing decisive reports `pass` or
`inconclusive` — "inconclusive" means the symptom file had no
evidence for that area, not that the area is healthy.

## Determinism

Same symptom, same diagnosis, every time. There is no randomness, no
network call, and no model. An LLM explainer could be added as a
pluggable interface that only rewords the diagnosis — it would never
change the cause, the confidence, or any number, and it is not part of
v0.1.0.

## Extension points

- Add a check to `checks.py` (keep it in `CHECK_ORDER`) and a cause
  entry in `diagnose.py`, with a runbook in `runbooks.py`.
- Add the symptom to `examples/` and a test in
  `tests/test_troubleshoot.py`.
