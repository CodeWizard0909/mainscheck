# Tickets

Six tickets, in dependency order. Each is sized to fit one working session, so any of
them can be picked up cold without re-reading the others.

```
01 tracer bullet ──┐
                   ├──> 03 corpus ──┐
02 test suite ─────────────────────┴──> 04 reliability ──> 05 matrix + economics ──> 06 publish
```

| # | Ticket | Blocked by |
|---|---|---|
| 01 | Tracer bullet — one answer end to end | — |
| 02 | Offline test suite | — |
| 03 | Corpus to 30 answers | 01 |
| 04 | Reliability metrics | 02, 03 |
| 05 | Configuration matrix and economics | 04 |
| 06 | Publish | 05 |

01 and 02 can both start immediately. Start with 01: it tells you whether the design
works at all, and seeing a real number makes writing 29 more answers feel like progress
rather than a wall.

Ticket 04 carries the two gates that decide the project's shape — the control-drift
check, and the day-9 call on whether the headline is reliability or cost.
