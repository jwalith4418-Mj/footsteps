# Can a model play through a private, rotatable hand?

A builder can hold two copies of face 33, turn the second copy clockwise, look at a square, and place that copy. Does the model carry that intention into play? We ran Qwen3.5 9B Q8 on the same seats with an indexed menu, literal tool calls, and private piece handles that keep their orientation. All three interfaces allow all four rotations and the same legal placements.

## What was compared

| Arm | What a builder can do |
|---|---|
| Menu | Submit indices into the legal face, turn and square lists as structured JSON. |
| Direct | Call `place_tile(piece, rotation, x, y)`. Optionally preview the same arguments, read the result, and retry. |
| Hand | Call `orient_tile(piece, rotation)` to set an absolute clockwise orientation. Preview or commit a piece at literal coordinates using its current orientation. |
| Literal / single | Commit literal coordinates, a piece and rotation in one response, using structured JSON or a single native call respectively. |
| Draft | Use the private hand, preview a placement and call `commit_preview()` to accept exactly that candidate. Each new preview supersedes the previous one. |
| Informed | The draft preview also reports whether the build permanently confines the marker, and whether staying or taking a legal step leaves any optimistic route in the remaining time. The search treats unbuilt squares as fully open and caps the horizon at 16 further steps. |
| Fit | The hand gains `inspect_rotations_at(piece, x, y)`, which shows all four compass readings and direct marker access for one chosen piece and square. The held orientation survives inspection. |

