# Casino de la teinte

A terminal casino game: the player bets on a hue of the colour wheel, the house
draws a colour from quantum entropy, and the payout scales with how close the two
hues are. This context covers the game loop and the persistent player profile.

## Language

**Session**:
One run of the program, from launch to exit. A session plays a sequence of rounds
against a single profile.
_Avoid_: game, partie (in English prose)

**Round**:
One bet-and-draw cycle: the player stakes an amount on a chosen hue, the house
draws a colour, proximity is measured, and the payout is settled.
_Avoid_: turn, hand, manche (in English prose)

**Profile**:
The single, implicit, per-machine record that persists between sessions. Holds the
bankroll and the round history. There is exactly one profile per machine; named or
multi-player profiles are explicitly out of scope.
_Avoid_: account, user, save file

**Bankroll**:
The player's balance, carried across sessions in the profile. A session resumes
from the bankroll the previous session left, not from a fixed amount.
_Avoid_: solde (in English prose), funds, chips

**Re-buy**:
A house top-up that restores the bankroll to the standard starting amount when a
session begins with the bankroll below a low threshold. Each re-buy is counted in
the profile.
_Avoid_: recave (in English prose), top-up, refill, bailout

**Proximity**:
How close the player's chosen hue is to the drawn hue, as a percentage: 100% is
identical, 0% is opposite on the wheel.
_Avoid_: score, accuracy, closeness

**Round history**:
The ordered list of every round the profile has played, one entry per round.
Entries are never edited after the fact; the history only grows.
_Avoid_: log, journal, ledger

**Average proximity**:
The arithmetic mean of proximity across the profile's rounds. A skill-level
measure: how well the player picks hues.
_Avoid_: success rate, accuracy

**Win rate**:
The fraction of the profile's rounds whose net outcome was positive (payout
above stake). A luck-and-payout measure, distinct from average proximity.
_Avoid_: success rate, hit rate

**House edge**:
The payout-curve exponent that bends the odds toward the bank. An exponent of 1.0
is a fair game; above 1.0 favours the house.
_Avoid_: avantage maison (in English prose), margin, vig
