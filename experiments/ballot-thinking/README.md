# How much thinking buys a useful ballot?

Use the live persistent native tool interface on the [role-swapped EXIT and dead-end positions](../exit-interest/README.md). Each checkpoint gets four decisions: a nonbuilder Red and Blue facing a Blue proposer on each board. Approving the literal EXIT helps Blue. Approving the closer, zero-exit tile permanently strands the marker and helps Red. All four fast controls use the same ordinary seat as the original experiment, at 16,384 context, temperature zero and inference seed one. The referee clock stays frozen in the paired trials.

The paths marked 0 allow up to five ordinary tool calls with thinking disabled and the live output limit of 240 per call. In the other arms we request native thinking with the same tools and give the whole decision a maximum total generation allowance (both thinking and the tool response). A local read consumes part of that allowance. A length-capped tool response cannot submit a ballot. All four positions remain in the denominator even when the seat runs out of tokens. Calls report the actual total returned tokens, wall time, prompt size, stop reason and whether a valid ballot was submitted. Warm the model before each run and use a single GPU caller.

Ollama 0.40.15 reported boolean thinking controls for Qwen3.5 9B Q8_0. The ordinary Qwen3.8 27B RANA tag advertised thinking capability and exposed no named levels in its model metadata. Both returned separate thinking text with the boolean switch enabled. The allowances below are generation budgets rather than checkpoint-native names for reasoning effort. [Ollama thinking controls](https://docs.ollama.com/capabilities/thinking)

## Owner views

Every returned Ollama thinking string, including incomplete attempts, goes verbatim into a private JSONL file. The matched public call stores its length and SHA-256 digest. Each role's omniscient review shows the actual board at the pending ballot. Expand a call to see its full trace, tool outcome and that trial's submitted vote or missing submission. The comparison never inserts an alternative vote into the referee's observed history. Public and single-seat viewer exports reject private sidecars. The thinking-game replay groups traces with the resulting ballot reveal. Frozen trials ending at an open ballot label their traces as pending.

Use matching basenames for public receipts and owner files. Regenerating a different game or checkpoint can produce different text even with the same seed. The viewer builder verifies the exact receipt/draft pairing before export.

```sh
mkdir -p /tmp/135-public /tmp/135-owner
python -m experiments.ballot_thinking 9b /tmp/135-public/9b-low.jsonl /tmp/135-owner/9b-low.jsonl --budgets 0 512 1536
python -m experiments.ballot_thinking 27b /tmp/135-public/27b-low.jsonl /tmp/135-owner/27b-low.jsonl --budgets 0 512 1536
python -m experiments.ballot_thinking 9b /tmp/135-public/9b-768.jsonl /tmp/135-owner/9b-768.jsonl --budgets 768
python -m experiments.thinking_view /tmp/135-owner /tmp/135-views --receipts /tmp/135-public
python -m experiments.thinking_game /tmp/135-game /tmp/135-game-owner --allowance 768
python -m footsteps view /tmp/135-game/game.json --omniscient --notes /tmp/135-game-owner/thinking-0.jsonl --notes /tmp/135-game-owner/thinking-1.jsonl --notes /tmp/135-game-owner/thinking-2.jsonl -o /tmp/135-game.html
```

## Primary matched seats

| Model | Total thinking-enabled allowance | Votes submitted | Team-serving votes | Mean request seconds per decision |
|---|---:|---:|---:|---:|
| 9B | Off | 4/4 | 2/4 | 5.2 |
| 9B | 512 | 1/4 | 1/4 | 7.1 |
| 9B | 768 | 2/4 | 2/4 | 9.1 |
| 9B | 1,536 | 4/4 | 4/4 | 7.9 |
| 27B | Off | 4/4 | 2/4 | 3.9 |
| 27B | 512 | 0/4 | 0/4 | 21.1 |
| 27B | 1,536 | 0/4 | 0/4 | 59.8 |

With thinking disabled both checkpoints approved the trap as Blue and rejected it as Red. At 1,536 tokens 9B reversed both, while preserving both correct EXIT votes. Its four decisions used 466–608 actual generated tokens each. At 768 it exhausted the allowance on both Red decisions. These are separate generations on the same projection. A smaller maximum did not consistently give a clipped copy of the response produced under a larger maximum. We did not establish the source of that variation.

The 27B RANA checkpoint exhausted every lower-budget attempt before submitting a vote. These are missing ballots with retained partial traces. No random vote or timeout was substituted into the frozen trial.

## Timed transfer

We replayed the full three-seat 13401 deal on the same real clocks, with one change to the model policy. Only an owed movement vote can spend the 768-token thinking allowance. Across calls on the same ballot, seats keep their own tool-call thinking until the revision advances. After exhaustion, the ordinary fast tools remain available until the original clock expires. Discussion, proposals, removals and construction keep the fast policy. This evaluates a practical fallback separately from the frozen trials' hard cap. The model can still reach different board positions from the earlier run.

We chose two additional checks after the primary panel. For 9B, reuse the short outward step and necessary detour from the earlier move-budget work. The public marker and proposed landing are identical across the two boards. Approval benefits Red on the short board and Blue on the detour. The experiment gives the voter its usual board and role. For 27B, allow 3,072 generated tokens on the two trap roles, since both shorter allowances expired without a single tool submission.

```sh
python -m experiments.ballot_thinking 9b /tmp/135-public/9b-route.jsonl /tmp/135-owner/9b-route.jsonl --budgets 0 1536 --cases short detour
python -m experiments.ballot_thinking 27b /tmp/135-public/27b-3072.jsonl /tmp/135-owner/27b-3072.jsonl --budgets 3072 --cases trap
```

### Finishing an interrupted decision

For each 27B attempt that spent the full 1,536-token allowance on its first call without casting a vote, the owner can reuse the exact saved thinking string. Fork the same seat twice. Both forks get a single fast, 240-token vote tool request with an explicit instruction to cast now. Only one receives its own interrupted draft. Record the separately submitted votes and incremental wall time. A forced finish on a saved draft is a distinct policy from a native thinking-enabled submission. It also requires keeping the owner text for reproduction.

```sh
mkdir -p /tmp/135-public/finish
python -m experiments.thinking_finish /tmp/135-public/27b-low.jsonl /tmp/135-owner/27b-low.jsonl /tmp/135-public/finish/results.jsonl /tmp/135-owner/finish.jsonl
```

On the matched timed game all 21 required choices arrived before deadline. Blue won on the second turn with the same opening bridge as 13401. This time neither of the first two removal attempts passed. All three seats were alive at the final vote: both Blues approved and the lone Red rejected. No movement voter needed the fast fallback. One Blue attempted a ballot without its boolean argument and corrected it within the remaining allowance. All seven returned thinking traces attach at the two movement opportunities. The owner's trace was joined to the matching private action receipt by seat, revision, actual output limit, token count and call order, before export. [Referee record](game-768/game.json) · [Thinking-call timings and accepted votes](game-768/movement-thinking.jsonl)

The 178.61 seconds include the changed removal discussions and extra living voter. The fast game used 150.93 seconds for 16 required choices. One game with different subsequent actions cannot establish a general throughput or win-rate effect.

### Directed-route transfer

All four 9B voters rejected the outward step on both budget settings. That serves Blue on the two-move short board and Red on the five-move detour, for 2/4 at each setting. All eight votes were explicit. The fast condition took 6.98 seconds per decision and the 1,536-token condition took 8.67 seconds. A permanent dead end on the proposed landing was tractable with thinking on this panel. Choosing between two future directed routes with opposite consequences remained difficult.

At 3,072 tokens the 27B Blue trap voter rejected the step after 2,524 tokens and 98.38 seconds. Red spent 2,715 tokens to request the board, then exhausted the remaining 357 without voting (121.10 seconds total). We stopped escalating because either call already exceeded a normal 60-second live decision before accounting for shared inference or the other seats.

The fast finish made all eight independent submissions across four positions and two conditions. Restricting the seat to the voting tool with no draft already gave 3/4 team-serving ballots. Returning the exact capped 1,536-token draft gave 4/4. Only the Red trap ballot changed: it approved the dead end after seeing its own draft. Incremental finishing time averaged 2.26 seconds with the draft; preparing it had already cost 59.79 seconds on average. The no-draft finish averaged 2.71 seconds and needed no preparation. A finish with a draft cost about 62 seconds end to end under these conditions. Neither policy was tested on a full 27B social table. [Matched finish receipts](finish/results.jsonl)

For this workstation, a 1,536-token allowance for 9B movement ballots is a useful experimental setting. The real-clock pilot used 768; the four frozen 9B seats all finished at 1,536. The harder route comparison and the small, correlated panel argue for keeping this optional while testing additional decisions.

### Making seat order visible

For #139 we replayed the four 9B directed-route ballots with the 1,536-token allowance. The revised state supplied at session start and through `get_state()` lists upcoming builders, and the tool descriptions advertise identity and order. Seat and team were already present. On both boards P3 is the voter and P0 built. Only P1 and P2 can still build on the short board. On the detour board P3 can expect another build if the game and seat survive. The board, roles, tools available, seed and budget match the earlier trials.

| State shown | Short Red / Blue | Detour Red / Blue | Team-serving submissions | Total generated tokens |
|---|---|---|---:|---:|
| Original | No / No | No / No | 2/4 | 2,453 |
| Upcoming builders visible | No / No | No submission / No | 1/4 | 3,422 |

The three submitted votes repeated their earlier choices. Detour Red identified its own team and considered rejecting the step, then reconsidered until its allowance expired. There was no accepted vote. Mean inference time per decision went from 8.67 to 11.75 seconds. Four correlated decisions with one generation per condition do not establish an effect on skill or speed. The new state makes a table fact available, and the harder route judgment remains open. [Earlier receipts](9b-route.jsonl) · [Seat-order receipts](seat-order/9b-route.jsonl)

To rerun the earlier condition use commit `efb6ff5`; the new condition starts with #139. Use fresh destinations for each condition.

```sh
mkdir -p /tmp/order-public /tmp/order-owner
python -m experiments.ballot_thinking 9b /tmp/order-public/9b-route.jsonl /tmp/order-owner/9b-route.jsonl --budgets 1536 --cases short detour
python -m experiments.thinking_view /tmp/order-owner /tmp/order-view --receipts /tmp/order-public
```
