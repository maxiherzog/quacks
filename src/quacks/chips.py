"""Chip identities.

A chip is a small integer ``color * 5 + value`` so that the hot simulation loop never has to touch
objects. ``COLOR_OF`` / ``VALUE_OF`` decode it.
"""

WHITE, ORANGE, GREEN, BLUE, RED, YELLOW, PURPLE, BLACK = range(8)
COLOR_NAMES = ("white", "orange", "green", "blue", "red", "yellow", "purple", "black")
N_COLORS = len(COLOR_NAMES)

_STRIDE = 5  # values are 1..4

COLOR_OF = tuple(i // _STRIDE for i in range(N_COLORS * _STRIDE))
VALUE_OF = tuple(i % _STRIDE for i in range(N_COLORS * _STRIDE))


def chip(color: int, value: int) -> int:
    return color * _STRIDE + value


def chip_name(c: int) -> str:
    return f"{COLOR_NAMES[COLOR_OF[c]]}{VALUE_OF[c]}"


# Starting bag of every player (base game).
STARTER_BAG = (
    [chip(WHITE, 1)] * 4
    + [chip(WHITE, 2)] * 2
    + [chip(WHITE, 3)]
    + [chip(ORANGE, 1)]
    + [chip(GREEN, 1)]
)
