# Profile storage: OS user-data dir, append-only unbounded history

The profile is a single JSON file in the OS user-data directory
(`~/.local/share/casino-teinte/` on Linux/macOS, `%APPDATA%\casino-teinte\` on
Windows), overridable with `CASINO_PROFILE_PATH`. It carries `schema_version`
from v1, the current `bankroll`, a `re_buys` counter, and a `history` array with
one entry per round that only ever grows. Writes happen after every round via a
temp file + `os.replace` so the file is never observed half-written.

We rejected storing the file next to the script (breaks as soon as the script is
run or moved elsewhere, risks being committed) and a dotfile in `$HOME` (works
but pollutes the home directory with mutable state).

We rejected a sliding-window history (keep the last N rounds) plus a `totals`
block of running counters. That design trades a bounded file for a class of bugs
where the counters drift out of sync with the retained rounds. At ~150 bytes per
entry, 10 000 rounds is ~1.5 MB — negligible for years of play. If the file ever
does become a problem, the sliding-window-plus-totals model is the migration to
make, and `schema_version` makes that migration explicit.

## Consequences

- All lifetime aggregates are computed by scanning `history` in full on each
  `stats` invocation; this is fine at the expected scale.
- A corrupt or unknown-version file is renamed to `.corrupt-<timestamp>` and a
  fresh profile is started, rather than aborting or overwriting silently.
- Concurrency is out of scope: two sessions writing the same file will have the
  last writer win. `os.replace` only guarantees the file is never corrupt.
