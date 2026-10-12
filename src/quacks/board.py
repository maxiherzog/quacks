"""The score track, rat tails and the bonus die.

Verification status of everything in this file is tracked in ``DATA_STATUS.md``.
"""

# Taken from the author's own notebooks (quacks.ipynb), which were transcribed from the physical board.
COINS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 15, 16, 16, 17, 17, 18, 18, 19, 19, 20, 20, 21,
         21, 22, 22, 23, 23, 24, 24, 25, 25, 26, 26, 27, 27, 28, 28, 29, 29, 30, 30, 31, 31, 32, 32, 33, 33]
RUBIES = [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1,
          0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1]
VP = [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8, 9,
      9, 9, 10, 10, 10, 11, 11, 11, 12, 12, 12, 12, 13, 13, 13, 14, 14]

assert len(COINS) == len(RUBIES) == len(VP)
TRACK_END = len(COINS) - 1  # highest index of the pot track

# Bonus die. UNVERIFIED: five outcomes are confirmed (1 VP, 2 VP, ruby, orange chip, droplet),
# the sixth face is not. A second ruby face is assumed.
DIE_FACES = ("vp1", "vp2", "ruby", "orange", "droplet", "ruby")

# Rat tails. UNVERIFIED: the real positions of the rat tails on the score track are unknown.
# We assume one tail per ``RAT_TAIL_EVERY`` victory points.
RAT_TAIL_EVERY = 2


def rat_tails_between(vp_low: int, vp_high: int) -> int:
    return vp_high // RAT_TAIL_EVERY - vp_low // RAT_TAIL_EVERY