The native loop permits six replies under one 30-second decision deadline. Its last reply must commit. A player can build remotely or close an edge under every full interface. A successful preview explains which steps the marker *could* take after construction. Only a subsequent proposal and ballot can actually move it. Handles distinguish duplicate private copies. Placement and discard resolve to ordinary base-1 events. [Live seat protocol](../../docs/table.md#native-action-calls-and-private-hand-pieces)

## Frozen decisions

The eight port puzzles request a specific entrance and exit on a straight or an elbow. Each was presented twice with reversed option and piece order. The seven archived tactical positions use the earlier Blue and Red prefixes and the turn-three escape on deal 8602. Blue scores for building a board with an immediately legal step and an optimistic onward path within the remaining turns. Red scores for permanently sealing the reachable component. Each is a sufficient tactical witness for this probe. Neither test measures the value of every legal strategy. Missing commitments score zero. A uniform pick across distinct faces, turns and legal squares has 0.91 expected hits over 14 archived presentations and 0.55 over eight fresh role swaps. [Position sources and scoring](../rotation_probe.py)

| Interface | Requested compass ports / 16 | Tactical witnesses / 14 | Tactical commitments / 14 |
|---|---:|---:|---:|
| Menu | 5 | 0 | 14 |
| Literal JSON, one call | 4 | 0 | 13 |
| Native commit, one call | 4 | 2 | 9 |
| Native direct with retry/preview | 11 | 4 | 14 |
| Private hand with retry/preview | 11 | 4 | 13 |

The direct and hand interfaces found exactly the same two tactical plays in both presentation orders. On the 8102 floor, role-swapping the builder left the hand interface choosing printed face 107 at (2, 0) in all four presentations. That build scores for Blue. Red can seal the same square with another face. Scoring four presentations amounts to finding two distinct plays, and does not establish role-sensitive strategy.

The hand called `orient_tile` on 9/16 port readings and 0/14 archived tactical decisions. It obtained a valid preview on 13/14 tactical decisions. At the turn-three escape, the live marker was at (−1, −2). The model could save it at (0, −2) with face 37 at turn 3, 82 at turn 2, or 178 at turn 2. In forward order it previewed printed face 178 at (−2, 0), saw the marker could not enter, then placed it there. Four of the ten direct-arm misses could have been repaired by turning the same tile on the chosen square. Five required choosing a different square and one required a different piece on that square.

In both the direct and hand arms, all 12 tactical commitments preceded by a successful preview used the exact handle, square and rotation in the last preview. That addresses a concrete failure of the earlier lookup interface, where the model could inspect one face and submit another by index. It also explains why requiring confirmation did little here. Both draft and informed still scored 4/14, with 10 and 13 commitments. In the Blue-8602 forward case, the informed builder received five consecutive previews saying that no route remained in time. It committed the fifth. The decision record distinguishes failing to use a warning from failing to receive it.

## Fresh role swaps

Before running a model on them, we selected a prefix from each of the first four qualifying cooperative paper-kit deals starting at seed 9600. Each prefix has at least one successful build for either role, accounting for at most a third of legal builds per role. We gave the same board and hand to the same seat twice, swapping its team, and alternated presentation order across deals. Seeds 9600–9603 qualified at event counts 10, 27, 35 and 10. Each included a blank tile. This deliberately selected sample is a test of tactics with known witnesses.

Menu, direct and hand each scored 2/8, all on Blue. Their accepted commitments were 8/8, 7/8 and 5/8 respectively. The choice of interface changed *which* Blue plays succeeded. Red missed all four opportunities with each interface. A follow-up control gives the builder only the one square shared by all successful Blue and Red plays on that floor. It tests piece choice and rotation conditional on knowing where to look. Its restricted square list makes it unsuitable for estimating ordinary table performance.

Restricting the same hand interface to that square yielded 4/8 (two Blue and two Red), including seven accepted commitments. For the three floors where both seats committed, changing the builder’s role left its piece and rotation identical every time. Face 29 helped Blue on seed 9600, face 150 sealed the marker for Red on 9601, and face 41 helped Blue on 9602. The extra Red hits therefore give little evidence of deliberate sabotage. The intervention helps distinguish “played a winning build” from “changed the build in pursuit of the assigned objective.”

The optional four-orientation lookup was requested on **22/22** archived and fresh tactical decisions. The fit arm secured 3/14 and 1/8 tactical witnesses respectively, with 6/14 and 3/8 timely commits. On fresh seed 9603 both roles turned H4 (face 243) twice clockwise. Blue ran out of time. Red committed it on the disputed square, which satisfied the Blue criterion. Lookup frequency measures demand for the information. The committed choice and deadline show whether the model could use it.

## First replies under the clock

Across the ordinary native direct and hand arms, every initial reply on the tactical panels reached the 320-token cap without making a call (44/44). Retries often worked. We compared just the first reply on Red-guest, Blue-82-escape, and both seat assignments of fresh floor 9600. The original prompt produced 0/4 calls. Raising the cap to 768 produced 1/4. Appending a short user message after the state, “Send exactly one native function call now,” produced 4/4. Median wall times were 11.65, 14.93 and 4.89 seconds respectively. The measurement counts a single advertised function name. With the full decision loop, the cue delivered 14/14 archived and 8/8 fresh commitments. It matched the ordinary hand's 4/14 archived witnesses, slipped from 2/8 to 1/8 on fresh decisions, and fell from 11/16 to 5/16 on port readings. On the port tasks it used a private turn only twice, down from nine times. A faster first reply can also mean prematurely placing the printed face. Keep the cue in the experiment harness.

## Complete social tables

Every table starts with deal 9501, three Blue seats and P1 Red, with EXIT two east and two north from START. The 16-tile supply contains exactly 29 entrances and 29 exits. Eight tiles remain after dealing. The same model plays every seat, including both ballots and nominations. The nominator can make a separate public argument before the removal ballot. Seats receive their own authenticated-view projection and twelve recent history entries. The experiment uses the live table's submission and fallback methods in process. Each model decision gets its own real 30-second budget and the table advances on a virtual clock, so concurrent ballot latency on a live server can differ.

The build-only comparison changes the builder's interface and retains the shared structured client for all other decisions. A fourth table uses the hand for construction and native actions for every other mandatory choice. The ordinary client requests a private explanation and native commits accept an optional one. After the first divergent discard or public fallback the same chance seed may draw different faces. The saved records permit exact referee replay.

| Social interface | Marker steps | Closest distance to EXIT | Ending square | Builds with an available step |
|---|---:|---:|---|---:|
| Menu | 1 | 3 | (−1, −2) | 1/8 |
| Native direct for building | 2 | 4 | START | 2/8 |
| Private hand for building | 8 | 3 | START | 8/8 |
| Private hand and all native decisions | 7 | 3 | (−1, −2) | 8/8 |

Red won all four tables on the eighth turn with every seat alive. The menu table was permanently confined after turn four. The direct table’s only nonzero placement rotation came from the host after a turn-four timeout. The private-hand tables produced a walkable step on every turn and spent their time retracing floor. One deal cannot estimate how often either team wins.

**Turn 2, event 16, all-native table.** P1 Red proposes walking from (−1, −2) back to START (−2, −2), one square farther from EXIT. All three Blue seats vote yes. P1 votes no on its own proposal. All three Blue private notes describe the return as progress. All seven movement ballots in the game have those identical seat votes, even as the direction alternates. The marker takes seven steps and finishes one square from START. All 115 mandatory native decisions arrived, across every stage. This provides a public paired edge for the existing ballot-tool and role-sensitive construction issues. [Referee record](games/9501-hand-all.json) · [Call receipts](games/9501-hand-all.calls.jsonl) · [Ballot follow-up](https://github.com/othercriteria/footsteps/issues/55#issuecomment-7051120778) · [Construction follow-up](https://github.com/othercriteria/footsteps/issues/76#issuecomment-7051027660)

### Two-turn solitaire control

We also gave each builder interface the same solvable complete game on two headings. EXIT is two steps away, every available piece is face 65 (printed entrance north, exit south), and there are exactly two movement opportunities. The solution is to build the midpoint on turn one, walk there, then enter EXIT on turn two. The east version requires turn 3, and the north version turn 2. The referee accepts both lines. All six model games lost, every placement was timely, and all twelve placements used printed orientation. In the north hand replay the player built two legal southbound steps and took both, increasing its distance from two to four. There was no opposing player and no choice of face to distract it. These deliberately simple deals test whether a player applies rotation spontaneously to a stated game objective.

To separate reading the objective from pursuing it, we returned to both initial snapshots. In a fresh query Qwen correctly calculated that the wrong-way step increases Manhattan distance from two to three, then answered on **both** boards that this line could still win with only one step left. Asked to plan backward from winning, it proposed START itself as the necessary first landing in both cases, with turn zero. It located EXIT correctly in the north version and misplaced it by one square in the east version. Giving those plans back to the native builder produced neither winning placement. The prediction, planning and placement queries used separate contexts. Only the builder received the model's own proposed plan. [Private-view probe and actual calls](games/corridor-goals.jsonl)

Giving the same builder a verified first square and rotation yielded 2/2 winning openings. Both headings show the same sequence of operations. They each preview the unturned piece, orient it, preview again, and commit the correct piece at the midpoint. This makes a goal-to-first-action failure observable independently of the ability to work the controls. In the separate full-game intervention we supplied only the opening placement. The player won both games, independently proposing and approving the two correct steps and handling the intervening return and build. [Verified plans and actual calls](games/corridor-verified.jsonl) · [Goal-pursuit follow-up](https://github.com/othercriteria/footsteps/issues/88)

## Reproduce

The commands create new files and take time on a local Ollama server. Use a new output directory per run. To inspect the saved evidence without a model, run `python -m experiments.native_summary` at the repository root. Every JSONL decision records the actual commitment or failure and each private operation the native model attempted. Complete game records contain referee chance results. Decision notes are separate, private while the table is live and optional on export.

```sh
out=$(mktemp -d)
python -m experiments.native_probe "$out/frozen.jsonl"
python -m experiments.native_opening "$out/openings.jsonl"
python -m experiments.native_transfer "$out/transfer-cued.jsonl" --arms cued
python -m experiments.native_probe "$out/frozen-cued.jsonl" --arms cued
python -m experiments.native_probe "$out/one-call.jsonl" --arms literal single
python -m experiments.native_probe "$out/preview-commit.jsonl" --arms draft informed --tactics-only
python -m experiments.native_probe "$out/rotation-fit.jsonl" --arms fit --tactics-only
python -m experiments.native_transfer "$out/transfer.jsonl"
python -m experiments.native_transfer "$out/transfer-fit.jsonl" --arms fit
python -m experiments.native_transfer "$out/isolated-square.jsonl" --arms hand --isolate-square
python -m experiments.native_games "$out/games" "$out/private" --seeds 9501
python -m experiments.native_games "$out/games" "$out/private" --seeds 9501 --arms hand --scope all
python -m experiments.native_games "$out/games" "$out/private" --corridor east
python -m experiments.native_games "$out/games" "$out/private" --corridor north
python -m experiments.native_games "$out/games" "$out/private" --corridor east --arms hand --give-opening
python -m experiments.native_games "$out/games" "$out/private" --corridor north --arms hand --give-opening
python -m experiments.corridor_goal "$out/games/corridor-goals.jsonl"
python -m experiments.corridor_goal "$out/games/corridor-verified.jsonl" --verified
python -m experiments.native_summary "$out"
python -m footsteps view "$out/games/9501-hand-all.json" --omniscient \
  --notes "$out/private/9501-hand-all.jsonl" -o "$out/9501-hand-all.html"
```

All runs used Ollama `qwen3.5:9b-q8_0` (local identifier `a8ee95bc3592`), temperature zero, inference seed 1, 4,096-token context and thinking disabled. The arms differ in schemas, prompts, response-token allowances and availability of feedback. Some sessions shared the local GPU. Wall times and fallback rates describe these runs under load. Full games include private explanations. Frozen probes omit them. Repeating a menu order or swapping a role on the same board does not create an independent game.
