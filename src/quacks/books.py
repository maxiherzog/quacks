"""Ingredient books (the 'almanac').

Every colour except orange has four sets (1-4); one set per colour is in play in a given game.
``cost_ok`` / ``effect_ok`` say whether we have a source for the numbers (see DATA_STATUS.md).
``implemented`` says whether the engine implements the effect. Sets that are not fully known are
excluded from random set selection unless ``include_unverified=True``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .chips import BLACK, BLUE, GREEN, ORANGE, PURPLE, RED, YELLOW


@dataclass(frozen=True)
class Book:
    color: int
    set_no: int
    costs: dict  # value -> coins
    cost_ok: bool = True
    effect_ok: bool = True
    implemented: bool = True
    note: str = ""

    @property
    def verified(self) -> bool:
        return self.cost_ok and self.effect_ok and self.implemented


def _b(color, set_no, costs, **kw):
    return (color, set_no), Book(color, set_no, costs, **kw)


BOOKS: dict = dict(
    [
        # Orange (pumpkin) and black (moth) have a single book each (moth: 2-player / 3-4-player side).
        _b(ORANGE, 1, {1: 3}),
        _b(BLACK, 1, {1: 10}),
        # Garden spider
        _b(GREEN, 1, {1: 4, 2: 8, 4: 14}),
        _b(GREEN, 2, {1: 6, 2: 11, 4: 18}),
        _b(GREEN, 3, {1: 4, 2: 8, 4: 14}, cost_ok=False, note="effect known, cost unknown (set-1 cost assumed)"),
        _b(GREEN, 4, {1: 4, 2: 8, 4: 14}, cost_ok=False, note="effect known, cost unknown (set-1 cost assumed)"),
        # Crow skull
        _b(BLUE, 1, {1: 5, 2: 10, 4: 19}),
        _b(BLUE, 2, {1: 5, 2: 10, 4: 19}, cost_ok=False, effect_ok=False, implemented=False,
           note="effect text not understood; behaves as a vanilla chip if forced"),
        _b(BLUE, 3, {1: 4, 2: 8, 4: 14}),
        _b(BLUE, 4, {1: 5, 2: 10, 4: 20}),
        # Toadstool
        _b(RED, 1, {1: 6, 2: 10, 4: 16}),
        _b(RED, 2, {1: 4, 2: 8, 4: 14}),
        _b(RED, 3, {1: 5, 2: 9, 4: 15}),
        _b(RED, 4, {1: 7, 2: 11, 4: 17}),
        # Mandrake
        _b(YELLOW, 1, {1: 8, 2: 12, 4: 18}),
        _b(YELLOW, 2, {1: 9, 2: 13, 4: 19}),
        _b(YELLOW, 3, {1: 8, 2: 12, 4: 18}),
        _b(YELLOW, 4, {1: 8, 2: 12, 4: 18}),
        # Ghost's breath
        _b(PURPLE, 1, {1: 9}),
        _b(PURPLE, 2, {1: 12}),
        _b(PURPLE, 3, {1: 10}),
        _b(PURPLE, 4, {1: 11}),
    ]
)

SET_COLORS = (GREEN, BLUE, RED, YELLOW, PURPLE)


def available_sets(color: int, include_unverified: bool = False) -> list:
    return [s for (c, s), b in sorted(BOOKS.items()) if c == color and (include_unverified or b.verified)]


def cost(color: int, set_no: int, value: int) -> int:
    return BOOKS[(color, set_no)].costs[value]
