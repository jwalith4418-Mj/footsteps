# Footsteps

Footsteps is a turn-based game of laying floor tiles and deciding whom to trust. One player expands the floor, everyone votes on where to step, and the exit gets harder to reach as the tile bag empties. Some players want the expedition to run out of time.

The first playable model includes a deterministic multiplayer referee, replayable public and private game accounts, a terminal solitaire game, and five automated solitaire players. A localhost referee hosts private browser seats and exposes the same decisions to automated players.

## Try a game

For a four-person table, print the [three-page playtest kit](playtest/kit.pdf). It includes cut tiles, role cards, simultaneous ballots, and an observer sheet. [Paper setup and tile mix](playtest/README.md)

From this directory use Python 3.13+ or enter the pinned shell with `nix develop`.

```sh
python -m footsteps solo --policy human --seed 0
python -m footsteps replay examples/crossing.json
python -m footsteps replay examples/crossing.json --seat 3
python -m footsteps solo --seed 59 --policy route --goal 6 0 --store 10 --save /tmp/game.json
python -m footsteps replay /tmp/game.json --full > /tmp/game.full.md
python -m footsteps replay /tmp/game.full.md
python -m unittest discover -s tests -v
```

Read the two-turn example to see a tied vote, an elimination and a win on the final draw. Its JSON is an editable scenario. A full Markdown account embeds the secret referee record and can be imported again. [Rulebook](docs/rules.md) · [Worked game](examples/crossing.md) · [JSON](examples/crossing.json) · [Record format](docs/records.md)

## Host a local table

```sh
python -m footsteps table --save /tmp/footsteps-game.json
```

New tables and solitaire games put EXIT at (0, 0). The usual layout starts at (−4, −2). Use `--start-origin` for historical coordinates. For solitaire, `--goal 4 2` specifies four squares east and two north from START in either convention.

For the experimental placement interface, add `--placement-check edge-and-marker` to the table command. Builders identify a neighboring tile, read the directed edge into the new tile and say whether the marker occupies the chosen origin. `--placement-check edge` asks only about the edge. [Worked positions and results](experiments/placement-check/README.md)

For three players, add `--seats 3` to deal two Blue roles and one Red. Open the private seat links printed in the host terminal. Each player selects **Ready to play**. The last ready seat starts the clock. The default deal uses the four-seat paper kit. Add `--crossing` for the public two-turn example setup, `--seconds 90` for longer decisions, or `--discussion 0` to go straight to voting. Each run needs a fresh output path.

For rotation assistance, an Ollama seat can use `--rotation-aid table` or `--rotation-aid tool`. The latter lets it request one held face by number. Add `--named-rotations` for literal clockwise turn names. [Comparison and tool-use observations](experiments/rotation/README.md)

To put a local model in one seat, run `python -m footsteps ollama --model qwen2.5:3b` and paste its private link. [Recorded model game](experiments/ollama-crossing.md) · [Mixed-strength self-play and workstation timings](experiments/model-panel/README.md)

For a model that keeps a private conversation across turns, run `python -m footsteps.session --model MODEL`. It can listen, check a revealed ballot, save a private summary and wait for its next opportunity. [Persistent seat and tools](docs/table.md#persistent-ollama-seat)

The host checkpoints the secret referee record. Only the selected seat's view and history go to its browser. Use the exported record for postgame review or a public transcript. [Local seat API and timing](docs/table.md)

## Inspect a transcript

Export a single HTML file and open it in a browser. It works offline. The viewer accepts the same JSON records and full Markdown accounts as the replay command, including unfinished games.

```sh
python -m footsteps view examples/crossing.json -o /tmp/crossing.html
python -m footsteps view examples/crossing.json --seat 0 -o /tmp/crossing-p0.html
python -m footsteps view examples/crossing.json --omniscient -o /tmp/crossing-referee.html
```

In the crossing, stop at event 4 to inspect the proposed destination. Select face 40 to see its west entrance and east exit. Advance once to reveal the ballots and watch the marker move on the builder’s tie-break. Use the slider to rewind or jump directly to a turn.

The default export contains the public history. A seat export also contains that player’s role, known teammates, hand and private observations. Hand tiles show their printed orientation and list their entry and exit edges. In P0’s export, step through the first draw, placement and return to see three tiles become one. The omniscient export contains every hand, role, private draw and return from setup onward, including hands set aside at elimination. Share that file with anyone entitled to see all seats’ secrets. A completed file includes the eventual outcome and role reveal. Export a record prefix when sharing an unresolved decision with playtesters.

## First solitaire results

Across 800 ten-turn games per policy, the player that checked onward exits reached the goal 789 times. The player that searched reachable floor and could backtrack won 792, including 258 wins after the earliest possible turn. Random play won zero. The experiment includes tight budgets, two exit offsets, two hand sizes and a shared-prefix endgame comparison. [Experiment and reproduction](experiments/README.md) · [Counts](experiments/counts.md) · [Raw CSV](experiments/pilot.csv)

A [four-seat exit-offset study](experiments/exit-offsets.md) holds the printed kit fixed and varies the goal. It includes a matched deal where a one-tile bridge works diagonally and a straight exit takes four moves.

## Development

With Nix, nix-direnv, and the Codex CLI installed, run these commands in a host terminal at the project root:

```sh
direnv allow                      # Once per checkout, and after editing .envrc
./scripts/resume-codex.sh         # Pick a Footsteps conversation
```

Use `./scripts/resume-codex.sh --last` to resume the latest project conversation, or pass a session ID. The helper loads the locked development shell, selects the Footsteps workspace, and requests on-demand approvals for operations such as pushing to GitHub. Host policy governs which approvals are available. For a one-off development command, use `direnv exec . python -m unittest discover -s tests`.

The [persistent-runner stocktake](docs/stocktake.md) lists the next experiments, migration dependencies, human playtest and coverage gaps. Use Issues for work and discussion. Submit mechanical decisions, worked examples and experimental results in the same PR as their implementation. [Contribution workflow](CONTRIBUTING.md) · [Worker guide](AGENTS.md) · [Design decisions](docs/decisions.md) · [Playtesting](docs/playtesting.md) · [Open issues](https://github.com/othercriteria/footsteps/issues)

Code and technical materials use MIT. The original rulebook, worked game prose and game art use CC BY 4.0. [License scope and texts](LICENSE)

Model seats can consult board tools and attach optional private explanations to an omniscient replay. [Seat tool catalog and roadmap](docs/seat-tools.md) · [Recording and viewing decision notes](docs/table.md#join-with-ollama)

For a model seat that places tiles by native function call, use `--action-tools direct` or `--action-tools hand`. In hand mode, each physical copy can be turned privately and a placement commits its current orientation. Add `--all-decisions` to exercise native calls beyond construction. The host can capture held-copy turns with `--private-rotations FILE` for an omniscient replay. [Private hand and action protocol](docs/table.md#native-action-calls-and-private-hand-pieces)
