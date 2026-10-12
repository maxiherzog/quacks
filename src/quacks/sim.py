"""Batch simulation: many games, seat shuffling, optional multiprocessing."""

from __future__ import annotations

import math
import random
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field

from .books import SET_COLORS, available_sets
from .chips import BLACK, ORANGE
from .engine import Game, Rules


def sample_sets(rng: random.Random, include_unverified: bool = False, fixed: dict | None = None) -> tuple:
    """Pick one set per colour. ``fixed`` maps colour -> set number for colours that should not vary."""
    sets = [0] * 8
    sets[ORANGE] = 1
    sets[BLACK] = 1
    for c in SET_COLORS:
        if fixed and c in fixed:
            sets[c] = fixed[c]
        else:
            sets[c] = rng.choice(available_sets(c, include_unverified))
    return tuple(sets)


@dataclass
class SeatStats:
    games: int = 0
    wins: float = 0.0  # ties split
    sum_final: float = 0.0
    sum_sq: float = 0.0
    explosions: int = 0

    def merge(self, o: "SeatStats"):
        self.games += o.games
        self.wins += o.wins
        self.sum_final += o.sum_final
        self.sum_sq += o.sum_sq
        self.explosions += o.explosions

    @property
    def win_rate(self) -> float:
        return self.wins / self.games if self.games else 0.0

    @property
    def mean(self) -> float:
        return self.sum_final / self.games if self.games else 0.0

    @property
    def std(self) -> float:
        if self.games < 2:
            return 0.0
        return math.sqrt(max(0.0, self.sum_sq / self.games - self.mean ** 2))

    @property
    def win_se(self) -> float:
        p = self.win_rate
        return math.sqrt(p * (1 - p) / self.games) if self.games else 0.0


def play_one(strats, rng, sets=None, include_unverified=False, rules=None, fixed_sets=None, shuffle=True):
    """Play one game. Returns (finals, win_share, explosions, sets) indexed like ``strats``."""
    m = len(strats)
    perm = list(range(m))
    if shuffle:
        rng.shuffle(perm)
    use_sets = sets if sets is not None else sample_sets(rng, include_unverified, fixed_sets)
    g = Game([strats[perm[j]] for j in range(m)], use_sets, rng, rules)
    res = g.run()
    finals = [0] * m
    share = [0.0] * m
    expl = [0] * m
    w = res["winners"]
    for seat in range(m):
        k = perm[seat]
        finals[k] = res["players"][seat]["final"]
        expl[k] = g.players[seat].explosions
        if seat in w:
            share[k] = 1.0 / len(w)
    return finals, share, expl, use_sets


def _chunk(args):
    strats, n, seed, by_set, kw = args
    rng = random.Random(seed)
    stats = [SeatStats() for _ in strats]
    groups: dict = {}
    for _ in range(n):
        finals, share, expl, used = play_one(strats, rng, **kw)
        for k in range(len(strats)):
            s = stats[k]
            s.games += 1
            s.wins += share[k]
            s.sum_final += finals[k]
            s.sum_sq += finals[k] ** 2
            s.explosions += expl[k]
        if by_set:
            for color in SET_COLORS:
                for k in range(len(strats)):
                    groups.setdefault((k, color, used[color]), SeatStats()).merge(
                        SeatStats(1, share[k], finals[k], finals[k] ** 2, expl[k]))
    return stats, groups


def run_games(strats, n_games: int, seed: int = 0, workers: int = 1, by_set: bool = False, **kw):
    """Simulate ``n_games`` games with the given seat strategies. Returns a SeatStats per entry of ``strats``
    (and, with ``by_set=True``, additionally a dict (seat_index, colour, set) -> SeatStats).

    kw: sets (fixed tuple), include_unverified, rules, fixed_sets, shuffle.
    """
    if workers <= 1 or n_games < 2 * workers:
        stats, groups = _chunk((strats, n_games, seed, by_set, kw))
        return (stats, groups) if by_set else stats
    per = n_games // workers
    jobs = []
    for w in range(workers):
        n = per + (n_games - per * workers if w == workers - 1 else 0)
        jobs.append((strats, n, seed * 7919 + w + 1, by_set, kw))
    total = [SeatStats() for _ in strats]
    groups_total: dict = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for part, groups in ex.map(_chunk, jobs):
            for t, s in zip(total, part):
                t.merge(s)
            for key, v in groups.items():
                groups_total.setdefault(key, SeatStats()).merge(v)
    return (total, groups_total) if by_set else total
