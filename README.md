# OrbitronOps Kubernetes Troubleshooting Agent

> **A read-only Kubernetes troubleshooting agent.** Give it a symptom — a
> pod status, events, resource usage, node conditions — and it walks the
> diagnosis in order, explains each check, narrows to a probable cause,
> and proposes read-only next commands plus a fix suggestion. It never
> runs a mutating command on its own.

[![CI](https://github.com/orbitronops/k8s-troubleshooting/actions/workflows/ci.yml/badge.svg)](https://github.com/orbitronops/k8s-troubleshooting/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Status: Demo](https://img.shields.io/badge/status-demo%20%E2%80%94%20not%20client%20work-lightgrey.svg)

**By [OrbitronOps](https://www.orbitronops.com)** — Production AI Infrastructure on Kubernetes.
North Vancouver, BC · Canada Remote / BC Hybrid

---

## What this proves

A buyer doesn't have to take our word for it. They can run this in 2 minutes:

```
git clone https://github.com/orbitronops/k8s-troubleshooting.git
cd k8s-troubleshooting
python -m orbitronops_k8s_troubleshoot diagnose examples/crashloop.json
```

And get a diagnosis like this:

```
Service: checkout-api  ·  Severity: HIGH  ·  Confidence: 0.88
Probable cause: OOMKilled — container exceeded its memory limit

Checks (in order):
  [ok  ] image: image registry.example.com/checkout-api:1.42.0 pulled successfully
  [FAIL] resources: terminated reason=OOMKilled, exit code 137, memory 511Mi / 512Mi
  [??  ] probes: no probe information in symptom
  [ok  ] config: logs show no config error
  [ok  ] node_pressure: node reports Ready, no pressure
  [??  ] networking: pod is not serving; unreachability is a consequence, not a cause
  [ok  ] scheduling: pod is scheduled on a node

Next steps (read-only):
  1. kubectl describe pod checkout-api-7d9f8-abc12 -n prod
  2. kubectl logs checkout-api-7d9f8-abc12 -n prod --previous
  3. kubectl top pod checkout-api-7d9f8-abc12 -n prod

Fix suggestion (for a human to review, NOT executed): Raise the container memory limit
(and the request, so the scheduler places it honestly), then validate under load
before calling it fixed.

Human approval: REQUIRED — no action was executed.
```

No API key needed for the demo. No cluster needed. No cloud bill.

## Why checks in order?

A troubleshooting agent that jumps to a conclusion is worse than no
agent. This one works the way a platform engineer does:

1. **Image** — nothing else matters if the image never arrived.
2. **Resources** — exit 137 / `OOMKilled`, memory at the limit.
3. **Probes** — readiness / liveness failing.
4. **Config** — exit 1 plus a config marker in the logs.
5. **Node pressure** — disk / memory pressure, eviction.
6. **Networking** — service not reachable (only blamed when the pod
   is actually up — a pod that never started is unreachable as a
   consequence, not a cause).
7. **Scheduling** — `Pending`, no node fits.

The first decisive failure wins. If no check fails decisively, the
agent says it does not know — confidence 0.30 — instead of guessing.

## Quickstart

**Requirements:** Python 3.10+ only. No dependencies for the demo.

```
# 1. Clone
git clone https://github.com/orbitronops/k8s-troubleshooting.git
cd k8s-troubleshooting

# 2. Diagnose the sample symptoms
python -m orbitronops_k8s_troubleshoot diagnose examples/crashloop.json
python -m orbitronops_k8s_troubleshoot diagnose examples/pending.json
python -m orbitronops_k8s_troubleshoot diagnose examples/imagepull.json

# 3. Or JSON, for tooling
python -m orbitronops_k8s_troubleshoot diagnose examples/pending.json --format json

# 4. Run the tests
python -m pytest -q

# or, with no pytest installed:
python -m unittest discover -s tests -v
```

### Try your own symptom

Copy an example and edit it:

```
cp examples/crashloop.json my-symptom.json
# edit my-symptom.json, then:
python -m orbitronops_k8s_troubleshoot diagnose my-symptom.json
```

See [`examples/`](examples/) for the symptom schema, and
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for how the checks work.

## How it works

```
Symptom JSON → Checks (in order) → Probable cause + confidence
                                  → Read-only runbook + fix suggestion
                                  → Human approval gate (nothing executed)
```

| Symptom | Probable cause | Confidence |
| --- | --- | --- |
| `CrashLoopBackOff` + exit 137 + memory at limit | OOMKilled — memory limit too low | High |
| `ImagePullBackOff` / `ErrImagePull` | Image tag missing, or registry auth | High |
| `Pending` + scheduler reason | Unschedulable — no node fits | High |
| Readiness / liveness probe failing | App not ready, or probe too strict | Medium |
| Pod evicted / `NodePressure` | Node disk / memory pressure | Medium |
| `CrashLoopBackOff` + exit 1 + config error in logs | Bad config / missing env var | Medium |
| Service not reachable, pod Running | Selector, endpoints, or NetworkPolicy | Medium |
| Nothing points to a cause | Unknown — says so plainly | Low |

The engine is deliberately deterministic for the demo — same input,
same output, every time.

## Project layout

```
.
├── src/orbitronops_k8s_troubleshoot/  # the agent
│   ├── models.py                      # Symptom / CheckResult / Diagnosis
│   ├── checks.py                      # ordered diagnostic checks
│   ├── diagnose.py                    # first decisive failure wins
│   ├── runbooks.py                    # read-only commands + fix suggestions
│   └── cli.py                         # `diagnose <file>`
├── examples/                          # sample symptoms + a sample output
├── tests/                             # tests for every symptom and rule
├── docs/
│   ├── ARCHITECTURE.md                # design, check order, extension points
│   └── SECURITY.md                    # what the agent can / cannot do
├── .github/workflows/ci.yml           # lint + tests on every push
├── Dockerfile                         # run the demo in a container
└── pyproject.toml
```

## Status

**Demo — not client work.**

OrbitronOps has not yet delivered a client Kubernetes troubleshooting
agent. This repository is a working prototype built to show how we
build one: the check order, the honest unknown, and the read-only
safety rule a client would actually get.

It pairs with the [incident-triage-agent](https://github.com/orbitronops/incident-triage-agent):
triage answers "what is happening, right now?" and this agent walks
the diagnosis step by step. The
[postmortem-generator](https://github.com/orbitronops/postmortem-generator)
then writes up what happened afterwards.

If you want this wired to *your* cluster, alerts, and runbooks, talk to us:
[orbitronops.com](https://www.orbitronops.com) · [LinkedIn](https://www.linkedin.com/company/orbitronops/)

## Roadmap

- Deterministic ordered checks + read-only runbooks + fix suggestions
- Live read-only Kubernetes connector (`kubectl get/describe/logs` via API)
- More symptoms: PVC binding, DNS failures, resource quotas, HPA thrash
- Slack / PagerDuty alert ingestion
- Optional LLM explainer (pluggable, off by default, rewording only)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues and PRs welcome — please keep the read-only safety rule intact.

## License

MIT — see [LICENSE](LICENSE).
