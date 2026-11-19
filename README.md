# Footsteps

Footsteps is a turn-based game of laying floor tiles and deciding whom to trust. One player expands the floor, everyone votes on where to step, and the exit gets harder to reach as the tile bag empties. Some players want the expedition to run out of time.

The first playable model includes a deterministic multiplayer referee, replayable public and private game accounts, a terminal solitaire game, and five automated solitaire players. The multiplayer referee currently accepts event records. The localhost table and Ollama seats are planned work.

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

## Inspect a transcript

Export a single HTML file and open it in a browser. It works offline. The viewer accepts the same JSON records and full Markdown accounts as the replay command, including unfinished games.

```sh
python -m footsteps view examples/crossing.json -o /tmp/crossing.html
python -m footsteps view examples/crossing.json --seat 0 -o /tmp/crossing-p0.html
```

In the crossing, stop at event 4 to inspect the proposed destination. Select face 40 to see its west entrance and east exit. Advance once to reveal the ballots and watch the marker move on the builder’s tie-break. Use the slider to rewind or jump directly to a turn.

The default export contains the public history. A seat export also contains that player’s role, known teammates, hand and private observations. A completed file includes the eventual outcome and role reveal. Export a record prefix when sharing an unresolved decision with playtesters.

## First solitaire results

Across 800 ten-turn games per policy, the player that checked onward exits reached the goal 789 times. The player that searched reachable floor and could backtrack won 792, including 258 wins after the earliest possible turn. Random play won zero. The experiment includes tight budgets, two exit offsets, two hand sizes and a shared-prefix endgame comparison. [Experiment and reproduction](experiments/README.md) · [Counts](experiments/counts.md) · [Raw CSV](experiments/pilot.csv)

## Development

With Nix, nix-direnv, and the Codex CLI installed, run these commands in a host terminal at the project root:

```sh
direnv allow                      # Once per checkout, and after editing .envrc
./scripts/resume-codex.sh         # Pick a Footsteps conversation
```

Use `./scripts/resume-codex.sh --last` to resume the latest project conversation, or pass a session ID. The helper loads the locked development shell, selects the Footsteps workspace, and requests on-demand approvals for operations such as pushing to GitHub. Host policy governs which approvals are available. For a one-off development command, use `direnv exec . python -m unittest discover -s tests`.

The next questions concern rotating private hands, recoverable traps and when a human table first has grounds to nominate someone. Use Issues for work and discussion. Submit mechanical decisions, worked examples and experimental results in the same PR as their implementation. [Contribution workflow](CONTRIBUTING.md) · [Worker guide](AGENTS.md) · [Design decisions](docs/decisions.md) · [Playtesting](docs/playtesting.md) · [Open issues](https://github.com/othercriteria/footsteps/issues)

Code and technical materials use MIT. The original rulebook, worked game prose and game art use CC BY 4.0. [License scope and texts](LICENSE)
