# Working on Footsteps

Read the README for commands, docs/rules.md for adjudication, and docs/decisions.md for the choices still worth testing. Follow [the contribution workflow](CONTRIBUTING.md). Claim a GitHub issue, work on its topic branch, and submit a PR against current main. Use a separate worktree when sharing a clone with another worker.

Use the locked Nix shell or Python 3.13+; the referee has no third-party Python dependencies. Run these checks from the root:

```sh
ruff check .
ruff format --check .
python -m unittest discover -s tests -v
python -m footsteps replay examples/crossing.json
```

The referee in footsteps/game.py is the sole authority on legality and termination. Keep rule changes there and in docs/rules.md. Policies in footsteps/solo.py may inspect only information available at their decision. Store an explicit chance result when a draw or timeout affects a replay. Test visibility and final-turn precedence when touching those paths. Never pass full referee JSON to a player.

For a rule change, discuss the motivation on the issue, include a small worked history, and explain any version impact in the PR. For an experiment, follow experiments/README.md and docs/playtesting.md. Put the reproduction command, result, and uncertainty in the PR and link the relevant issue. Keep reproducible observations in the repository even after the issue closes.
