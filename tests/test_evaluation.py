import pytest

from quacks import board
from quacks.engine import Game, Pot, Rules
from quacks.strategies import Strategy
from tests.helpers import *  # noqa: F401,F403


def c(color, v):
    return chip(color, v)


def make_pot(chips, positions=None, start=0, wsum=None):
    pot = Pot(start, 7)
    pos = start
    for i, ch in enumerate(chips):
        pos = positions[i] if positions else pos + (ch % 5)
        pot.chips.append(ch)
        pot.spots.append(pos)
        pot.counts[ch // 5] += 1
        if ch // 5 == WHITE:
            pot.wsum += ch % 5
    pot.cur = pot.spots[-1] if pot.spots else start
    return pot


def game(sets=None, n=1, strat=None):
    return Game([strat or DrawN(0)] * n, sets or sets_of(), FixedRng(), Rules())


# ---- green
def test_green1_one_ruby_per_green_in_last_two():
    g = game(sets_of(green=1))
    p = g.players[0]
    pot = make_pot([c(G, 4), c(G, 1), c(W, 1)])  # only the second green is in the last two
    g._chip_actions(p, pot, [0], 0)
    assert p.rubies == 1
    p.rubies = 0
    pot = make_pot([c(O, 1), c(G, 2), c(G, 1)])
    g._chip_actions(p, pot, [0], 0)
    assert p.rubies == 2


def test_green2_gives_bag_chips_by_value():
    g = game(sets_of(green=2))
    p = g.players[0]
    pot = make_pot([c(G, 2), c(G, 4)])
    g._chip_actions(p, pot, [0], 0)
    assert sorted(p.pending) == sorted([c(BLUE, 1), c(YELLOW, 1)])
    p.pending.clear()
    g._chip_actions(p, make_pot([c(O, 1), c(G, 1)]), [0], 0)
    assert p.pending == [c(O, 1)]


def test_green3_exact_seven_moves_last_chip():
    g = game(sets_of(green=3))
    p = g.players[0]
    pot = make_pot([c(W, 3), c(W, 3), c(W, 1), c(G, 2), c(G, 4)])
    start_cur = pot.cur
    g._chip_actions(p, pot, [0], 0)
    assert pot.wsum == 7 and pot.cur == start_cur + 6
    pot = make_pot([c(W, 3), c(W, 3), c(G, 2)])
    cur = pot.cur
    g._chip_actions(p, pot, [0], 0)
    assert pot.cur == cur  # white total 6, no bonus


def test_green4_pays_rubies_for_droplet():
    class Pay(Strategy):
        def green4_pay(self, g, p, pot, k):
            return k

    g = game(sets_of(green=4), strat=Pay())
    p = g.players[0]
    p.rubies = 5
    g._chip_actions(p, make_pot([c(G, 1), c(G, 2)]), [0], 0)
    assert p.droplet == 2 and p.rubies == 3


# ---- purple
def test_purple1_tiers():
    g = game(sets_of(purple=1))
    p = g.players[0]
    for n, (vp, rub, drop) in {1: (1, 0, 0), 2: (1, 1, 0), 3: (2, 0, 1), 5: (2, 0, 1)}.items():
        p.vp = p.rubies = p.droplet = 0
        g._chip_actions(p, make_pot([c(P, 1)] * n), [0], 0)
        assert (p.vp, p.rubies, p.droplet) == (vp, rub, drop), n


def test_purple2_trade_in_discards_chips_and_cannot_combine():
    g = game(sets_of(purple=2), strat=DrawN(0, tier=2))
    p = g.players[0]
    pot = make_pot([c(P, 1)] * 4)
    g._chip_actions(p, pot, [0], 0)
    assert pot.counts[PURPLE] == 2  # exactly two discarded
    assert p.vp == 3 and p.droplet == 1
    assert sorted(p.pending) == sorted([c(G, 1), c(B, 2)])


def test_purple3_scores_by_position():
    g = game(sets_of(purple=3))
    p = g.players[0]
    pot = make_pot([c(P, 1), c(P, 1), c(P, 1), c(P, 1)], positions=[9, 10, 25, 31])
    g._chip_actions(p, pot, [0], 0)
    assert p.vp == 0 + 1 + 2 + 3


def test_purple4_upgrades_into_the_bag():
    class First(Strategy):
        def upgrade_choice(self, g, p, pot, cand, to):
            return cand[0]

    g = game(sets_of(purple=4), strat=First())
    p = g.players[0]
    pot = make_pot([c(R, 1), c(P, 1)])
    g._chip_actions(p, pot, [0], 0)
    assert c(R, 2) in p.pending and c(R, 1) not in pot.chips
    p.pending.clear()
    pot = make_pot([c(R, 1), c(P, 1), c(P, 1), c(P, 1)])  # three purples: 1 -> 4
    g._chip_actions(p, pot, [0], 0)
    assert p.pending == [c(R, 4)]


# ---- black
@pytest.mark.parametrize("blacks,expect", [
    ([2, 1, 0, 0], (1, 1)),  # more than both neighbours (seat 1 and seat 3): droplet + ruby
    ([2, 1, 0, 3], (1, 0)),  # more than the left neighbour only: droplet
    ([1, 1, 0, 3], (0, 0)),  # not more than either neighbour
])
def test_black_neighbours(blacks, expect):
    g = game(n=4)
    p = g.players[0]
    g._chip_actions(p, make_pot([c(K, 1)] * blacks[0]), blacks, 0)
    assert (p.droplet, p.rubies) == expect


def test_black_two_players():
    g = game(n=2)
    p = g.players[0]
    g._chip_actions(p, make_pot([c(K, 1)] * 2), [2, 1], 0)
    assert (p.droplet, p.rubies) == (1, 1)
    p.droplet = p.rubies = 0
    g._chip_actions(p, make_pot([c(K, 1)] * 2), [2, 2], 0)
    assert (p.droplet, p.rubies) == (1, 0)


# ---- rounds / scoring
class Buyer(Strategy):
    def __init__(self, picks):
        self.picks = picks

    def buy(self, g, p, coins):
        return self.picks

    def should_draw(self, g, p, pot):
        return False


def test_empty_pot_scores_first_space():
    g = Game([Buyer([])], sets_of(), FixedRng(die="ruby"), Rules(n_rounds=1))
    g.run()
    assert g.players[0].vp == board.VP[1] and g.players[0].last_cur == 0


def test_exploded_player_chooses_vp_or_coins():
    class Boom(Strategy):
        def should_draw(self, g, p, pot):
            return True

        def explosion_choice(self, g, p, pot, vp, coins):
            return "vp"

    g = Game([Boom()], sets_of(), FixedRng(), Rules(n_rounds=1))
    p = g.players[0]
    p.bag = [c(W, 3), c(W, 3), c(W, 2)]
    g.run()
    assert p.vp == board.VP[9] and p.pending == []


def test_buy_validation():
    g = game()
    p = g.players[0]
    with pytest.raises(ValueError):
        g.players[0].strategy = Buyer([c(R, 4)])
        g._buy(p, 10)  # cannot afford (16)
    p.strategy = Buyer([c(R, 1), c(R, 2)])
    with pytest.raises(ValueError):
        g._buy(p, 100)  # same colour twice
    p.strategy = Buyer([c(R, 1), c(G, 1), c(G, 2)])
    with pytest.raises(ValueError):
        g._buy(p, 100)  # three chips
    p.strategy = Buyer([c(R, 1), c(G, 1)])
    g._buy(p, 10)
    assert p.pending == [c(R, 1), c(G, 1)]


def test_bonus_die_only_for_furthest_unexploded_pot():
    class Draw3(Strategy):
        def should_draw(self, g, p, pot):
            return pot.drawn < 1

    g = Game([Draw3(), Draw3()], sets_of(), FixedRng(die="vp2"), Rules(n_rounds=1))
    g.players[0].bag = [c(O, 1)] + [c(W, 1)] * 3
    g.players[1].bag = [c(G, 4)] + [c(W, 1)] * 3
    g.run()
    # player 1 is furthest (space 4 vs 1) and gets the die; also green1 ruby irrelevant here
    assert g.players[1].vp == board.VP[5] + 2
    assert g.players[0].vp == board.VP[2]


def test_rat_tails_head_start_from_round_two():
    g = Game([Buyer([]), Buyer([])], sets_of(), FixedRng(), Rules(n_rounds=2))
    g.players[0].vp = 10
    seen = {}
    orig = g._brew

    def spy(p, start):
        seen.setdefault(p.seat, []).append(start)
        return orig(p, start)

    g._brew = spy
    g._round(1)
    g.round = 2
    g.players[1].vp = 0
    g.players[0].vp = 10
    g._round(2)
    assert seen[1][0] == 0 and seen[1][1] == board.rat_tails_between(0, 10) and seen[0][1] == 0


def test_end_of_game_rubies_convert_and_tiebreak():
    g = Game([Buyer([]), Buyer([])], sets_of(), FixedRng(), Rules(n_rounds=1))
    a, b = g.players
    a.vp, a.rubies = 10, 5
    b.vp, b.rubies = 11, 0
    a.last_cur, b.last_cur = 3, 9
    r = g.result()
    assert r["players"][0]["final"] == 11 and r["winners"] == [1]  # tie on 11 -> further pot wins
