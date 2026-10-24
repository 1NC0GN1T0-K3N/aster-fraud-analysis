# Release verification — 25 October 2026

Verification used a clean copy containing only the public release files, without the original coursework directory, generated answer keys, model binaries, environments or prior notebook outputs.

| Check | Result |
|---|---|
| Original midterm unit tests | All 12 pass |
| Midterm offline analytics | 176 raw / 169 valid / 7 quarantined claim rows; 42 alert rows |
| Midterm reconciliation | Source counts and numeric amounts balance; two invalid master records are retained in quarantine |
| Final command-line pipeline | Completes and regenerates all synthetic inputs and analytical reports |
| Final integrity/leakage checks | All 15 pass |
| Public final notebook | Every code cell executes from both repository root and `final/` |
| Figure generation | All four analytical plots render using the included portable helper |
| Test metrics | Match committed metrics and README values |
| Package environment | Python 3.12 with the core packages pinned in `final/requirements.txt` |

The main notebook source and companion helpers are included. Generated `private/`, `models/` and `notebook_run/` files are reproducible outputs, not unpublished prerequisites. The figure helper uses Matplotlib's noninteractive backend and does not depend on macOS font paths.

Notebook structure, Python syntax, JSON, local documentation links, tracked-file completeness and common credential patterns are checked before the push. The original embedded NVD credential from the separate vulnerability project is absent from these release files and their Git history.

## Limits

The optional n8n/PostgreSQL/Gemini exports have not been imported and exercised against live services in this verification. A fresh dependency download/install, Windows execution and every possible Python/Node version were not separately tested. Peer exercises and peer-review outcomes are outside the public release.
