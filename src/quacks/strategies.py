"""Decision policies.

A ``Strategy`` answers every question the engine asks. ``ParamStrategy`` is a fully parametric policy
(a flat parameter vector) that the optimiser in optimize.py tunes; the named presets are hand-written
baselines in the spirit of the original notebooks ("Schisser" = cautious).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import board
from .chips import BLACK, BLUE, COLOR_OF, GREEN, ORANGE, PURPLE, RED, VALUE_OF, WHITE, YELLOW, chip

# Chip types a player can ever buy (set-independent). The set only changes cost and effect.
BUY_TYPES = tuple(
    [chip(c, v) for c in (GREEN, BLUE, RED, YELLOW) for v in (1, 2, 4)]
    + [chip(PURPLE, 1), chip(BLACK, 1), chip(ORANGE, 1)]
)
BUY_INDEX = {c: i for i, c in enumerate(BUY_TYPES)}
N_BUY = len(BUY_TYPES)

# theta layout
I_RISK_EARLY, I_RISK_LATE, I_FLASK, I_EXPL_COINS, I_DROP_UNTIL, I_SCORE0 = range(6)
N_THETA = I_SCORE0 + 2 * N_BUY  # (base, slope) per buyable chip type


class Strategy:
    """Default (conservative) behaviour; subclasses override what they care about."""

    name = "base"

    # -- brewing
    def should_draw(self, g, p, pot) -> bool:
        return pot.explode_risk(p.bag) <= 0.0

    def use_flask(self, g, p, pot) -> bool:
        return pot.wsum >= 5

    def blue_choice(self, g, p, pot, options) -> int:
        """Crow skull set 1: pick the best non-exploding chip (largest value), or -1 for none."""
        room = pot.limit - pot.wsum
        best, best_k = 0, -1
        for k, c in enumerate(options):
            v = VALUE_OF[c]
            if COLOR_OF[c] == WHITE and v > room:
                continue
            score = v + (0.5 if COLOR_OF[c] != WHITE else 0.0)
            if score > best:
                best, best_k = score, k
        return best_k

    # -- evaluation
    def explosion_choice(self, g, p, pot, vp, coins) -> str:
        return "coins" if coins >= 12 else "vp"

    def buy(self, g, p, coins) -> list:
        return []

    def spend_rubies(self, g, p):
        return p.rubies // 2, (not p.flask)

    def green4_pay(self, g, p, pot, k) -> int:
        return k

    def purple2_tier(self, g, p, pot, max_tier) -> int:
        return max_tier

    def green2_choice(self, g, p, options) -> int:
        return options[0]

    def upgrade_choice(self, g, p, pot, candidates, to_value):
        """Index into pot.chips to upgrade; prefer the chip of the colour we value most."""
        return max(candidates, key=lambda j: _color_rank(COLOR_OF[pot.chips[j]]))


_RANK = {YELLOW: 4, BLUE: 3, RED: 2, GREEN: 1}


def _color_rank(color: int) -> int:
    return _RANK.get(color, 0)


@dataclass
class ParamStrategy(Strategy):
    theta: list = field(default_factory=list)
    label: str = "param"

    def __post_init__(self):
        if not self.theta:
            self.theta = default_theta()
        self.name = self.label

    # -- helpers
    def _frac(self, g) -> float:
        n = g.rules.n_rounds
        return (g.round - 1) / (n - 1) if n > 1 else 0.0

    def _risk_cap(self, g) -> float:
        t = self.theta
        f = self._frac(g)
        return t[I_RISK_EARLY] + (t[I_RISK_LATE] - t[I_RISK_EARLY]) * f

    def score(self, g, idx: int) -> float:
        t = self.theta
        return t[I_SCORE0 + 2 * idx] + t[I_SCORE0 + 2 * idx + 1] * self._frac(g)

    # -- brewing
    def should_draw(self, g, p, pot) -> bool:
        return pot.explode_risk(p.bag) <= self._risk_cap(g)

    def use_flask(self, g, p, pot) -> bool:
        return pot.wsum >= self.theta[I_FLASK]

    # -- evaluation
    def explosion_choice(self, g, p, pot, vp, coins) -> str:
        return "coins" if coins >= self.theta[I_EXPL_COINS] else "vp"

    def buy(self, g, p, coins) -> list:
        cands = []
        for c, cost, color in g.catalog:
            if cost <= coins:
                s = self.score(g, BUY_INDEX[c])
                if s > 0:
                    cands.append((s, cost, c, color))
        if not cands:
            return []
        cands.sort(key=lambda t: (-t[0], -t[1]))
        first = cands[0]
        picks = [first[2]]
        left = coins - first[1]
        if g.rules.max_buys >= 2:
            for s, cost, c, color in cands[1:]:
                if cost <= left and (color != first[3] or g.rules.same_color_twice):
                    picks.append(c)
                    break
        return picks

    def spend_rubies(self, g, p):
        if g.round > self.theta[I_DROP_UNTIL]:
            return 0, (not p.flask)
        return p.rubies // 2, (not p.flask)

    def green4_pay(self, g, p, pot, k) -> int:
        return k if g.round <= self.theta[I_DROP_UNTIL] else 0


def default_theta() -> list:
    """Moderate risk, buy the most expensive useful chips (score ~ cost)."""
    t = [0.0] * N_THETA
    t[I_RISK_EARLY], t[I_RISK_LATE] = 0.15, 0.15
    t[I_FLASK] = 5.0
    t[I_EXPL_COINS] = 12.0
    t[I_DROP_UNTIL] = 8.0
    cost_guess = {1: 6, 2: 10, 4: 16}
    for i, c in enumerate(BUY_TYPES):
        color = COLOR_OF[c]
        if color == ORANGE:
            s = 1.0
        elif color == PURPLE:
            s = 9.0
        elif color == BLACK:
            s = 8.0
        else:
            s = float(cost_guess[VALUE_OF[c]])
        t[I_SCORE0 + 2 * i] = s
    return t


def preset(name: str) -> ParamStrategy:
    t = default_theta()
    if name == "cautious":  # never takes any explosion risk (the notebooks' "Schisser")
        t[I_RISK_EARLY] = t[I_RISK_LATE] = 0.0
    elif name == "moderate":
        t[I_RISK_EARLY] = t[I_RISK_LATE] = 0.15
    elif name == "gambler":
        t[I_RISK_EARLY] = t[I_RISK_LATE] = 0.35
    elif name == "ramp":  # careful early, bolder late
        t[I_RISK_EARLY], t[I_RISK_LATE] = 0.05, 0.3
    else:
        raise KeyError(name)
    return ParamStrategy(theta=t, label=name)


PRESETS = ("cautious", "moderate", "gambler", "ramp")
