import itertools
import random

from quacks.books import SET_COLORS, available_sets
from quacks.chips import COLOR_OF, BLACK
from quacks.engine import Game
from quacks.sim import sample_sets
from quacks.strategies import PRESETS, preset


def test_every_implemented_set_combination_plays_without_error():
    rng = random.Random(0)
    for color in SET_COLORS:
        for s in available_sets(color, include_unverified=False):
            fixed = {color: s}
            for name in PRESETS:
                sets = sample_sets(rng, fixed=fixed)
                g = Game([preset(name)] * 4, sets, rng)
                res = g.run()
                assert res["winners"]


def test_unverified_sets_also_run():
    rng = random.Random(1)
    for _ in range(200):
        sets = sample_sets(rng, include_unverified=True)
        g = Game([preset(n) for n in ("moderate", "gambler")] * 2, sets, rng)
        g.run()


def test_chip_conservation_and_bounds():
    rng = random.Random(2)
    for _ in range(100):
        g = Game([preset("gambler")] * 3, sample_sets(rng), rng)
        g.run()
        for p in g.players:
            assert all(COLOR_OF[c] != 8 for c in p.bag)
            assert len(p.bag) >= 8  # chips are only ever added to a bag (barring purple trades), never lost
            assert 0 <= p.droplet <= 52 and p.rubies >= 0 and p.pending == []
