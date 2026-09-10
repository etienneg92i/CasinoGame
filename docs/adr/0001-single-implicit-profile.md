# Single implicit per-machine profile

There is exactly one profile per machine, resolved from a fixed OS path (or
`CASINO_PROFILE_PATH`), with no name prompt and no way to keep more than one.
Named or multi-player profiles were considered and deliberately rejected: they
would add a launch-time selection flow, a profile-management surface, and a
"which profile?" question to every command, for a single-user terminal toy. The
cost of adding them later is a schema migration plus a new CLI path — acceptable
if real demand appears — so we keep the scope small now.

## Consequences

- The profile schema has no `name` / `id` field; adding multi-profile support is a
  breaking schema change (hence `schema_version`).
- Two concurrent sessions share one file; last write wins (see ADR-0003).
