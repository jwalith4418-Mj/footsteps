# Working on Footsteps

Read the README for commands, docs/rules.md for adjudication, and docs/decisions.md for the choices still worth testing. Start with a GitHub issue describing a behavior or design question. The initial issue bodies in docs/issues/ can be filed when bringing the project online. Once filed, track status and discussion on GitHub.

Use the locked Nix shell or Python 3.13+; the referee has no third-party Python dependencies. Run these checks from the root:

```sh
ruff check .
ruff format --check .
python -m unittest discover -s tests -v
python -m footsteps replay examples/crossing.json
```

The referee in footsteps/game.py is the sole authority on legality and termination. Keep rule changes there and in docs/rules.md. Policies in footsteps/solo.py may inspect only information available at their decision. Store an explicit chance result when a draw or timeout affects a replay. Test visibility and final-turn precedence when touching those paths. Never pass full referee JSON to a player.

For a rule change, discuss the motivation on the issue, include a small worked history, and explain any version impact in the PR. For an experiment, follow experiments/README.md and docs/playtesting.md. Put the reproduction command, result, and uncertainty in the PR and link the relevant issue. Keep reproducible observations in the repository even after the issue closes.

For initial publication under othercriteria/footsteps, push the initial branch, then run `python scripts/seed_issues.py`. It checks open and closed issue titles before posting the four briefs. Later issues can be created directly on GitHub.
