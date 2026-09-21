# Issue tracker: Local Markdown

Issues for this repo live as tracked markdown files in `tickets/`.

This repo has no git remote yet. Ticket 06 creates a public GitHub repository; re-run
`/setup-matt-pocock-skills` after that if you want to move issues to GitHub Issues.

## Conventions

This repo is a single piece of work, so tickets sit flat in `tickets/` rather than
under a per-feature directory.

- One file per ticket at `tickets/<NN>-<slug>.md`, numbered from `01` in dependency
  order, never a single combined tickets file
- `tickets/README.md` carries the dependency graph and the summary table
- Blocking edges are a `**Blocked by:**` line near the top, naming ticket numbers, or
  "None (can start immediately)"
- Triage state is a `**Status:**` line near the top (see `triage-labels.md` for the
  role strings)
- Acceptance criteria are `- [ ]` checkboxes in the body
- Comments and conversation history append to the bottom under a `## Comments` heading
- Tickets are committed to git, not treated as scratch

## Where the spec lives

**Not in this repo.** The product requirements document is a Claude doc, not a local
file. A skill instructed to "fetch the relevant spec" should ask the user for the link
rather than looking for `spec.md`.

The repo does hold two spec-adjacent documents, both gitignored as private working
notes under `research/`: the build spec and the target dossiers.

## When a skill says "publish to the issue tracker"

Create a new file at `tickets/<NN>-<slug>.md`, taking the next free number in
dependency order, and add a row to `tickets/README.md`.

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the
ticket number directly.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `tickets/README.md` (the Notes / Decisions-so-far / Fog body).
- **Child ticket**: `tickets/<NN>-<slug>.md`, numbered from `01`, with the question in
  the body. A `Type:` line records the ticket type (`research`/`prototype`/`grilling`/
  `task`); a `Status:` line records `claimed`/`resolved`.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when
  every file it lists is `resolved`.
- **Frontier**: scan `tickets/` for files that are open, unblocked, and unclaimed;
  first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`,
  then append a context pointer (gist + link) to the Decisions-so-far in
  `tickets/README.md`.
