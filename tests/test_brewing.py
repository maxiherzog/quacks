from quacks import board
from tests.helpers import *  # noqa: F401,F403


def c(color, v):
    return chip(color, v)


def test_pot_explodes_above_seven_not_at_seven():
    _, _, pot = brew([c(W, 3), c(W, 3), c(W, 1)])
    assert pot.wsum == 7 and not pot.exploded
    _, _, pot = brew([c(W, 3), c(W, 3), c(W, 2)])
    assert pot.wsum == 8 and pot.exploded
    assert pot.cur == 8  # the exploding chip is placed


def test_no_more_draws_after_explosion():
    _, p, pot = brew([c(W, 3), c(W, 3), c(W, 2), c(W, 1)], n=10)
    assert pot.exploded and len(pot.chips) == 3 and len(p.bag) == 1


def test_positions_follow_values():
    _, _, pot = brew([c(O, 1), c(G, 4), c(W, 2)])
    assert pot.spots == [1, 5, 7]


def test_start_offset_from_droplet_or_rat():
    _, _, pot = brew([c(W, 1)], start=4)
    assert pot.spots == [5]


def test_position_is_capped_at_track_end():
    _, _, pot = brew([c(R, 4)] * 3, start=board.TRACK_END - 2)
    assert pot.cur == board.TRACK_END


# ---- red
def test_red1_orange_bonus():
    sets = sets_of(red=1)
    _, _, pot = brew([c(R, 1)], sets=sets)
    assert pot.cur == 1  # no orange
    _, _, pot = brew([c(O, 1), c(R, 1)], sets=sets)
    assert pot.spots == [1, 3]  # one orange: +1
    _, _, pot = brew([c(O, 1)] * 3 + [c(R, 1)], sets=sets)
    assert pot.spots[-1] == 3 + 1 + 2  # three oranges: +2


def test_red2_is_placed_after_stopping():
    _, _, pot = brew([c(R, 2), c(W, 1), c(W, 1)], sets=sets_of(red=2), n=3)
    assert pot.spots == [1, 2, 4]  # red lands after the last chip


def test_red2_lost_on_explosion():
    _, p, pot = brew([c(R, 2), c(W, 3), c(W, 3), c(W, 2)], sets=sets_of(red=2), n=4)
    assert pot.exploded and pot.counts[RED] == 0


def test_red3_after_white():
    sets = sets_of(red=3)
    _, _, pot = brew([c(W, 2), c(R, 1)], sets=sets)
    assert pot.spots == [2, 5]  # 2 + (1 + 2)
    _, _, pot = brew([c(O, 1), c(R, 1)], sets=sets)
    assert pot.spots == [1, 2]


def test_red4_doubles_later_white_ones_only():
    sets = sets_of(red=4)
    _, _, pot = brew([c(W, 1), c(R, 1), c(W, 1), c(W, 2)], sets=sets)
    assert pot.spots == [1, 2, 4, 6]
    assert pot.wsum == 4  # explosion counting is unaffected


# ---- yellow
def test_yellow1_returns_previous_white_and_keeps_space():
    _, p, pot = brew([c(W, 2), c(Y, 1)], sets=sets_of(yellow=1))
    assert pot.spots == [3] and pot.chips == [c(Y, 1)]
    assert pot.wsum == 0 and c(W, 2) in p.bag


def test_yellow1_needs_white_before_it():
    _, _, pot = brew([c(O, 1), c(Y, 1)], sets=sets_of(yellow=1))
    assert pot.spots == [1, 2]


def test_yellow2_doubles_next_chip():
    _, _, pot = brew([c(Y, 1), c(W, 3), c(O, 1)], sets=sets_of(yellow=2))
    assert pot.spots == [1, 7, 8] and pot.wsum == 3


def test_yellow3_raises_explosion_limit():
    bag = [c(Y, 1), c(W, 3), c(W, 3), c(W, 2)]
    _, _, pot = brew(bag, sets=sets_of(yellow=3))
    assert pot.limit == 8 and pot.wsum == 8 and not pot.exploded
    _, _, pot = brew(bag, sets=sets_of(yellow=1))
    assert pot.exploded


def test_yellow3_limit_nine_after_three_yellows():
    _, _, pot = brew([c(Y, 1)] * 3, sets=sets_of(yellow=3))
    assert pot.limit == 9


def test_yellow4_bonus_for_first_three():
    _, _, pot = brew([c(Y, 1)] * 4, sets=sets_of(yellow=4))
    assert pot.spots == [2, 5, 9, 10]


# ---- blue
def test_blue3_ruby_on_ruby_space():
    g, p, pot = brew([c(W, 3), c(B, 2)], sets=sets_of(blue=3))
    assert pot.spots == [3, 5] and board.RUBIES[5] == 1 and p.rubies == 1
    g, p, pot = brew([c(W, 3), c(B, 1)], sets=sets_of(blue=3))
    assert p.rubies == 0


def test_blue4_victory_points_equal_value_on_ruby_space():
    g, p, pot = brew([c(W, 3), c(B, 2)], sets=sets_of(blue=4))
    assert p.vp == 2


def test_blue1_draws_value_chips_and_places_chosen_one():
    # blue2 placed, then the next two chips (O1, G4) are shown; choose index 1 (green4)
    g, p, pot = brew([c(B, 2), c(O, 1), c(G, 4), c(W, 1)], n=1, sets=sets_of(blue=1),
                     strategy=DrawN(1, blue=1))
    assert pot.chips == [c(B, 2), c(G, 4)] and pot.spots == [2, 6]
    assert sorted(p.bag) == sorted([c(O, 1), c(W, 1)])


def test_blue1_can_decline():
    g, p, pot = brew([c(B, 1), c(W, 3)], n=1, sets=sets_of(blue=1), strategy=DrawN(1, blue=-1))
    assert pot.chips == [c(B, 1)] and p.bag == [c(W, 3)]


# ---- flask
def test_flask_returns_last_white_chip():
    g, p, pot = brew([c(O, 1), c(W, 3), c(W, 1)], strategy=DrawN(2, flask_after=2))
    assert pot.chips == [c(O, 1)] and pot.cur == 1 and pot.wsum == 0
    assert not p.flask and c(W, 3) in p.bag


def test_flask_not_usable_when_last_chip_not_white():
    g, p, pot = brew([c(W, 3), c(O, 1)], strategy=DrawN(2, flask_after=2))
    assert p.flask and len(pot.chips) == 2
