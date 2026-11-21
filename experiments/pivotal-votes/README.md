# Would I cast a different removal ballot?

In the [previous 9901 replay](../voter-perspective/README.md), the model could read “I am the nominee” when asked directly. Every experimental removal vote was No. This study elicits a real ballot and a short private reason, without first asking a comprehension question. It measures whether changing a fact that matters to this voter changes the vote. A board, a seat order and its two option orders are paired observations.

## A vote that decides who gets the final turn

Five seats, three Blue and two Red, are voting on the last nomination of a turn. One tile remains. The shared marker already has a directed step onto EXIT; the compulsory final build cannot close it. The nominee builds next if kept and the following seat builds if the nominee is removed. The focal observer is always Red and knows both builders' teams. Swap their alignments. The observer's own role, seat, floor, public history, hand, proposer and nominee are identical within each pair.

For scoring, the four other current ballots split two Yes and two No, which makes the model's actual submitted vote pivotal. The model cannot see those ballots. Continue each fork through the referee, placing an inertly located open tile on the last draw. A Blue builder proposes EXIT, a Red builder stays. Blue seats support an EXIT proposal; the proposer supports its own proposal. A Blue proposal passes on every tested fork. The two votes therefore give opposite winners under these continuations. We score the nominee separately. Keeping itself leaves the nominee in charge of the final turn. The model is free to vote either way. A missing or unfinished decision earns no hit; an implicit timeout No does not demonstrate a deliberate choice.

| Panel | Turn | Builder | Nominee if kept | Next builder if removed | Red observer |
|---|---:|---|---|---|---|
| East | 1 | P0 | P1 | P2 | P3 |
| North | 2 | P1 | P2 | P3 | P4 |
| West, wrapping around P0 | 4 | P3 | P4 | P0 | P1 |

The two worked north tables show the 27B observer's realized decisions in the original display order. When P2 was Blue it voted Yes and handed P3 the final build. When P2 was Red it voted No and kept P2 in control. Red won both games by staying. All other decisions in these two records are scripted. [Blue nominee](worked/pivotal98-rana-north-blue-nominee.json) · [Red nominee](worked/pivotal98-rana-north-red-nominee.json)

## From the first board to two further seatings

We started with the ordinary ballot, the previously tested explicit first-person relationship and a version that also supplies public next-builder identities. None produced one correct switch across the two rosters in either display order on the east floor. With a direct boolean vote followed by a private reason, 9B did switch in both orders. This changes both ballot encoding and task-specific prompt wording. We froze this interface for north. When it missed there we put each actual vote, removal result and successor on a single row, optionally including the successor's alignment to the extent already known to the voter. We kept the wraparound table for a further check. All inputs to a seat come from its own projection.

| 9B observer | East | North | Wrap |
|---|---:|---:|---:|
| Ordinary ballot | 2/4 | 2/4 | 2/4 |
| Direct boolean ballot and reason | 4/4 | 2/4 | 3/4 |
| One row per ballot, with already-known team | — | 4/4 | 2/4 |

A score of 2/4 is attainable by a constant ballot. The ordinary 9B observer switched correctly in **0/6** roster pairs; the direct ballot achieved **3/6**. The north model sometimes explained both branches accurately and submitted the opposite vote. Naming the successor's team on each row worked on north and failed to transfer to wrap. On east, asking the voter to generate the two successor teams first gave 4/4 observer votes, but only one of the four nominee replies finished. One observer forecast reversed the teams, then the explanation correctly identified them. Receipts distinguish generated forecasts, committed votes and the reply cap. [East interventions](east-direct.jsonl) · [North interventions](north-inline.jsonl) · [Wrap transfer](wrap.jsonl)

