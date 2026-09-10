# Re-buy instead of permanent bust

When a session starts with the bankroll below 10 €, the house tops it back up to
the standard 1000 € and increments a `re_buys` counter in the profile. A player
can never be permanently locked out.

We considered a hard bust (0 € ends the profile forever) and an unconditional
top-up to 1000 € every session. Hard bust punishes a casual player far too
harshly for a terminal game and would need a manual reset path anyway.
Unconditional top-up erases the meaning of a persistent bankroll — there would be
no reason to store it. A tracked re-buy keeps the stakes real within a session
(running out mid-session still ends that session) while letting the player come
back the next time they launch the game.

## Consequences

- `bankroll` must be stored explicitly: a re-buy sets it *to* 1000 € from an
  arbitrary low value, so it cannot be reconstructed from round history alone.
- Re-buys are house money injected outside of play; they are counted separately
  and excluded from lifetime net (which sums round `net` only).
- Running out of money mid-session still ends the session with the existing
  "Solde épuisé" message; the re-buy only happens at the next launch.
