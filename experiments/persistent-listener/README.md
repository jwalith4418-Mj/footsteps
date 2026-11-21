# An accusation before and after compaction

P3 is Blue and plays two turns through its own authenticated localhost seat link. Its private Ollama conversation starts at setup. P0, P1 and P2 use scripted policies. P0 builds the crossing and proposes the first step. P1 nominates P0, and Red P2 says publicly that P0 voted No on the step and should be removed. In one game P0 actually voted Yes. In the other P0 voted No. The marker advanced in both. The script keeps P0 alive whatever P3 decides.

After the first removal ballot, the runner asks P3 to compact its conversation. The player chooses what to write. The next exchange receives its own summary, rules, current seat identity, state and cursor. P3 gets its own nomination opportunity and can speak again on the following turn. Both games used Qwen3.8 27B RANA, temperature zero, seed one, thinking disabled, an 8,192-token context, a 240-token reply limit, 15-second discussion and 30-second decisions. The model was loaded before the table started.

| Actual first ballot by P0 | P3 on removing P0 | P3’s own nomination after compaction | Voluntary history lookups | Missed decisions | Model requests | Prompt / output tokens | Inference |
|---|---|---|---:|---:|---:|---:|---:|
| Yes, accusation false | No | Passed | 0 | 0/4 | 14 | 39,306 / 576 | 40.4 s |
| No, accusation true | Yes | Nominated P0 and voted Yes again | 0 | 0/5 | 18 | 60,587 / 756 | 80.5 s |

On the false accusation P3's summary correctly recalled the unanimous movement ballot and identified P2's statement as false. On the true accusation P3 publicly supported removal, remembered that P2 spoke against P0 and then voted against removal, and named P0 as the seat it suspected. The model carried that suspicion into its own nomination. It also embellished the evidence in a public remark: it said P0 had proposed a move that kept the marker in place. The marker had actually moved. P0 was Blue in both games; a true claim about a ballot is compatible with a mistaken inference about team membership. P3 eventually approved the winning step onto EXIT in both games. [False accusation game](rana/game.json) · [True accusation game](rana-true/game.json)

This pair demonstrates different votes and different later actions in the presence of different evidence. The first ballot was recent enough to be present in both conversations. Neither run demonstrates voluntary recovery of a forgotten fact. The scripted test exercises independent history lookup of the remark and vote after compaction and across a turn boundary. Each model run used one seat, one floor and a live clock. The model also chose different remarks before the accusation. Removing or nominating P0 has no unique strategically correct answer on the public evidence. Total inference time excludes suspended waits. Prompt totals sum the lengths Ollama reported across calls, including repeated context. [False accusation receipts](rana/calls.jsonl) · [True accusation receipts](rana-true/calls.jsonl)

## Reproduction

From the repository root, run the scripted acceptance sequence and audit the archived ballots, compactions and timings offline.

```sh
python -m unittest discover -s tests -p test_session.py -v
python -m experiments.persistent_listener experiments/persistent-listener/rana
python -m experiments.persistent_listener experiments/persistent-listener/rana-true
```

To repeat with local inference, choose new paths. The full tool trace contains private state and notes. The experiment directory receives the referee game and per-call measurements.

```sh
out=$(mktemp -d)
python -m experiments.persistent_listener "$out/false" "$out/false.private.jsonl"
python -m experiments.persistent_listener "$out/true" "$out/true.private.jsonl" --true-claim
```