We then ran the same frozen boolean ballot in a single 4k model-size block with the installed Qwen3.8 27B RANA quantization. The observer scored **12/12**, switching correctly on all six roster pairs, including reversed displays. The nominees scored **7/12** at the initial 144-token reply cap (eight timely votes). Increasing only the cap to 320 gave **11/12** nominee votes aligned, all twelve timely, with the observer still at 12/12. These short, selected positions are evidence of private roster use. “Remove opponents and keep teammates” would also pass the observer comparison.

## Can a Red player put its team ahead of a teammate?

On the wrap board we fixed the observer's own team, the nominee and its actual alignment, then exchanged the final builders' *programs*. The experiment publicly discloses which seat will stay and which will propose EXIT and vote Yes if it builds. The referee actually plays those programs. These are controlled player policies, not promises or a rule change. The current ballot split remains hidden. Crossing these programs with both rosters creates cases where Red must remove a Red teammate or protect a Blue opponent to win.

| Red observer on the public programs | 9B votes aligned | 27B votes aligned | 9B / 27B correct switches (out of four each) |
|---|---:|---:|---:|
| Direct boolean ballot and reason | 3/8 | 6/8 | 0 / 2 |
| Vote only, final movement voting policy also supplied | 4/8 | 4/8 | 0 / 0 |
| Same vote-only interface, with the computed public winner on each option | 6/8 | 6/8 | 2 / 2 |

