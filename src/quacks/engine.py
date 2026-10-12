"""Game engine for The Quacks of Quedlinburg (2018 base game).

The engine only knows the rules; every decision (draw/stop, flask, buying, ...) is delegated to a
``Strategy`` (see strategies.py). Chip effects are implemented per (colour, set) in ``_play`` (when a
chip is drawn) and ``_chip_actions`` (evaluation phase B).

Rules encoded here that are NOT backed by a source are listed in DATA_STATUS.md.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from . import board
from .books import BOOKS
from .chips import (BLACK, BLUE, COLOR_OF, GREEN, ORANGE, PURPLE, RED, STARTER_BAG, VALUE_OF, WHITE, YELLOW,
                    chip)

TRACK_END = board.TRACK_END


@dataclass
class Rules:
    n_rounds: int = 9
    explosion_limit: int = 7  # pot explodes when the white total is strictly greater
    start_rubies: int = 0  # UNVERIFIED
    rubies_per_vp: int = 5  # final conversion, UNVERIFIED
    ruby_cost: int = 2  # per droplet step / flask refill
    max_buys: int = 2
    same_color_twice: bool = False  # UNVERIFIED: may both bought chips share a colour?
    die_faces: tuple = board.DIE_FACES
    use_rat_tails: bool = True
    # Red set 2: chips set aside may be placed after stopping. UNVERIFIED whether this also holds after
    # an explosion; we assume not.
    aside_after_explosion: bool = False
    # UNVERIFIED: do green/purple/black chip actions (phase B) still resolve for an exploded pot?
    chip_actions_on_explosion: bool = True


class Pot:
    __slots__ = ("start", "cur", "chips", "spots", "wsum", "exploded", "limit", "base_limit", "counts", "aside",
                 "double_next", "drawn")

    def __init__(self, start: int, limit: int):
        self.start = start
        self.cur = start
        self.chips: list = []
        self.spots: list = []
        self.wsum = 0
        self.exploded = False
        self.limit = limit
        self.base_limit = limit
        self.counts = [0] * 8
        self.aside: list = []  # red set 2
        self.double_next = False  # yellow set 2
        self.drawn = 0

    def explode_risk(self, bag) -> float:
        """Probability that the next draw makes the pot explode."""
        if not bag:
            return 0.0
        room = self.limit - self.wsum
        n = 0
        for c in bag:
            if COLOR_OF[c] == WHITE and VALUE_OF[c] > room:
                n += 1
        return n / len(bag)

    def last_is_white(self) -> bool:
        return bool(self.chips) and COLOR_OF[self.chips[-1]] == WHITE


class Player:
    __slots__ = ("seat", "strategy", "bag", "vp", "rubies", "droplet", "flask", "pending", "last_cur", "history",
                 "explosions")

    def __init__(self, seat: int, strategy, rules: Rules):
        self.seat = seat
        self.strategy = strategy
        self.bag = list(STARTER_BAG)
        self.vp = 0
        self.rubies = rules.start_rubies
        self.droplet = 0
        self.flask = True
        self.pending: list = []
        self.last_cur = 0
        self.history: list = []  # per round (exploded, cur, vp_after)
        self.explosions = 0


class Game:
    def __init__(self, strategies, sets=(0, 1, 1, 1, 1, 1, 1, 1), rng: random.Random | None = None,
                 rules: Rules | None = None, record: bool = False):
        """``sets[color]`` is the ingredient-book set (1-4) in play for that colour."""
        self.rules = rules or Rules()
        self.rng = rng or random.Random()
        self.sets = tuple(sets)
        self.players = [Player(i, s, self.rules) for i, s in enumerate(strategies)]
        self.n = len(self.players)
        self.round = 0
        self.record = record
        self.catalog = self._build_catalog()
        self.log: list = []

    # ------------------------------------------------------------------ setup
    def _build_catalog(self):
        cat = []
        for (color, set_no), book in BOOKS.items():
            if color in (ORANGE, BLACK) or self.sets[color] == set_no:
                for value, c in book.costs.items():
                    cat.append((chip(color, value), c, color))
        cat.sort(key=lambda t: (t[1], t[0]))
        return cat

    # --------------------------------------------------------------- main loop
    def run(self):
        for r in range(1, self.rules.n_rounds + 1):
            self.round = r
            self._round(r)
        return self.result()

    def result(self):
        """Final standings: list of dict per player, plus winners (ties by last-round pot position)."""
        out = []
        for p in self.players:
            final = p.vp + p.rubies // self.rules.rubies_per_vp
            out.append({"seat": p.seat, "vp": p.vp, "rubies": p.rubies, "final": final, "tiebreak": p.last_cur})
        best = max((o["final"], o["tiebreak"]) for o in out)
        winners = [o["seat"] for o in out if (o["final"], o["tiebreak"]) == best]
        return {"players": out, "winners": winners}

    # ------------------------------------------------------------------- round
    def _round(self, r: int):
        rules = self.rules
        players = self.players
        leader_vp = max(p.vp for p in players)
        pots = []
        for p in players:
            tails = 0
            if rules.use_rat_tails and r > 1:
                tails = board.rat_tails_between(p.vp, leader_vp)
            start = min(p.droplet + tails, TRACK_END)
            pots.append(self._brew(p, start))

        # A: bonus die for the furthest non-exploded pot(s)
        alive = [i for i, pot in enumerate(pots) if not pot.exploded]
        if alive:
            best = max(pots[i].cur for i in alive)
            for i in alive:
                if pots[i].cur == best:
                    self._roll_die(players[i])

        # B: chip actions
        blacks = [pot.counts[BLACK] for pot in pots]
        for i, p in enumerate(players):
            if rules.chip_actions_on_explosion or not pots[i].exploded:
                self._chip_actions(p, pots[i], blacks, i)

        # C-F per player
        for i, p in enumerate(players):
            pot = pots[i]
            idx = min(pot.cur + 1, TRACK_END)
            p.rubies += board.RUBIES[idx]
            vp_gain, coins = board.VP[idx], board.COINS[idx]
            if pot.exploded:
                if p.strategy.explosion_choice(self, p, pot, vp_gain, coins) == "vp":
                    coins = 0
                else:
                    vp_gain = 0
            p.vp += vp_gain
            if coins > 0:
                self._buy(p, coins)
            p.last_cur = pot.cur
            if pot.exploded:
                p.explosions += 1
            if r < rules.n_rounds:
                self._spend_rubies(p)
            if self.record:
                p.history.append((pot.exploded, pot.cur, p.vp))

        # return everything to the bags
        for i, p in enumerate(players):
            pot = pots[i]
            p.bag.extend(pot.chips)
            p.bag.extend(pot.aside)
            p.bag.extend(p.pending)
            p.pending.clear()

    # ------------------------------------------------------------------- brewing
    def _brew(self, p: Player, start: int) -> Pot:
        pot = Pot(start, self.rules.explosion_limit)
        strat = p.strategy
        bag = p.bag
        rng = self.rng
        while bag and not pot.exploded:
            if not strat.should_draw(self, p, pot):
                break
            c = bag.pop(rng.randrange(len(bag)))
            pot.drawn += 1
            self._play(p, pot, c)
            if (not pot.exploded and p.flask and pot.last_is_white() and strat.use_flask(self, p, pot)):
                self._use_flask(p, pot)
        if not pot.exploded:
            for c in pot.aside:  # red set 2: place after the last chip
                pos = min(pot.cur + VALUE_OF[c], TRACK_END)
                pot.chips.append(c)
                pot.spots.append(pos)
                pot.counts[RED] += 1
                pot.cur = pos
            pot.aside = []
        return pot

    def _use_flask(self, p: Player, pot: Pot):
        c = pot.chips.pop()
        pot.spots.pop()
        pot.cur = pot.spots[-1] if pot.spots else pot.start
        pot.wsum -= VALUE_OF[c]
        pot.counts[WHITE] -= 1
        p.bag.append(c)
        p.flask = False

    def _play(self, p: Player, pot: Pot, c: int):
        """Place chip ``c`` into the pot and resolve its draw-time effect."""
        color = COLOR_OF[c]
        v = VALUE_OF[c]
        sets = self.sets
        chips = pot.chips
        move = v
        prev = chips[-1] if chips else -1
        prev_white = prev >= 0 and COLOR_OF[prev] == WHITE

        if color == WHITE:
            if sets[RED] == 4 and pot.counts[RED] and v == 1:
                move = 2
        elif color == RED:
            s = sets[RED]
            if s == 1:
                o = pot.counts[ORANGE]
                move += 2 if o >= 3 else (1 if o >= 1 else 0)
            elif s == 2:
                pot.aside.append(c)
                return
            elif s == 3 and prev_white:
                move += VALUE_OF[prev]
        elif color == YELLOW:
            if sets[YELLOW] == 4:
                n = pot.counts[YELLOW] + 1
                if n <= 3:
                    move += n

        if pot.double_next:
            move *= 2
            pot.double_next = False

        pos = min(pot.cur + move, TRACK_END)
        chips.append(c)
        pot.spots.append(pos)
        pot.cur = pos
        pot.counts[color] += 1

        if color == WHITE:
            pot.wsum += v
            if pot.wsum > pot.limit:
                pot.exploded = True
        elif color == YELLOW:
            s = sets[YELLOW]
            if s == 1 and prev_white:
                # return the previous white chip to the bag; the yellow chip keeps its space
                chips.pop(-2)
                pot.spots.pop(-2)
                pot.wsum -= VALUE_OF[prev]
                pot.counts[WHITE] -= 1
                p.bag.append(prev)
            elif s == 2:
                pot.double_next = True
            elif s == 3:
                ny = pot.counts[YELLOW]
                pot.limit = pot.base_limit + (1 if ny >= 1 else 0) + (1 if ny >= 3 else 0)
        elif color == BLUE:
            s = sets[BLUE]
            if s == 3:
                if board.RUBIES[pos]:
                    p.rubies += 1
            elif s == 4:
                if board.RUBIES[pos]:
                    p.vp += v
            elif s == 1:
                self._blue_draw(p, pot, v)

    def _blue_draw(self, p: Player, pot: Pot, n: int):
        bag = p.bag
        rng = self.rng
        options = [bag.pop(rng.randrange(len(bag))) for _ in range(min(n, len(bag)))]
        if not options:
            return
        k = p.strategy.blue_choice(self, p, pot, options)
        chosen = None
        if 0 <= k < len(options):
            chosen = options.pop(k)
        bag.extend(options)
        if chosen is not None:
            self._play(p, pot, chosen)

    # ---------------------------------------------------------------- evaluation
    def _roll_die(self, p: Player):
        face = self.rng.choice(self.rules.die_faces)
        if face == "vp1":
            p.vp += 1
        elif face == "vp2":
            p.vp += 2
        elif face == "ruby":
            p.rubies += 1
        elif face == "orange":
            p.pending.append(chip(ORANGE, 1))
        elif face == "droplet":
            p.droplet = min(p.droplet + 1, TRACK_END)

    def _chip_actions(self, p: Player, pot: Pot, blacks, i: int):
        sets = self.sets
        counts = pot.counts

        # Green (garden spider): last or next-to-last chip
        if counts[GREEN]:
            gl = [c for c in pot.chips[-2:] if COLOR_OF[c] == GREEN]
            s = sets[GREEN]
            if gl:
                if s == 1:
                    p.rubies += len(gl)
                elif s == 2:
                    for c in gl:
                        p.pending.append(self._green2_reward(p, pot, VALUE_OF[c]))
                elif s == 4:
                    pay = p.strategy.green4_pay(self, p, pot, len(gl))
                    pay = max(0, min(pay, len(gl), p.rubies))
                    p.rubies -= pay
                    p.droplet = min(p.droplet + pay, TRACK_END)
            if s == 3 and pot.wsum == 7:
                total = sum(VALUE_OF[c] for c in pot.chips if COLOR_OF[c] == GREEN)
                pot.cur = min(pot.cur + total, TRACK_END)

        # Purple (ghost's breath)
        n = counts[PURPLE]
        if n:
            s = sets[PURPLE]
            if s == 1:
                if n == 1:
                    p.vp += 1
                elif n == 2:
                    p.vp += 1
                    p.rubies += 1
                else:
                    p.vp += 2
                    p.droplet = min(p.droplet + 1, TRACK_END)
            elif s == 2:
                tier = p.strategy.purple2_tier(self, p, pot, min(n, 3))
                tier = max(0, min(tier, n, 3))
                if tier:
                    self._remove_chips(pot, PURPLE, tier)
                    if tier == 1:
                        p.pending.append(chip(BLACK, 1))
                        p.vp += 1
                        p.rubies += 1
                    elif tier == 2:
                        p.pending.append(chip(GREEN, 1))
                        p.pending.append(chip(BLUE, 2))
                        p.vp += 3
                        p.droplet = min(p.droplet + 1, TRACK_END)
                    else:
                        p.pending.append(chip(YELLOW, 4))
                        p.vp += 6
                        p.rubies += 1
                        p.droplet = min(p.droplet + 2, TRACK_END)
            elif s == 3:
                for c, sp in zip(pot.chips, pot.spots):
                    if COLOR_OF[c] == PURPLE:
                        p.vp += 3 if sp >= 30 else (2 if sp >= 20 else (1 if sp >= 10 else 0))
            elif s == 4:
                self._purple4_upgrade(p, pot, n)

        # Black (moth)
        nb = blacks[i]
        if nb:
            n_players = self.n
            if n_players == 2:
                opp = blacks[1 - i]
                if nb > opp:
                    p.droplet = min(p.droplet + 1, TRACK_END)
                    p.rubies += 1
                elif nb == opp:
                    p.droplet = min(p.droplet + 1, TRACK_END)
            else:
                left, right = blacks[(i + 1) % n_players], blacks[(i - 1) % n_players]
                if nb > left and nb > right:
                    p.droplet = min(p.droplet + 1, TRACK_END)
                    p.rubies += 1
                elif nb > left or nb > right:
                    p.droplet = min(p.droplet + 1, TRACK_END)

    def _green2_reward(self, p: Player, pot: Pot, value: int) -> int:
        if value == 1:
            return chip(ORANGE, 1)
        if value == 2:
            return chip(p.strategy.green2_choice(self, p, (BLUE, RED)), 1)
        return chip(p.strategy.green2_choice(self, p, (YELLOW, PURPLE)), 1)

    @staticmethod
    def _remove_chips(pot: Pot, color: int, k: int):
        removed = 0
        for j in range(len(pot.chips) - 1, -1, -1):
            if COLOR_OF[pot.chips[j]] == color:
                pot.chips.pop(j)
                pot.spots.pop(j)
                pot.counts[color] -= 1
                removed += 1
                if removed == k:
                    break

    def _purple4_upgrade(self, p: Player, pot: Pot, n: int):
        frm, to = (1, 2) if n == 1 else ((2, 4) if n == 2 else (1, 4))
        cand = [j for j, c in enumerate(pot.chips)
                if VALUE_OF[c] == frm and COLOR_OF[c] in (GREEN, BLUE, RED, YELLOW)]
        if not cand:
            return
        j = p.strategy.upgrade_choice(self, p, pot, cand, to)
        if j is None:
            return
        c = pot.chips.pop(j)
        pot.spots.pop(j)
        pot.counts[COLOR_OF[c]] -= 1
        p.pending.append(chip(COLOR_OF[c], to))

    # --------------------------------------------------------------- spending
    def _buy(self, p: Player, coins: int):
        picks = p.strategy.buy(self, p, coins)
        if not picks:
            return
        cost_of = {c: cost for c, cost, _ in self.catalog}
        if len(picks) > self.rules.max_buys:
            raise ValueError("too many chips bought")
        total = 0
        colors = set()
        for c in picks:
            if c not in cost_of:
                raise ValueError(f"chip {c} is not for sale")
            total += cost_of[c]
            col = COLOR_OF[c]
            if col in colors and not self.rules.same_color_twice:
                raise ValueError("cannot buy two chips of the same colour")
            colors.add(col)
        if total > coins:
            raise ValueError(f"cannot afford {picks}: {total} > {coins}")
        p.pending.extend(picks)

    def _spend_rubies(self, p: Player):
        drops, refill = p.strategy.spend_rubies(self, p)
        rc = self.rules.ruby_cost
        if refill and not p.flask and p.rubies >= rc:
            p.rubies -= rc
            p.flask = True
        drops = max(0, min(drops, p.rubies // rc))
        p.rubies -= drops * rc
        p.droplet = min(p.droplet + drops, TRACK_END)
