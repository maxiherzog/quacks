"""Command line: ``python -m quacks.cli {sim,sets,optimize} ...``"""

from __future__ import annotations

import argparse

from . import optimize as opt
from .books import SET_COLORS
from .chips import BLACK, BLUE, COLOR_NAMES, GREEN, ORANGE, PURPLE, RED, YELLOW
from .sim import run_games
from .strategies import PRESETS, ParamStrategy, preset

SET_ORDER = (GREEN, BLUE, RED, YELLOW, PURPLE)


def parse_seat(spec: str):
    if spec in PRESETS:
        return preset(spec)
    return ParamStrategy(theta=opt.load(spec), label=spec.rsplit("/", 1)[-1])


def parse_sets(spec: str | None):
    """``random`` (default) or a comma list of fixed sets in the order green,blue,red,yellow,purple;
    ``-`` leaves that colour random, e.g. ``1,-,-,2,-``."""
    if not spec or spec == "random":
        return None
    parts = spec.split(",")
    if len(parts) != 5:
        raise SystemExit("--sets needs 5 entries (green,blue,red,yellow,purple)")
    return {c: int(p) for c, p in zip(SET_ORDER, parts) if p != "-"}


def print_table(seats, stats):
    print(f"{'seat':<18}{'win%':>8}{'±':>6}{'mean VP':>9}{'sd':>6}{'expl/rd':>9}")
    for s, x in zip(seats, stats):
        print(f"{s.name:<18}{100 * x.win_rate:8.1f}{100 * x.win_se:6.1f}{x.mean:9.1f}{x.std:6.1f}"
              f"{x.explosions / max(1, x.games) / 9:9.2f}")


def cmd_sim(a):
    seats = [parse_seat(s) for s in a.seats.split(",")]
    fixed = parse_sets(a.sets)
    stats = run_games(seats, a.games, seed=a.seed, workers=a.workers, include_unverified=a.unverified,
                      fixed_sets=fixed)
    print_table(seats, stats)


def cmd_sets(a):
    seats = [parse_seat(s) for s in a.seats.split(",")]
    stats, groups = run_games(seats, a.games, seed=a.seed, workers=a.workers, by_set=True,
                              include_unverified=a.unverified)
    k = a.focus
    print(f"{seats[k].name}: results by ingredient set (all other colours random)")
    print(f"{'book':<10}{'set':>4}{'games':>8}{'win%':>8}{'mean VP':>9}")
    for color in SET_COLORS:
        for (kk, cc, sset), g in sorted(groups.items()):
            if kk == k and cc == color:
                print(f"{COLOR_NAMES[color]:<10}{sset:>4}{g.games:8d}{100 * g.win_rate:8.1f}{g.mean:9.1f}")


def cmd_optimize(a):
    theta, hist = opt.optimize(
        opponents=tuple(a.opponents.split(",")), self_play=a.self_play, generations=a.generations,
        population=a.population, n_games=a.games, seed=a.seed, workers=a.workers, objective=a.objective,
        include_unverified=a.unverified, fixed_sets=parse_sets(a.sets))
    opt.save(theta, a.out)
    print(opt.describe(theta))
    seats = [ParamStrategy(theta=theta, label="optimised")] + [preset(n) for n in a.opponents.split(",")]
    print("\nvalidation (fresh seeds):")
    print_table(seats, run_games(seats, a.validate, seed=a.seed + 99991, workers=a.workers,
                                 include_unverified=a.unverified, fixed_sets=parse_sets(a.sets)))
    print(f"\nsaved to {a.out}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="quacks")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--seats", default="moderate,gambler,cautious,ramp",
                       help="comma list of presets (%s) or saved theta files" % "/".join(PRESETS))
        p.add_argument("--games", type=int, default=2000)
        p.add_argument("--seed", type=int, default=0)
        p.add_argument("--workers", type=int, default=4)
        p.add_argument("--unverified", action="store_true", help="also draw ingredient sets whose data is unverified")

    p = sub.add_parser("sim", help="simulate games and print win rates")
    common(p)
    p.add_argument("--sets", default="random")
    p.set_defaults(fn=cmd_sim)

    p = sub.add_parser("sets", help="how a strategy performs with each ingredient set")
    common(p)
    p.add_argument("--focus", type=int, default=0, help="seat index to report")
    p.set_defaults(fn=cmd_sets)

    p = sub.add_parser("optimize", help="evolve a strategy")
    common(p)
    p.add_argument("--opponents", default="moderate,gambler,ramp")
    p.add_argument("--self-play", action="store_true")
    p.add_argument("--generations", type=int, default=30)
    p.add_argument("--population", type=int, default=24)
    p.add_argument("--objective", default="mixed", choices=("win", "score", "mixed"))
    p.add_argument("--sets", default="random")
    p.add_argument("--validate", type=int, default=4000)
    p.add_argument("--out", default="best_strategy.json")
    p.set_defaults(fn=cmd_optimize)

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
