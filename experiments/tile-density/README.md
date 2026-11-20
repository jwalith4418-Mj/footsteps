# How much does a fixed tile supply change building?

A sixteen-tile supply has 64 possible entrances and 64 possible exits. We chose exactly 29 of each for the sparser supply (45.31%) and 35 of each for the denser supply (54.69%). For each kind of permission we independently shuffle all 64 labelled tile sides and enable the first slots up to the chosen count. Every subset of the requested size is equally likely. One tile may have no exits, and an entrance and an exit can share a side. All comparisons using the same mix seed reuse the two permutations. The sparse balanced supply is therefore a subset of the dense supply, side for side.

The printed supply contains 32 entrances and 26 exits, also 58 permissions. That prompted a third condition with those exact counts redistributed uniformly. The experiment measures how much the total budget matters and whether moving three permissions between entrances and exits at that budget appreciably changes these policies' results.

## Four cooperative builders

The exit is four east and two north. Four private two-tile hands leave eight turns. Everyone approves movement and passes on nominations. Rotation, draws, discards and movement follow base-1. For each of 100 fresh mix seeds (8700–8799), we used eight unique deal seeds and both the local exits policy and the route search. Each policy played all three supplies on each deal. Streams for the deal, draws and player choices are distinct. Divergent decisions can change later draws. The 800 deals share 100 kits per condition.

| Exact entrances / exits | Distinct forward opening builds, mean | Exits wins / 800 | Route wins / 800 | Exits turns missing a forward build when needed | Route turns missing one |
|---|---:|---:|---:|---:|---:|
| 35 / 35 | 13.22 | 793 | 750 | 36 / 4,022 | 15 / 3,222 |
| 29 / 29 | 9.83 | 734 | 699 | 296 / 4,192 | 125 / 3,283 |
| 32 / 26 | 9.96 | 728 | 703 | 332 / 4,195 | 140 / 3,285 |

A forward build is a distinct (square, oriented face) that the marker could enter immediately, closer to EXIT, with a further goalward exit. That onward edge may face empty floor. We count a turn as needing one when no closer built step exists. All 800 opening hands had at least one forward build under each exact supply. Later on, the local policy finished sealed in 14 sparse games versus zero dense ones. Among local-policy wins, 733 of 734 sparse wins and 792 of 793 dense wins still came on turn six. Scarcity changes whether this builder succeeds more than how long its successes take.

Going from dense to sparse changed 63 local wins to losses and four losses to wins. Route changed 88 wins to losses and 37 losses to wins. The policies pick among changing menus and can use newly available openings poorly. For inspection, deal 69617 flips a local result one way and deal 70008 the other. The [fixed-count records and deal rows](fixed/) include each supply for both deals.

## Why fixing the count matters

For comparison we also ran the old independent per-side generator at probability .55 and .45 on the same uniform draws. Across the same 100 fresh kit seeds, local wins fell from 788 to 727 of 800, and route wins from 736 to 703. Reusing only seed zero, which produced the printed kit at .55, gives a much larger change. Lowering its threshold removes fifteen of its 58 permissions, leaving just 22 entrances and 21 exits. On 200 matched deals of that one kit, local wins fell from 193 to 139, route wins from 189 to 119. That single comparison makes the .45 treatment considerably sparser than intended. [Threshold deal rows](deals.csv)

The 29/29 supply leaves room for competent cooperative building while making imperfect later hands more common. The two 58-permission conditions are close in this sample. None of the 8,800 cooperative games involved vetoes, intentional obstruction, or elimination. A social game on 29/29 can test whether harder construction creates new evidence or merely makes ordinary moves look suspicious.

## Reproduce

Run from the repository root. Each run creates a new output directory. Each saved example is a complete referee record that can also be opened in the transcript viewer.

```sh
python -m experiments.tile_density run /tmp/footsteps-fixed --fixed
python -m experiments.tile_density summary /tmp/footsteps-fixed/deals.csv
python -m experiments.tile_density run /tmp/footsteps-threshold
python -m experiments.tile_density summary /tmp/footsteps-threshold/deals.csv
python -m footsteps replay experiments/tile-density/fixed/deal-69617-p29-29.json
python -m footsteps table --kit-counts 29 29 --kit-seed 8700 --save /tmp/footsteps-table.json
```

The same two kit options work with `python -m experiments.social_evidence`. Set both the kit seed and the deal seed to reproduce a social setup. A replay stores the actual faces, hands and store.

In the [first four-seat social comparison](../four-seat/README.md), a good listener cast the pivotal vote to remove another good player on the 29/29 kit. The printed kit produced fourteen failed nominations.
