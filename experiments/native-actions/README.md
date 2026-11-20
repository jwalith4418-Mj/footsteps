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

The eight port puzzles request a specific entrance and exit on a straight or an elbow. Each was presented twice with reversed option and piece order. The seven archived tactical positions use the earlier Blue and Red prefixes and the turn-three escape on deal 8602. Blue scores for building a board with an immediately legal step and an optimistic onward path within the remaining turns. Red scores for permanently sealing the reachable component. Each is a sufficient tactical witness for this probe. Neither test measures the value of every legal strategy. Missing commitments score zero. [Position sources and scoring](../rotation_probe.py)

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

## Reproduce

The commands create new files and take time on a local Ollama server. Use a new output directory per run. To inspect the saved evidence without a model, run `python -m experiments.native_summary` at the repository root. Every JSONL decision records the actual commitment or failure and each private operation the native model attempted. Complete game records contain referee chance results. Decision notes are separate, private while the table is live and optional on export.

```sh
out=$(mktemp -d)
python -m experiments.native_probe "$out/frozen.jsonl"
python -m experiments.native_probe "$out/one-call.jsonl" --arms literal single
python -m experiments.native_probe "$out/preview-commit.jsonl" --arms draft informed --tactics-only
python -m experiments.native_probe "$out/rotation-fit.jsonl" --arms fit --tactics-only
python -m experiments.native_transfer "$out/transfer.jsonl"
python -m experiments.native_transfer "$out/transfer-fit.jsonl" --arms fit
python -m experiments.native_transfer "$out/isolated-square.jsonl" --arms hand --isolate-square
python -m experiments.native_games "$out/games" "$out/private" --seeds 9501
python -m experiments.native_games "$out/games" "$out/private" --seeds 9501 --arms hand --scope all
python -m experiments.native_summary "$out"
python -m footsteps view "$out/games/9501-hand-all.json" --omniscient \
  --notes "$out/private/9501-hand-all.jsonl" -o "$out/9501-hand-all.html"
```

All runs used Ollama `qwen3.5:9b-q8_0` (local identifier `a8ee95bc3592`), temperature zero, inference seed 1, 4,096-token context and thinking disabled. The arms differ in schemas, prompts, response-token allowances and availability of feedback. Some sessions shared the local GPU. Wall times and fallback rates describe these runs under load. Full games include private explanations. Frozen probes omit them. Repeating a menu order or swapping a role on the same board does not create an independent game.
