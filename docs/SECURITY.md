# Security

## What this agent can do

- Read a symptom JSON file you give it.
- Print a diagnosis, read-only commands, and a fix suggestion.

## What it cannot do

- It never talks to a cluster, an API, or the network. There are no
  credentials in the code and no live calls anywhere.
- It never executes anything. `action_executed` is always `False`.
  The fix suggestion is prose for a human to review.
- Its commands are read-only only: `kubectl get`, `describe`, `logs`,
  `top`. The test `test_no_mutating_commands_anywhere` enforces this
  over the whole `src/` tree.

## What to check before trusting a diagnosis

- The diagnosis is only as good as the symptom file. A missing field
  is reported as inconclusive, never silently assumed.
- A low-confidence "Unknown" result means "gather more evidence",
  not "everything is fine". Run `kubectl describe`, `logs`, and
  `events` and re-run the diagnosis with the fuller picture.
- Never paste real credentials, tokens, or secrets into a symptom
  file. The examples use fictional services and registries.
