"""CLI: python -m orbitronops_k8s_troubleshoot diagnose <symptom.json> [--format json]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from a checkout without installing: `src` on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orbitronops_k8s_troubleshoot.diagnose import diagnose  # noqa: E402
from orbitronops_k8s_troubleshoot.models import Symptom  # noqa: E402


def _render_text(result) -> str:
    lines = [
        f"Service: {result.service}  ·  Severity: {result.severity}  ·  Confidence: {result.confidence:.2f}",
        f"Probable cause: {result.probable_cause}",
        "",
        "Checks (in order):",
    ]
    for c in result.checks:
        mark = {"pass": "ok  ", "fail": "FAIL", "inconclusive": "??  "}[c.outcome]
        lines.append(f"  [{mark}] {c.name}: {c.evidence}")
    lines += ["", "Signals:"]
    lines += [f"  - {s}" for s in result.signals]
    lines += ["", "Next steps (read-only):"]
    lines += [f"  {i}. {cmd}" for i, cmd in enumerate(result.read_only_commands, 1)]
    lines += [
        "",
        f"Fix suggestion (for a human to review, NOT executed): {result.fix_suggestion}",
        "",
        "Human approval: REQUIRED — no action was executed.",
        "This agent is read-only by design. See docs/SECURITY.md.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="orbitronops-k8s-troubleshoot",
        description="Read-only Kubernetes troubleshooting agent (OrbitronOps demo).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    diag = sub.add_parser("diagnose", help="Diagnose one symptom JSON file.")
    diag.add_argument("file", help="Path to a symptom JSON file. See examples/.")
    diag.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)

    if args.command == "diagnose":
        try:
            data = json.loads(Path(args.file).read_text(encoding="utf-8"))
        except FileNotFoundError:
            print(f"error: file not found: {args.file}", file=sys.stderr)
            return 2
        except json.JSONDecodeError as exc:
            print(f"error: invalid JSON in {args.file}: {exc}", file=sys.stderr)
            return 2

        result = diagnose(Symptom.from_dict(data))
        if args.format == "json":
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(_render_text(result))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
