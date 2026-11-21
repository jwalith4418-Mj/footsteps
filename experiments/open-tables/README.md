# Two open social tables after the clock clarification

We picked two new seeds and played each deal to termination. Each living seat had its own persistent conversation with Qwen3.5 9B Q8_0, using the live movement-clock instructions from a04b8c4. The seats received their ordinary private projections, could speak before either kind of ballot and used the native action tools. Nobody received a pregame memo or a scripted move. We looked for useful play, disputed claims, construction trouble, nominations, deadline misses and decisions worth replaying on both teams.

| Deal | Distribution | START | Starting store | Seed |
|---|---|---|---:|---:|
| Three | 2 Blue, 1 Red | (−2, 0) | 4 | 13401 |
| Four | 3 Blue, 1 Red | (−2, −1) | 6 | 13402 |

Both deals shuffle the paper kit, deal two tiles per hand, and use EXIT at (0, 0). They ran sequentially at 16k with thinking disabled. Each required action has 60 seconds. Discussion allows one remark per living seat, up to 30 seconds, and closes early when all seats finish speaking. Several parameters change together. The observations describe these games and do not isolate a seat-count or prompt effect.

## Reproduce

Run from the repository root with local Ollama and fresh output directories. Each game has a host record for replay and redacted per-seat call receipts for timing. Raw seat traces are local owner files.

```sh
python -m experiments.open_tables three /tmp/134-three /tmp/134-private-three
python -m experiments.open_tables four /tmp/134-four /tmp/134-private-four
python -m experiments.early_ballot experiments/open-tables/three
python -m experiments.early_ballot experiments/open-tables/four
python -m footsteps view experiments/open-tables/four/game.json --omniscient -o /tmp/134-four.html
```

Replay reproduces the saved events exactly. Re-running inference can change discussion and actions as the seats share a wall clock and GPU queue.

## Three seats

P0's opening placement of face 41 supplied both the west entrance from START and an east exit into EXIT. All three approved the first step. P1, who had just endorsed the construction, then nominated P0. Red P2 publicly identified itself as the lone Red, P0 questioned the nomination, and P1 asserted that P0 was Red. All three voted to remove P0, including P0 itself. The recorded tool calls distinguish this self-vote from a timeout.

On turn two Blue P1 proposed EXIT. P2 publicly said both that it supported the move and that it must vote against it because Blue would win. Its actual ballot was No. P1's Yes broke the 1–1 tie and won for Blue, with two tiles left. All 16 required decisions were timely. Final remarks appeared in all eight accepted ballot prompts. This finish supplies a useful positive case for [the proposer/voter experiment](https://github.com/othercriteria/footsteps/issues/101). [Game record](three/game.json)
