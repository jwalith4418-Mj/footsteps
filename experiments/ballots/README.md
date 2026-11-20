# Why did the builder veto its own move?

In a recorded four-seat game, the sole surviving good builder voted against five of its own proposals. Llama 3.1 8B repeated all five vetoes with indexed ballots. Reversing the order of the same choices turned all five into approvals. Literal ballot names reduced order sensitivity on those positions, but the model still vetoed its own closer moves in fresh games. Keep named ballots available as an experiment. [Original deal](../model-panel/llama-guided-11/game.json) · [Issue and experiment plan](https://github.com/othercriteria/footsteps/issues/24)

## Frozen votes

We reconstructed P3's seat view just before events 14, 25, 30, 35, 40 and 44. Event 14 concerns the bad builder's proposal. The last five are the survivor's self-vetoes. Each replay prefix supplies only the seat's hand, role, public state and its own history to the model. We also constructed three two-seat positions. A bad builder can propose a step into EXIT, a step onto a tile with no outgoing edge, or elimination of the sole good seat. Each living seat votes on each proposal. Score whether the seat favors its team's outcome if its vote is pivotal. A veto on the trap leaves the good builder a direct move into EXIT next turn. The recorded positions have no assigned correct answer.

Each row below covers six controlled seat decisions with approve listed first, then the same six with reject listed first. “Switched” counts positions where that single change altered the vote. The preview appends one factual sentence about approval and rejection to the latest history entry. It uses only consequences inferable from that seat's view.

| Model | Ballot | Correct, approve first | Correct, reject first | Switched in controls | Switched in recorded positions |
|---|---|---:|---:|---:|---:|
| Llama 3.1 8B | index | 3/6 | 3/6 | 6/6 | 5/6 |
| Llama 3.1 8B | named | 3/6 | 2/6 | 3/6 | 2/6 |
| Llama 3.1 8B | named + preview | 3/6 | 3/6 | 0/6 | 1/6 |
| Qwen3.5 4B | index | 3/6 | 3/6 | 0/6 | 0/6 |
| Qwen3.5 4B | named | 2/6 | 3/6 | 3/6 | 0/6 |
| Qwen3.5 4B | named + preview | 4/6 | 3/6 | 1/6 | 1/6 |

Llama with previews always supported EXIT, rejected the trap and rejected elimination of the good seat, even as the bad voter. Qwen approved every indexed ballot in the panel. Consistency under reversal alone would miss both behaviors. The two orders are repeated measurements of a position. These probes supply no evidence of the models' motives. [Indexed and named replies](probe.csv) · [Preview replies](preview.csv)

## Complete games

Four Llama seats used the paper kit, one bad role, guided placement, named proposals, thinking disabled, 15-second decision clocks and zero discussion. Each matched seed starts with the same roles, hands, bag and draw stream. Divergent decisions can change later draws. In the reference condition, only ballots are scripted. All voters reject elimination. Good seats approve moves that reduce Manhattan distance and bad seats approve the other moves. The model still builds, discards, proposes and nominates. This intervention changes both kinds of ballot and cannot identify their individual effects.

| Deals | Voters | Good wins | Closest distances, by seed | Turn-one eliminations | Good builders voting No on their own closer proposal |
|---|---|---:|---|---:|---:|
| 21, 22, 23 | indexed | 0/3 | 5, 5, 5 | 3/3 | 12/18 |
| 21, 22, 23 | named | 0/3 | 6, 6, 4 | 0/3 | 15/17 |
| 21, 22, 23 | reference | 1/3 | 0, 4, 4 | 0/3 | 0/8 |
| 31, 32, 33 | named | 0/3 | 5, 5, 5 | 2/3 | 12/15 |
| 31, 32, 33 | reference | 3/3 | 0, 0, 0 | 0/3 | 0/14 |

All fifteen records replayed, conserved the tile inventory and matched submitted choices to the recorded decisions. Every decision arrived. Scripted votes are labeled in the call logs and contribute essentially zero inference time. The reference voter let the builders reach EXIT on four of six deals. On deal 21 the **bad** builder proposed entering EXIT. On deals 22 and 23 the good turn-two builder placed face 12 with no exits, then proposed stepping onto it. The same hand contained face 41, which could leave an onward route at the same square. Manhattan progress counted both traps as forward builds. That result prompted a separate placement experiment. [Winning reference game](reference-21/game.json) · [Trap on turn two](reference-22/game.json) · [Per-game audit](results.csv) · [Placement investigation](https://github.com/othercriteria/footsteps/issues/36)

These small panels answer whether these particular builders can finish some deals under a different voter. They do not estimate balance or how humans would use eliminations. The bad seat has no way to win an elimination ballot in the reference condition. Further ballot wording trials would need evidence of role-sensitive decisions on fresh positions to justify expanding the panel.

## Reproduce

Run from the repository root with Ollama serving locally. We used Ollama 0.40.15, Llama digest prefix 46e0c10c039e and Qwen d8b0f5e9760c. Model options use temperature zero, seed 1 and 4096 context tokens. Backend scheduling and timings can vary. Each game needs a new output directory.

```sh
python -m experiments.ballot_probe > /tmp/ballot-probe.csv
python -m experiments.ballot_probe --preview > /tmp/ballot-preview.csv
for run in index-21 named-21 named-22 index-22 index-23 named-23 reference-21 reference-22 reference-23 named-31 reference-31 reference-32 named-32 named-33 reference-33; do
    mode=${run%-*}
    set --
    case "$mode" in named|reference) set -- "--$mode-ballots" ;; esac
    python -m experiments.model_panel --model llama3.1:8b --guided --named-moves --no-think --seed "${run#*-}" "$@" --out "/tmp/footsteps-ballots/$run" || exit 1
done
python -m experiments.ballot_summary experiments/ballots
python -m experiments.model_panel_summary experiments/ballots > /tmp/ballot-results.csv
cmp /tmp/ballot-results.csv experiments/ballots/results.csv
python -m footsteps view experiments/ballots/reference-22/game.json --seat 1 -o /tmp/turn-two.html
```
