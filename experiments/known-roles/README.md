# What does a model know about the other seats?

The rulebook and private player prompts now distinguish the common information rule from the identities each seat is told. Every player knows the starting counts, knows who receives which information, and knows the others know this too. A bad player receives its complete team lineup and can identify every good seat. A good player receives their own alignment and can reason from counts and public play. The host derives each private briefing from that single seat's view. [Setup rules](../../docs/rules.md#setup)

Before asking a model to act, we asked it to identify P2 and P3 on an unchanged opening floor, and separately to say whether bad players' information is common knowledge. Qwen3.5 9B saw the same deal and public action in four seats with lineups BGBG, GBGB and BGGG. P0 and P1 answered independently in each layout. The original condition omits the two added information fields. The explicit condition includes them. The role quiz used temperature zero, inference seed one, thinking disabled and fixed answer order. Each cell reuses six questions across related layouts. [All replies](../role-knowledge.csv)

| Question | Original correct | Explicit correct |
|---|---:|---:|
| Bad observer identifies another player's actual team | 2/6 | 6/6 |
| Good observer recognizes the other player's alignment is unknown | 3/6 | 5/6 |
| Observer recognizes the common information rule | 6/6 | 6/6 |

The remaining good error was in the lone-bad game. P1 declared P2 good despite knowing only that one of the other three seats was bad. Passing the yes/no common-knowledge question by itself was an especially weak check: the original player answered it correctly while often misidentifying individual seats.

On the 8201 self-removal ballot, the clarified brief with human motives still approved removal in both menu orders. The assisted policy rejected it twice with the model choosing. On the quiet good opening, it passed in one of the two orders. On the repeated six-turn cross-play deal, bad survived the opening twice and won both games with policy assistance on decisive choices. Identifying teammates and acting effectively toward a team objective deserve separate tests. [Prior comparison](../social-behavior/README.md) · [Tight games](tight-assisted/)

The role quiz uses the live model request constructor. Regression tests compare complete prompts after exchanging two other hidden roles, check the bad roster after removal, and inspect the private request used to generate a public statement. A good observer's ordinary, assisted, and speaking requests remain identical across a hidden swap. Only the speaker's submitted words enter the table record.

## Reproduce

The seat wording used in the matched choice and game files is pinned at `2cb881c`. The compact prompt also displays the initial player count alongside the initial bad count in the release. The standard role quiz already includes both counts.

```sh
out=$(mktemp -d)
notes=$(mktemp -d)
python -m experiments.role_probe --out "$out/knowledge.csv"
for arm in human assisted; do
  python -m experiments.behavior_probe --strategy "$arm" --out "$out/$arm.csv" --private-notes "$notes/$arm.jsonl"
done
python -m experiments.behavior_crossplay --strategy assisted --seeds 8411 --store 6 \
  --out "$out/tight-assisted" --private-notes "$notes/tight-assisted"
```

To play a four-seat model game with actual bad teammates, use an explicit seat layout. The deal, ballots and role disclosure follow base-1. The chosen lineup belongs to the postgame record. During play each agent receives only its own seat view.

```sh
python -m experiments.social_evidence --roles GBGB --arm receipt --debate --model-floor \
  --outcome-policy --seeds 8602 --out "$out/two-bad" --private-notes "$notes/two-bad"
python -m footsteps view "$out/two-bad/8602-bad1+3.json" --omniscient \
  --notes "$notes/two-bad/8602-bad1+3.jsonl" -o "$notes/two-bad.html"
```