**27B twice voted to remove its known Red teammate** when that teammate was programmed to propose EXIT and the replacement would stay. When the programs swapped, it twice voted to keep the same teammate. Its private reasons identified both builders, both actions and the resulting winners. The same model twice failed the inverse case of protecting a Blue opponent: it predicted the replacement would propose EXIT and called that a Red win. One correct conditional policy is stronger evidence than voting along team lines, but it did not generalize to the opposite conflict. The winner labels are an experimental upper-bound aid tracked by [the assistance graduation issue](https://github.com/othercriteria/footsteps/issues/93). [9B program swap](policy-swap.jsonl) · [9B explicit winners](policy-ceiling.jsonl) · [27B program swap and controls](rana-programs.jsonl)

## Back at the original removal ballots

We repeated the previous explicit relationship presentation on all five seats at 9901 event 55 and 8602 event 12. The 27B model cast two Yes votes on each ballot. The 9B model had cast none. At event 55 P4's unsolicited reason for No explicitly described keeping *itself* in play, although its numerical claim was wrong: removing one Blue would leave a 2/2 tie. Both Red seats voted No and their reasons treated keeping a Blue majority as helpful to Red. On the independent relationship quiz, both 27B nominees missed “myself.” The quiz and the actual choice provide distinct evidence. [Archived-ballot comparison](rana-archived.jsonl)

## Whole five-seat table on 9901

A full-table transfer uses the initial 3 Blue / 2 Red deal from the original replay. Every seat uses the same model within a game. The floor uses the earlier assisted `clear` interface and its optimistic routes. All nominations, votes, discards and elimination discussion are model decisions. During removal, both group outcomes identify who builds next if no further player is removed this turn. Outside the calibrated last nomination this is a conditional projection. Each seat casts a boolean ballot and may give a private reason. Floor and removal requests allow 320 reply tokens; the existing ordinary decisions keep their usual limits. The host applies the standard public fallbacks. These games test a model swap with the same seat interface and initial deal. Downstream decisions and draws can diverge.

At event 12 the 27B Red builder P1 chose face 29 with rotation 3 at (−1,−1), permanently trapping the marker away from EXIT. The visible-hand audit confirmed that P1 could also have kept a timely route open. P1's private reason identified the seal and its purpose. Blue P2's random fallback build on turn 3 happened after this position was already lost. There were 25 nomination opportunities and one removal ballot. On turn 5 Red P1 nominated Blue P0. P0 identified itself as the nominee and voted No; both other Blues voted No, both Reds Yes. The nomination failed 2–3. This was natural role-aligned voting during a game, but the vote could no longer change the winner. Red won on turn 6 with all seats still alive. [Complete 27B game](rana-game/five-9901-clear-r320.json) · [Seat receipts](rana-game/five-9901-clear-r320.calls.jsonl)

On the identical initial deal the 9B table reached EXIT in four turns. At turn 2 event 17, Red P1 kept the route open with face 22 at (−1,−1) despite a permanent seal being available. On turn 4 Red P3 proposed the winning step for Blue. All five seats voted Yes. Red P1's reason identified Blue as the immediate winner, then described voting No as moving away from victory. During 15 nomination opportunities this table made 14 nominations. Only three of the 70 removal ballots were Yes; three more timed out as No. Nobody was removed. [Complete 9B game](9b-game/five-9901-clear-r320.json) · [Seat receipts](9b-game/five-9901-clear-r320.calls.jsonl)

| Same 9901 deal | Winner | Nominations / opportunities | Timely decisions / requests |
|---|---|---:|---:|
| 9B | Blue, EXIT on turn 4 | 14/15 | 114/117 |
| 27B RANA | Red, depletion on turn 6 | 1/25 | 51/52 |

The first placements already differ. One game per model shows the decisions each table actually made, with no estimate of model win rates. The final 9B vote gives a concrete follow-up: can a seat distinguish which team wins from whether that outcome is desirable for itself, across both possible proposer teams? [Follow-up experiment](https://github.com/othercriteria/footsteps/issues/101)

## Reproduce

Use fresh output paths. All model comparisons use temperature zero, inference seed one, thinking disabled and the same 4,096-token context. A model decision has 30 seconds; the initial setup loads the model before the 27B block. Reply caps are separate from the context window. A length-capped response is missing even when a partial reply starts with a plausible vote. No hidden ballot, counterfactual winner or full referee record goes to a model seat in ordinary play. Program controls add only the specified public experiment facts. Private reasons are saved separately.

```sh
out=$(mktemp -d)
mkdir "$out/notes"
trial() {
  name=$1
  shift
  python -m experiments.pivotal_votes "$out/$name.jsonl" --private "$out/notes/$name.jsonl" "$@"
}
trial east --panel east --arms ordinary relative turn-order
trial east-direct --panel east --arms binary reason-first forecast-first
trial north --panel north --arms ordinary binary
trial north-inline --panel north --arms inline inline-team
trial north-silent --panel north --arms silent
trial wrap --panel wrap --arms ordinary binary inline inline-team
trial policy-swap --panel wrap --arms binary inline-team --controllers
trial policy-ceiling --panel wrap --arms silent ceiling --controllers

big=footsteps-qwen3.8:27b-rana-layout
for panel in east north wrap; do
  trial "rana-$panel" --model "$big" --panel "$panel" --arms binary
  trial "rana-room-$panel" --model "$big" --panel "$panel" --arms binary --max-reply 320
done
trial rana-programs --model "$big" --panel wrap --arms binary silent ceiling --controllers
python -m experiments.voter_perspective "$out/rana-archived.jsonl" "$out/notes/rana-archived.jsonl" --relative --model "$big"
python -m experiments.pivotal_game "$out/rana-game" "$out/notes/rana-game" --model "$big"
python -m experiments.pivotal_game "$out/9b-game" "$out/notes/9b-game" --model qwen3.5:9b-q8_0
```

For an offline summary, run `python -m experiments.pivotal_votes experiments/pivotal-votes/wrap.jsonl` or substitute any pivotal-ballot receipts file. The summary reconstructs the ballot, plays both continuations through the referee, checks the saved winners and expected vote, and counts complete correct pairs separately from timely individual answers. For the older factual questionnaire use the `task`, `expected` and `answer` fields in `rana-archived.jsonl`. To inspect the role-swapped paths without model inference, run `python -m footsteps replay experiments/pivotal-votes/worked/pivotal98-rana-north-blue-nominee.json` and the adjacent Red-nominee record.
