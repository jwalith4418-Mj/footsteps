# Open social tables after the clock clarification

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

## Four seats

The lone Red builder P0 opened a traversable northward step and identified itself as Red when P1 nominated it. Blue P1 argued against its own nomination, describing P0 as cooperative. All four rejected the nomination. During the next removal discussion P2 claimed that its starting roster information pointed to P1 being Red. As a Blue seat P2 had no such private roster. All four voted No again. The statements establish what the seats told each other, leaving open whether individual claims were mistakes or bluffs.

On turn two the group approved another legal step, going east. The proposer said the destination admitted entry from the east. That step actually requires entry from the west. On turn three P2 placed a tile with no entrances off the route, then used the already-built path to propose EXIT. Blue P3 publicly identified the winning team, Red P0 supported the proposal, and all four voted Yes. That is the opposite of the three-seat Red response to the same terminal consequence. Its ballot alone could not have changed the outcome in this game either. All 37 decisions were timely and all 20 speaking windows yielded remarks. [Game record](four/game.json)

## A blind guest with persistent opponents

The earlier guest harness used a virtual clock and the per-decision model runner. The live guest now uses the same authenticated localhost table as the persistent models. Its file terminal exposes one seat's legal choices, public remarks and ballots, held faces, and role briefing. The guest can speak before movement or removal votes. Each packet carries its revision and remaining time. Late packets expire, and the referee decides whether a submission arrived in time. Accepted guest choices can carry a short private observation into the owner's omniscient viewer. The debrief is requested before showing the final roster. Blinding on a shared workstation depends on the guest using only the exchange and rulebook it was given.

Launch the host with three local model seats. Give a guest only the exchange directory and its copied rulebook. All three paths must be fresh. The host uses a freshly generated seed unless supplied with `--seed`. The seed and guest index are written to the postgame deal receipt.

```sh
python -m experiments.persistent_guest /tmp/game134 /tmp/owner134 /tmp/seat134
python /tmp/seat134/seat.py next
python /tmp/seat134/seat.py submit 1 '{"choice":{"vote":false},"observation":"My observation before the reveal."}'
```

Use the actual packet ID and legal fields. A speech packet takes a `speech` string or the empty string to stay silent. Submit the debrief as an `observation`. The guest table allows 90 seconds per decision and 40 seconds of discussion. Its clock and one human-operated seat differ from the two all-model tables.

On seed 3772523307 the blind guest drew Blue P0. Its opening tile allowed a north step and it publicly described the west entrance and east exit needed at (−1, 0). Red P1 supplied both on the very next build. Blue P2 later proposed entering EXIT. All three movement ballots were unanimous and all nominations were passes. Every one of the 29 required choices was timely. Before seeing the final roster the guest tentatively suspected P3, citing P1's construction and P2's use of the route as evidence for Blue. P3 was Blue and never had a build turn. P1 was the lone Red.

At event 22, P1 and P3 both attributed the proposed winning step to the newest tile at (−1, −1). EXIT is diagonal from that tile. The marker was at (−1, 0) on P1's older tile, which genuinely had a traversable east edge. This gives two instances of a legal choice with a publicly incorrect explanation on one ballot. The debrief and time-stamped guest observations are owner-only. [Guest game](guest/game.json) · [Deal and guest seat](guest/deal.json)

To export the private guest observations on a replay, use the corresponding guest seat's owner sidecar. For this deal the guest was P0:

```sh
python -m footsteps view /tmp/game134/game.json --omniscient --notes /tmp/owner134/seat-0.jsonl -o /tmp/134-guest.html
```
