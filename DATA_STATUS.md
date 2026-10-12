# Data & rules status

I had no access to the physical game and the rule sites are blocked from the sandbox, so the
ingredient data comes from **search-result excerpts of the ultraboardgames.com almanac** (a fan site),
cross-checked against the Set 1 costs in `quacks.ipynb` (all matched). I never saw a full page. Treat
everything below as "plausible, please check against your copy" until you have.

Everything is data/config in three files: `src/quacks/books.py` (costs, flags),
`src/quacks/board.py` (track, die, rat tails) and `Rules` in `src/quacks/engine.py`.

## Ingredient books (2018, sets 1-4)

| Colour | Set 1 | Set 2 | Set 3 | Set 4 |
|---|---|---|---|---|
| Green (spider) | OK | OK | effect OK, **cost guessed** | effect OK, **cost guessed** |
| Blue (crow skull) | OK | **not implemented** (effect text unclear, cost unknown) | OK | OK |
| Red (toadstool) | OK | OK | OK | OK |
| Yellow (mandrake) | OK | OK | OK (cost from excerpt) | OK (cost from excerpt) |
| Purple (ghost's breath) | OK (see below) | OK | OK | OK |
| Orange (pumpkin) | OK, no effect, cost 3 | | | |
| Black (moth) | OK, cost 10; 2-player and 3/4-player versions chosen by player count | | | |

Sets marked "guessed"/"not implemented" are excluded from random set selection unless `--unverified`
is passed (then Blue 2 behaves as a plain chip and the guessed costs are used).

Interpretation choices that the excerpts left open:
- Purple set 1: one chip = 1 VP, two = 1 VP + ruby, three or more = 2 VP + droplet. One excerpt omitted the single-chip case.
- Yellow set 2 doubles the *whole* movement of the next chip (value + bonuses).
- Black: a bonus needs at least one black chip in your pot (otherwise 0 = 0 would reward nobody-has-any). Neighbours are the adjacent seats.
- Green set 3 triggers only when the white total is exactly 7 and moves the last chip, which changes the scoring space.
- Red set 2: set-aside red chips are placed after stopping, but not after an explosion (`Rules.aside_after_explosion`).
- Purple set 2 discards the traded purple chips for good; purple set 4 removes the old chip and adds the upgraded one to the bag.
- Chip supply limits are ignored.

## Rules

Confirmed by excerpts: 9 rounds; white total > 7 explodes; scoring space = first space after the last chip;
exploded players pick VP *or* coins; bonus die only for non-exploded players in the furthest pot (ties all roll);
phase order A bonus die, B chip actions, C rubies, D/E VP and coins, F spending; rat tails from round 2;
flask returns the last white chip (not the exploding one); 2 rubies = 1 droplet step or a flask refill; max 2 purchases.

**Unverified assumptions (please check against the rulebook):**

| Assumption | Where | Why it matters |
|---|---|---|
| Bonus die faces: 1 VP, 2 VP, ruby, orange, droplet, **+ a second ruby** (6th face unknown) | `board.DIE_FACES` | value of leading the round |
| Rat tails: one per 2 VP of difference (real tail positions on the score track unknown) | `board.RAT_TAIL_EVERY` | strength of the catch-up mechanic; shapes risk-taking when behind |
| Players start with 0 rubies, flask starts full | `Rules.start_rubies` | |
| 5 rubies = 1 VP at game end | `Rules.rubies_per_vp` | |
| The two purchased chips must differ in colour | `Rules.same_color_twice` | |
| Chip actions (green/purple/black) still resolve for an exploded pot | `Rules.chip_actions_on_explosion` | |
| Tie-break: furthest pot in the last round | `Game.result` | |
| Score/coin/ruby track arrays are exactly those from your notebook (53 spaces) | `board.py` | |
| Pot positions are capped at the last space (52) | | |

**Not implemented yet:** the 24 fortune teller cards (no reliable card list found; the engine runs
without them), and both expansions (Herb Witches, The Alchemists) - the planned second step.
