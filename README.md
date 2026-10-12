# Quacks of Quedlinburg strategy simulator

Headless simulator of the 2018 base game (all four ingredient sets of every colour that we have data for)
for finding good strategies. Not meant to be played.

```
pip install -e . pytest          # or: PYTHONPATH=src
python -m quacks sim --games 20000 --seats moderate,gambler,cautious,ramp
python -m quacks sets --games 40000 --seats moderate         # how each ingredient set affects a strategy
python -m quacks optimize --generations 30 --out best.json   # evolve a strategy against the presets
python -m quacks sim --seats best.json,moderate,gambler,ramp
pytest
```

* `src/quacks/engine.py` - rules; every decision is delegated to a `Strategy`.
* `src/quacks/strategies.py` - decision policies; `ParamStrategy` is a flat parameter vector (stop-drawing risk
  by round, flask use, a buying score per chip type and round, ruby spending, explosion choice).
* `src/quacks/optimize.py` - evolution strategy with common random numbers.
* `src/quacks/sim.py` - batch runs with seat shuffling, random ingredient sets, multiprocessing (~3000 games/s on 4 cores).
* `DATA_STATUS.md` - **read this**: which rules/data are verified and which are assumptions.

The original exploratory notebooks (`quacks.ipynb`, `no_oop.ipynb`, `quackgpt.ipynb`) are untouched.
