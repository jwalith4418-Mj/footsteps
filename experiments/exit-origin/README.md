# Using EXIT as the coordinate origin

On the paper layout, a table can call START (−4, −2) and EXIT (0, 0). A marker at (−2, −1) needs at least three steps. East and north still have their usual meanings. A missing entrance can still make a three-step approach impossible.

We tested three increasingly demanding questions with `qwen3.5:9b-q8_0` (local model ID `a8ee95bc3592`, temperature 0, seed 1, thinking off). The model read a displacement, chose a legal move on a directed floor, and played complete games. Coordinate translation preserves tile masks, geometry, legal menu order, initial hands and voting rules. Match results by physical square after undoing the translation. [Issue and initial panel](https://github.com/othercriteria/footsteps/issues/78)

## Reading a distance

Given only the marker and EXIT coordinates, ask for the minimum number of cardinal steps ignoring arrows and missing floor. The primary panel has two positions from the last five-seat experiment, a marker beyond EXIT on both axes, and an arrival. Each has an east–west reflection. All prompts in this panel used 71 input tokens.

| Position | Correct distance | START origin, original / reflected answers | EXIT origin, original / reflected answers |
|---|---:|---|---|
| Short floor, marker at (0, −1) | 5 | 4 / 4 | 5 / 5 |
| Long floor, marker at (−1, 1) | 6 | 5 / 7 | 6 / 6 |
| Marker beyond EXIT | 4 | 3 / 3 | 4 / 4 |
| Already at EXIT | 0 | 0 / 0 | 0 / 0 |

That is 2/8 versus 8/8. The reflected arrival yields an identical EXIT-centered prompt. The six nonzero examples account for the entire difference. [Paired answers](bounds.csv)

A seeded confirmation used four opening markers at START and eight later or hypothetical positions. We added a third presentation that puts the *current marker* at (0, 0). On openings, the model got 4/4 in every frame. On the other eight, it got **1/8 with START fixed, 8/8 with EXIT fixed, and 8/8 with the marker fixed**. Either endpoint at zero simplified this arithmetic for this model. A fixed EXIT also gives different players stable square names throughout the game. A marker-relative square name would change after each successful step. Human ease of use remains a playtest question. [Confirmation answers and coordinates](bounds-check.csv)

## Choosing a step

The four published solitaire stalls and four reflected forced detours use the [existing movement criteria](../skill_probe.py). Ask the ordinary unaided solitaire adapter to pick a legal action with its hand, oriented floor, marker, EXIT and legal literals visible. Present the menu in both orders.

| Frozen choice | START origin | EXIT origin |
|---|---:|---:|
| Advance to a closer tile outside permanent confinement | 7/8 | 7/8 |
| Take the only viable detour when stepping closer is fatal | 5/8 | 4/8 |

On the detours, changing the origin rescued one move and spoiled two. The other five choices were identical. A closer open landing is a local progress criterion for the recorded stalls. It does not certify a win, particularly in the last-turn example. [Choices in common referee coordinates](moves.csv)

## Complete games

On four fresh solitaire deals (9101–9104), the same unaided model played construction, discard and movement in both frames. Each deal had two tiles in hand, ten tiles after the deal, and EXIT four east and two north. Calls started with a fresh context. The starting frame alternated by seed. The referee recorded moves in the frame used at the table. All eight games ended on turn ten by depletion with zero fallback decisions.

| Seed | Final distance, START origin | Final distance, EXIT origin |
|---|---:|---:|
| 9101 | 5 | 5 |
| 9102 | 6 | 6 |
| 9103 | 5 | 5 |
| 9104 | 3 | 5 |

Both frames had two certified endgame traps. For 9103 the trap occurred only with EXIT at the origin, and for 9104 only with START at the origin. This panel supports EXIT coordinates as a reading aid. It supplies little evidence of a playing-strength gain. [Outcomes](solitaire/games.csv) · [START-origin records](solitaire/start) · [EXIT-origin records](solitaire/exit)

We also replayed the five-seat 8602 deal from a new table with EXIT at (0, 0), START at (−2, −2), three Blue and two Red. Both this table and its [START-origin counterpart](../action-language/short-actions/8602-bad1+3.json) took one step physically south, removed nobody and lost to depletion. The southward step came on turn one in the original and turn five in the new game. The two tables had different discussions and histories from their first placement. [EXIT-origin game](social/8602-bad1+3.json) · [Social decisions](social/choices.csv)

**Turns four and five show exactly where the lower bound matters.** On event 34 all three Blue seats declined a move from (−2, −2) to (−2, −3). Four turns would remain. Staying could still work, while five squares would put EXIT out of time. The assisted payoff policy cast those ballots. On event 45 the table unanimously accepted the same move. By then only three turns would remain. Staying four squares away or stepping five squares away both assured Red a win. These votes came from the model. P0 described the southward step as moving closer.

The last chance was Blue P4's placement on event 42. Four legal face/rotation pairs at (−1, −2) kept a timely route possible. P4 instead played face 100 at (−1, −1). One referee-checked alternative uses **the same draws and returns** as the played game. P4 places 58 at (−1, −2), P0 places 22 at (−1, −1), then P1 places 37 at (−1, 0). Each proposes a step onto that tile. P2 can then propose entering EXIT. All rotations are zero. This is a constructed continuation with everyone passing on nominations and Blue approving each proposal over Red opposition. It requires Red P1 to make the helpful third build and proposal. It establishes that the floor and supply allowed a win. [Counterfactual record, branching after event 41](counterfactual-8602.json)

## Reproduce

Run from the repository root with local Ollama serving the model above and use fresh output paths. Run the jobs sequentially on a shared GPU. The probe and solitaire adapter use an 8192-token context, and the social seats use 4096. The game records contain the realized deals and draws. The CSVs describe the observed model choices. A different model build or inference backend may choose differently.

```sh
work=$(mktemp -d)
python -m experiments.exit_origin bounds "$work/bounds.csv"
python -m experiments.exit_origin bounds-check "$work/bounds-check.csv"
python -m experiments.exit_origin probes "$work/moves.csv"
python -m experiments.exit_origin games "$work/solo"
python -m experiments.social_evidence --roles GBGBG --paired-fifth-hand --color-teams \
  --arm receipt --debate --model-floor --outcome-policy --kit-counts 29 29 \
  --kit-seed 8700 --seeds 8602 --goal 2 2 --action-brief --exit-origin \
  --out "$work/social" --private-notes "$work/private"
python -m footsteps replay experiments/exit-origin/counterfactual-8602.json
```

At a new human or model table, `python -m footsteps table --exit-origin --save /tmp/exit-table.json` chooses one frame for everyone, including the record and replay. Solitaire also accepts `--exit-origin`. The version-2 record carries the actual starting square. Existing version-1 records always start at (0, 0). The same base-1 referee handles both.
