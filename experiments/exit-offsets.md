# How close can the exit be?

**Keep the first four-seat paper trial at (4, 2).** Use five steps as a candidate minimum for a full-length four-seat social playtest, and keep shorter exits available for teaching and replay fixtures. Five is a participation criterion. Human evidence is still needed to decide how many turns make a satisfying deduction game.

## What geometry guarantees

Let D be the Manhattan distance from START to EXIT. An arrival on turn D requires a successful goalward step on every turn and visits D−1 ordinary floor tiles. Each of the first D−1 builders must place the tile used on their turn. The final builder still places a tile, but can put it anywhere legal because EXIT is already on the floor.

| Distance | What the setup allows |
|---|---|
| 0 | The special tiles coincide. The referee already rejects this setup. |
| 1 | After the mandatory build, the marker can step directly between the two unrestricted tiles on the opening ballot. The table can win before the first nomination regardless of the deal. Declining the proposal or staying remains legal. |
| 2 | One correctly oriented ordinary tile can supply the whole route. In a straight line there is one possible bridge square. On the diagonal there are two. |
| 3 | Even the third builder can place off-route on a shortest win. The fourth seat may vote and nominate without ever building. |
| 4 | All four surviving seats can build on a shortest win. The fourth seat can place off-route and propose entry into EXIT. |
| 5–7 | With four surviving seats, every seat must supply a used tile on a shortest win. At (4, 2) the eight-tile bag leaves two extra turns for delays or a detour. |
| 8 or more | At exactly eight, one stay or rejected movement makes arrival impossible with this bag. Beyond eight, even uninterrupted movement cannot arrive. The referee still resolves play normally. |

These statements concern routes to EXIT. Elimination can end a social game independently. More generally, for P seats, D ≥ P+1 gives each seat a necessary placement on the fastest possible win if everyone survives. Use setup guidance to select for that experience. The existing rules adjudicate all distinct near exits without an exception.

## An exact count and a matched pair

The first builder sees four of the sixteen physical tiles. There are 1,820 equally likely four-tile subsets after a fair shuffle, counting duplicates as separate pieces. For each face we tried each rotation on every legal opening square and checked both directed steps with the board's movement function.

- At (1, 1), 1,820/1,820 holdings contain a bridge. Only the two copies of face 16 and the single face 12 cannot make either turn. Any four-piece holding therefore contains a usable tile.
- At (2, 0), 1,815/1,820 holdings contain a bridge. Faces 153 and 74 also fail the straight-through requirement. Any four of these five unsuitable pieces account for the five misses.

This counts an available placement. A player can place differently, propose staying, or vote against it.

In deal 1040 the first builder sees **74, 16, 16, 12**. Against a diagonal exit the route player walks (0, 0) → (1, 0) → (1, 1). Against the straight exit it walks (0, 0) → (1, 0) → (1, 1) → (2, 1) → (2, 0). Reproduce either full referee record for the viewer:

```sh
python -m experiments.offsets record --goal 1 1 --seed 1040 --policy route --out /tmp/diagonal.json
python -m experiments.offsets record --goal 2 0 --seed 1040 --policy route --out /tmp/straight.json
python -m footsteps view /tmp/diagonal.json --seat 0 -o /tmp/diagonal.html
python -m footsteps view /tmp/straight.json --seat 0 -o /tmp/straight.html
```

## What four cooperating builders did

We played 5,200 games across 13 offsets using the printed sixteen-piece mix, four two-tile private hands, and eight tiles left in the bag. Each offset and policy used the same 200 shuffled deals (seeds 1000–1199). Four good players rotate through the builder seat. All use the same policy within a game, accept legal proposals, and pass nominations. Each builder's choice receives its own hand and public floor. The referee alone samples from the bag. Shuffling, drawing and policy choices use separate random streams. Once policies discard different tiles, later draws may diverge.

| Exit | Exit-aware wins / 200 | Route-search wins / 200 | Route wins at earliest turn | Route median winning turn |
|---|---:|---:|---:|---:|
| (1, 0) | 200 | 200 | 200 | 1 |
| (1, 1) | 200 | 200 | 200 | 2 |
| (2, 1) | 199 | 200 | 108 | 3 |
| (3, 2) | 197 | 194 | 77 | 6 |
| (4, 2) | 198 | 184 | 74 | 7 |
| (6, 0) | 189 | 192 | 189 | 6 |
| (4, 4) | 190 | 45 | 45 | 8 |

At (2, 1), the exit-aware policy finished before the fourth seat built on 199/200 deals. Route search did so on 108/200. At (4, 2), route search won after turn six on 110 deals. Simply moving EXIT to (6, 0) at the same distance reduced that count to three. Both distance and shape deserve a place on the setup sheet.

Counts are conditional on this one tile mix, these policies and the fixed eight-turn deadline. Shortening the distance also increases slack. Paired configurations reuse the same 200 deals. A hidden-role table adds adversarial choices, vetoed moves and eliminations. Its win rate and engagement still need direct observation. For a human comparison, try (3, 2) alongside (4, 2) with the loose pieces. Record whether each surviving seat built a tile the group used and what board evidence existed at the first nomination.

The full tables include wins before the fourth build for every offset, plus the zero-win (9, 0) control. The CSV records each game’s goal, seed, policy, outcome and terminal turn. [All counts](offset-counts.md) · [Raw outcomes](offsets.csv) · [Paper mix](../playtest/README.md) · [Policy definitions](README.md)

```sh
python -m experiments.offsets run --out /tmp/offsets.csv
cmp /tmp/offsets.csv experiments/offsets.csv
python -m experiments.offsets summary /tmp/offsets.csv > /tmp/offset-counts.md
cmp /tmp/offset-counts.md experiments/offset-counts.md
```
