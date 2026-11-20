# Can a builder distinguish placement from movement?

In a five-seat game, a builder correctly said the new edge was blocked and incorrectly said the marker was on its origin. The two questions measure different things. A private correction fixed the marker answer. The model still built the same tile. [Turn-by-turn checks](checks.csv) · [Game record](table/8602-bad1+3.json) · [Design issue](https://github.com/othercriteria/footsteps/issues/80)

## Frozen builds

We restored Blue P4 immediately before event 42 of the EXIT-centered 8602 game, and Red P2 immediately before event 24 of the guest game. For Blue, success means building a tile that permits a first step with an optimistic route to EXIT in the remaining turns. For Red, success means closing every route out of the marker’s component. Both opportunities have independently verified examples. We presented each seat with the original legal menu and with its order reversed. Those four decisions per condition represent two distinct positions. [Blue continuation](../exit-origin/counterfactual-8602.json) · [Red guest game](../blind-guest/game/1244867160-bad1+2.json)

The joint prompt requests all fields together, including indices for the tile, rotation and both squares. The staged prompt first selects an ordinary provisional build. A short second prompt lists adjacent origins by coordinate, their outgoing sides, the direction to the new tile, its rotated entrances and the actual marker square. Both versions allow one correction with referee feedback. The staged version fixes the provisional build for the duration of the check. An ordinary decision takes one model call, a staged decision takes two, and a correction adds one.

| Free build interface | Accepted first try | Accepted within budget | Achieved team tactic |
|---|---:|---:|---:|
| Ordinary, either run | 4/4 | 4/4 | 0/4 |
| Joint, edge | 0/4 | 0/4 | 0/4 |
| Joint, edge and marker | 0/4 | 0/4 | 0/4 |
| Staged, edge | 2/4 | 4/4 | 0/4 |
| Staged, edge and marker | 2/4 | 4/4 | 0/4 |

Four additional questions fixed the origin, new square, face and rotation on Blue’s floor. In two, the marker occupied the origin. In two, the origin was the tile north of the marker. In each pair face 58 was placed east of the origin, once with the west entrance open and once with it closed. Only the judgments were left to the model.

| Fixed edge interface | All required answers correct first try | Accepted after at most one correction | Marker answer correct first try |
|---|---:|---:|---:|
| Joint, edge | 2/4 | 2/4 | — |
| Joint, edge and marker | 1/4 | 3/4 | 2/4 |
| Staged, edge | 2/4 | 4/4 | — |
| Staged, edge and marker | 2/4 | 4/4 | 4/4 |

The joint prompt elicited “marker on origin” on both remote builds. With the staged prompt, the model located the marker in all four positions but answered that every edge was open. Its two corrected edge answers followed feedback that explicitly described the blocked side. This makes first answers the more informative measure of unaided reading. [Joint attempts](joint.csv) · [Staged attempts](staged.csv)

## Full five-seat game

We repeated the EXIT-centered 8602 deal with each staged interface. Three Blue and two Red seats used the same model, public discussion and assisted voting policy as the ordinary table. Both checked runs had identical public events and remarks. First-pass accuracy on the edge question was 4/8 in each. With the extra question, the first marker answer was correct on 7/8 builds. On turn seven the marker was at (−1, −1) and the builder chose (−2, −1) as origin. Only the marker assertion needed correction. Both interfaces ended up committing six model placements and two random fallbacks (turns three and eight). Fallbacks consume randomness from the same stream as later draws, so matched setup and seed do not guarantee identical later hands across ordinary and checked tables.

| Interface | Placements accepted first try | Corrected placements | Random placements | Final marker | Result |
|---|---:|---:|---:|---|---|
| Ordinary | 8 | 0 | 0 | (−2, −3) | Red by depletion |
| Edge | 4 | 2 | 2 | (−1, −1) | Red by depletion |
| Edge and marker | 3 | 3 | 2 | (−1, −1) | Red by depletion |

There was also a genuine social consequence on turn five. The assisted movement ballot split 3–2 along team lines for a step east. Blue P0 then publicly cited P1’s dissent. Four seats removed Red P1, including fellow Red P3. All five elimination votes came from the model. On the ordinary table all five seats survived. A single shared deal gives us an example to inspect, with little basis for estimating a change in win rate. [Ordinary record](../exit-origin/social/8602-bad1+3.json) · [Edge record](edge-table/8602-bad1+3.json) · [Edge and marker record](table/8602-bad1+3.json)

Keep the second question available as a private diagnostic. The next tactical experiment should give the player one opportunity to revise the proposed tile, rotation or square after reading its local consequences. Compare against a player given the same number of calls, and score the committed build and fallbacks on held-out positions. [Guest tactic transfer](https://github.com/othercriteria/footsteps/issues/76)

## Reproduce

Run with local Ollama serving `qwen3.5:9b-q8_0`. These runs used a 4096-token context, temperature zero, seed one and thinking off. Use fresh output paths. Model or backend revisions can affect the replies.

```sh
work=$(mktemp -d)
python -m experiments.placement_check "$work/staged.csv"
python -m experiments.placement_check "$work/joint.csv" --joint
for check in edge edge-and-marker; do
  python -m experiments.social_evidence --roles GBGBG --paired-fifth-hand --color-teams \
    --arm receipt --debate --model-floor --outcome-policy --kit-counts 29 29 \
    --kit-seed 8700 --seeds 8602 --goal 2 2 --action-brief --exit-origin \
    --placement-check "$check" --out "$work/$check" --private-notes "$work/private-$check"
done
python -m experiments.social_summary "$work"
python -m footsteps view "$work/edge-and-marker/8602-bad1+3.json" --omniscient \
  --notes "$work/private-edge-and-marker/8602-bad1+3.jsonl" -o "$work/8602.html"
```

The private `.checks.jsonl` file contains the attempts and referee feedback for each turn. The published counts retain the first answer’s correctness, attempt count and fallback indicator. The ordinary game record and the checked game records replay without those files.
