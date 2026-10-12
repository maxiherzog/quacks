from quacks import board
from quacks.chips import BLACK, BLUE, GREEN, ORANGE, PURPLE, RED, WHITE, YELLOW, chip
from quacks.engine import Game, Rules
from quacks.strategies import Strategy

W, O, G, B, R, Y, P, K = WHITE, ORANGE, GREEN, BLUE, RED, YELLOW, PURPLE, BLACK


class FixedRng:
    """Always draws the first chip of the bag, so bag order == draw order."""

    def __init__(self, die=None):
        self.die = die

    def randrange(self, n):
        return 0

    def choice(self, seq):
        return self.die if self.die is not None else seq[0]

    def random(self):
        return 0.0


class DrawN(Strategy):
    """Draws exactly ``n`` chips (or until the bag is empty / the pot explodes); never uses the flask."""

    def __init__(self, n, flask_after=None, **kw):
        self.n = n
        self.flask_after = flask_after  # use the flask when the pot holds this many chips
        self.kw = kw

    def should_draw(self, g, p, pot):
        return pot.drawn < self.n

    def use_flask(self, g, p, pot):
        return self.flask_after is not None and pot.drawn == self.flask_after

    def blue_choice(self, g, p, pot, options):
        return self.kw.get("blue", -1)

    def purple2_tier(self, g, p, pot, max_tier):
        return self.kw.get("tier", max_tier)


def sets_of(green=1, blue=1, red=1, yellow=1, purple=1):
    s = [0] * 8
    s[ORANGE] = 1
    s[BLACK] = 1
    s[GREEN], s[BLUE], s[RED], s[YELLOW], s[PURPLE] = green, blue, red, yellow, purple
    return tuple(s)


def brew(bag, n=None, sets=None, start=0, strategy=None, n_players=1, rules=None, die=None):
    """Brew one pot from a fixed bag order. Returns (game, player, pot)."""
    strat = strategy or DrawN(n if n is not None else len(bag))
    g = Game([strat] * n_players, sets or sets_of(), FixedRng(die), rules)
    p = g.players[0]
    p.bag = list(bag)
    pot = g._brew(p, start)
    return g, p, pot
