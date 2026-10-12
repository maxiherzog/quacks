"""Strategy search: a (mu, lambda) evolution strategy over ParamStrategy parameter vectors.

Candidates are compared with common random numbers (same seed for every candidate in a generation) so
that differences come from the strategy, not from luck of the shuffle.
"""

from __future__ import annotations

import json
import random
from concurrent.futures import ProcessPoolExecutor

from .chips import COLOR_NAMES, VALUE_OF, COLOR_OF
from .sim import run_games
from .strategies import (BUY_TYPES, I_DROP_UNTIL, I_EXPL_COINS, I_FLASK, I_RISK_EARLY, I_RISK_LATE, I_SCORE0,
                         N_BUY, N_THETA, ParamStrategy, default_theta, preset)


def _scales() -> list:
    s = [3.0] * N_THETA
    s[I_RISK_EARLY] = s[I_RISK_LATE] = 0.08
    s[I_FLASK] = 1.0
    s[I_EXPL_COINS] = 4.0
    s[I_DROP_UNTIL] = 1.5
    return s


SCALES = _scales()


def clip(theta: list) -> list:
    t = list(theta)
    t[I_RISK_EARLY] = min(1.0, max(0.0, t[I_RISK_EARLY]))
    t[I_RISK_LATE] = min(1.0, max(0.0, t[I_RISK_LATE]))
    t[I_FLASK] = min(8.0, max(1.0, t[I_FLASK]))
    t[I_EXPL_COINS] = min(40.0, max(0.0, t[I_EXPL_COINS]))
    t[I_DROP_UNTIL] = min(9.0, max(0.0, t[I_DROP_UNTIL]))
    return t


def fitness(stats, objective: str) -> float:
    s = stats[0]
    if objective == "win":
        return s.win_rate
    if objective == "score":
        return s.mean
    return s.win_rate + s.mean / 100.0  # mixed: win rate first, score as low-noise tie-breaker


def _eval(args):
    theta, opp_thetas, opp_presets, n_games, seed, objective, kw = args
    seats = [ParamStrategy(theta=theta, label="cand")]
    seats += [ParamStrategy(theta=t, label="opp") for t in opp_thetas]
    seats += [preset(n) for n in opp_presets]
    return fitness(run_games(seats, n_games, seed=seed, **kw), objective)


def optimize(opponents=("moderate", "gambler", "ramp"), self_play: bool = False, n_players: int = 4,
             generations: int = 30, population: int = 24, n_games: int = 400, sigma: float = 1.0,
             sigma_decay: float = 0.96, seed: int = 0, workers: int = 4, objective: str = "mixed",
             start: list | None = None, log=print, **kw):
    """Returns (best_theta, history). With ``self_play`` the opponents are copies of the current mean."""
    rng = random.Random(seed)
    mean = clip(start or default_theta())
    mu = max(2, population // 4)
    weights = [mu - i for i in range(mu)]
    wsum = sum(weights)
    history = []
    best = (-1e9, mean)
    ex = ProcessPoolExecutor(max_workers=workers) if workers > 1 else None
    try:
        for gen in range(generations):
            cands = [mean] + [clip([m + sigma * sc * rng.gauss(0, 1) for m, sc in zip(mean, SCALES)])
                              for _ in range(population - 1)]
            if self_play:
                opp_thetas, opp_presets = [mean] * (n_players - 1), []
            else:
                opp_thetas, opp_presets = [], list(opponents)[: n_players - 1]
            gen_seed = seed * 100003 + gen
            jobs = [(c, opp_thetas, opp_presets, n_games, gen_seed, objective, kw) for c in cands]
            scores = list(ex.map(_eval, jobs)) if ex else [_eval(j) for j in jobs]
            order = sorted(range(len(cands)), key=lambda i: -scores[i])
            top = order[:mu]
            if scores[order[0]] > best[0] or self_play:
                best = (scores[order[0]], cands[order[0]])
            mean = clip([sum(w * cands[i][d] for w, i in zip(weights, top)) / wsum for d in range(N_THETA)])
            sigma *= sigma_decay
            history.append({"gen": gen, "best": scores[order[0]], "mean_cand": sum(scores) / len(scores)})
            log(f"gen {gen:3d}  best {scores[order[0]]:.4f}  avg {sum(scores) / len(scores):.4f}  sigma {sigma:.2f}")
    finally:
        if ex:
            ex.shutdown()
    return (mean if self_play else best[1]), history


def describe(theta: list) -> str:
    """Human-readable summary of a parameter vector."""
    lines = [
        f"stop drawing when explosion risk > {theta[I_RISK_EARLY]:.2f} (round 1) -> {theta[I_RISK_LATE]:.2f} (round 9)",
        f"use flask once white total >= {theta[I_FLASK]:.1f}",
        f"after an explosion take coins if >= {theta[I_EXPL_COINS]:.0f}, else victory points",
        f"spend rubies on the droplet up to round {theta[I_DROP_UNTIL]:.1f}",
        "buy priority (score at round 1 -> round 9; only chips with score > 0 are bought):",
    ]
    rows = []
    for i, c in enumerate(BUY_TYPES):
        b, sl = theta[I_SCORE0 + 2 * i], theta[I_SCORE0 + 2 * i + 1]
        rows.append((b, f"  {COLOR_NAMES[COLOR_OF[c]]:7s}{VALUE_OF[c]}  {b:7.2f} -> {b + sl:7.2f}"))
    rows.sort(key=lambda r: -r[0])
    return "\n".join(lines + [r for _, r in rows])


def save(theta: list, path: str):
    with open(path, "w") as f:
        json.dump({"theta": theta}, f, indent=1)


def load(path: str) -> list:
    with open(path) as f:
        return json.load(f)["theta"]
