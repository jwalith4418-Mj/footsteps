# Persistent seats on a directed floor and at a social table

The initial persistent listener could carry a recent ballot through compaction. This panel starts a builder at setup and moves the listener's dispute to the following turn. A single local Qwen3.8 27B RANA instance handles the requests. The starting configuration uses an 8,192-token context, a 240-token output limit, temperature zero, inference seed one and thinking disabled. Later comparisons change model size, context size and the compaction allowance as indicated. Each game with one model-controlled seat uses a real 30-second decision clock. Social discussion gets 15 seconds. Request times include prompt evaluation. Sums of prompt tokens count the repeated context on each call. Missing backend counters stay unknown.

## Two chances to move

Start two squares from EXIT. The hand and both tiles in the store are face 65, with a north entrance and south exit in printed orientation. There is exactly one first placement and orientation that can still win. Then the player must propose the intermediate square, approve the movement, build somewhere else and propose and approve EXIT. The live solitaire seat casts its own movement votes. All placements, returns, proposals and votes come from the model unless the referee marks a fallback.

The first two runs used the original persistent tools. The next two offered `inspect_rotations_at(piece,x,y)`. It shows the four absolute orientations and whether the marker could step onto that square. The player still has to turn the held piece and place it. Both original opening builds used the correct square and the wrong orientation. With inspection, both calls on the opening square were voluntary, both selected the enterable orientation and both committed it. On each first proposal the player tried to jump from START straight to EXIT. After rejection it chose to stay. On the north table the second placement and proposal also expired. A required compaction took 28.7 seconds when only about 24 seconds remained on the proposal.

The third interface puts the actual marker, EXIT and legal one-step destinations into the proposal update. The movement ballot names its proposed landing. These are visible referee facts. The player may still stay or vote against its step. East and north are repeated positions. West is a transfer check. A longer ordinary game uses seed 9811 from the earlier solitaire study.

| Two-turn corridor | Opening gave a step toward EXIT | First proposal | Winner | Missed decisions |
|---|---|---|---|---:|
| [Original east](base-east/game.json) | No | Stay | Red | 0 |
| [Original north](base-north/game.json) | No | Stay | Red | 0 |
| [Inspection, east](inspect-east/game.json) | Yes | Stay | Red | 0 |
| [Inspection, north](inspect-north/game.json) | Yes | Stay | Red | 2 |
| [Inspection and movement update, east](landing-east/game.json) | No | Stay | Red | 0 |
| [Inspection and movement update, north](landing-north/game.json) | No | Stay | Red | 1 |
| [Inspection and movement update, west](landing-west/game.json) | Yes | Onto the new bridge | Blue | 0 |

The west seat placed the bridge with rotation 1, stepped onto it, made its second build behind START, then proposed and approved the step from the bridge to EXIT. On east it skipped inspection entirely. On north it inspected at the correct square and placed the unchanged piece. Different builds already change which steps are possible. Timing also varies. The original updates included fractional seconds. These full games provide examples of failures and recoveries, with little basis for estimating win rates.

## A dispute about the older of two votes

The persistent listener is Blue P3. P0 proposes an eastward step toward EXIT on turn one. P1 proposes a return to START on turn two. Scripted P0 casts opposite ballots on these steps. Red P2 then nominates P0 and says that P0 voted No on the *first* move. The original listener can page public ballots and inspect each entry’s turn. The revised lookup can select the turn explicitly. P3's first nomination on turn one provides an opportunity to compact before P2 names the disputed voter. A No on the first ballot does not establish a Red role. P0 is Blue in both games.

The first false-claim run stopped on an Ollama HTTP 500 during late compaction. The record is an explicitly unfinished prefix. During discussion P3 correctly described the *second* ballot in its reply to a claim about the *first*. We retained that prefix and modified the experiment host to log transient errors and let the referee clock continue. In the complete repeat its private summary had even retained that everyone approved the first step. It still defended P0 by citing P0’s more recent No on the backward proposal. After the removal vote it lost a nomination and its final movement vote to timeouts during repeated backend errors. The matching true-claim run also voted against removal. It passed its first nomination before the outer experiment loop could request compaction. We treat that run as a different memory condition. Moving the scheduling decision to the exact snapshot used for inference fixes the race. [Interrupted prefix](older-false-interrupted/game.json) · [Complete false claim](older-false/game.json) · [True claim without the scheduled early compaction](older-true/game.json)

The revised 27B listener compacted at the intended point in both games. In each, it made all six decisions on time and voted against removal. Neither first summary retained P0's ballot, neither listener queried the public record, and neither spoke about the accusation. The true-claim listener later endorsed the winning move out loud. Timely ballots and relevant speech can coexist with a complete absence of evidence checking. [False accusation](revised-false/game.json) · [True accusation](revised-true/game.json)

## Why a compaction request returned HTTP 500

We reconstructed the old ordinary seat at revision 15 from the referee prefix and its recorded private tool calls and results. The original fractional clock readings in each input update were unavailable, so the reconstructed notices used a fixed clock. We then froze this entire private request and changed only `num_predict`. With the original 240-token limit, both attempts failed. Ollama identified an unexpected end of JSON while parsing the arguments of the named `compact` call. At 80 tokens it returned the same error. The four larger limits all produced the same length reply and note. [Redacted measurements and shared request digest](compaction-caps.jsonl)

| Output cap | Result | Measured request time |
|---:|---|---:|
| 240, twice | HTTP 500, incomplete compact arguments | 10.39 s, 6.68 s |
| 80 | Same parser error | 2.45 s |
| 410 (5% of 8k) | Complete, 306 output tokens | 8.98 s |
| 480 | Complete, 306 output tokens | 8.67 s |
| 512 | Complete, 306 output tokens | 8.47 s |
| 819 (10% of 8k) | Complete, 306 output tokens | 8.37 s |

The successful prompts were 5,975 tokens and the saved note was 785 characters, comfortably within the earlier 1,600-character check. The sampled server log reported no input truncation. The output budget cut off the serialized tool call before the server could return it. The historic client retained only the 500 status, so individual historical errors cannot all be attributed with certainty. The dedicated compaction budget now scales with context; regular actions keep their smaller limit. Replaying an owner-held compact request at a range of caps writes counts, timing, status and a request hash while keeping the input and summary local.

## All three seats share one local inference queue

Blue P0, Red P1 and Blue P2 each hold their own seat credentials and persistent conversation. The referee gives 45 seconds per decision and 15 seconds for discussion. The three sessions use one FIFO inference worker. Queue time counts against the allowance. START is two steps west of EXIT and the store supports three turns. The same private opening hands and draw seed are used for the smaller-model repeat.

In the 27B game Blue P0 built the direct bridge. All three players approved stepping onto it. Red P1 then built to the side and stayed even though a step to EXIT was available. On the last turn Blue P2 inspected six times across held pieces and squares, built off the route, proposed EXIT and won the ballot 2–1 against Red. Each role cast the winning-move ballot in its team's interest. No one spoke or nominated. All 20 owed decisions arrived on time and all 75 requests returned accepted calls. The sum of per-seat queue times was 305.5 seconds out of 542.5 total request-seconds. These sums overlap in wall time. [Replay record and per-seat receipts](three/)

## Reproduce

For offline reports, run `python -m experiments.persistent_panel report experiments/persistent-panel/NAME` on any completed single-seat run. The report replays the referee events to count actual commitments, reveal results and misses. The interrupted prefix can be inspected with `python -m footsteps replay experiments/persistent-panel/older-false-interrupted/game.json`.

Use fresh output paths for inference. The original, inspection and landing comparisons used the pre-audit seat interface in commit `e2511c8`. Commit `80cd8f1` includes the host's backend-error handling and the scheduling fix. The archived older-true game records the original scheduling race. These are real-clock experiments. The saved records reproduce the game exactly, while another model run can differ in timing, words and actions.

```sh
out=$(mktemp -d)
run() {
  name=$1
  heading=$2
  shift 2
  python -m experiments.persistent_panel "$heading" "$out/$name" "$out/$name.private.jsonl" "$@"
}
for heading in east north; do
  run "base-$heading" "$heading"
  run "inspect-$heading" "$heading" --inspect-rotations
done
for heading in east north west ordinary; do
  run "landing-$heading" "$heading" --inspect-rotations --movement-context
done
for claim in false true; do run "older-$claim" "$claim"; done
```

With the revised interface, run the matched listener games, the three independent seats and the fixed proposal comparison as follows. The ordinary deal uses the same seed, draw stream and clock as its earlier run.

```sh
for claim in false true; do run "revised-$claim" "$claim" --implicit-wait; done
run revised-ordinary ordinary --inspect-rotations --movement-context --implicit-wait
python -m experiments.persistent_table "$out/three" "$out/three-private"
python -m experiments.persistent_proposals "$out/proposals.jsonl" --model footsteps-qwen3.8:27b-rana-layout
```

To compare the smaller model on the same scenarios, use the same seed and seat fixtures at each context size. The frozen proposals can also be audited without inference by omitting `--model`. The live three-seat report takes the game directory as its only argument.

```sh
for ctx in 8192 4096; do
  python -m experiments.persistent_proposals "$out/proposals-9b-$ctx.jsonl" --model qwen3.5:9b-q8_0 --context "$ctx"
  run "9b-$ctx-false" false --implicit-wait --model qwen3.5:9b-q8_0 --context "$ctx"
done
run 9b-4096-east east --inspect-rotations --movement-context --implicit-wait --model qwen3.5:9b-q8_0 --context 4096
python -m experiments.persistent_table "$out/three-9b-4096" "$out/three-9b-4096-private" --model qwen3.5:9b-q8_0 --context 4096
```

To repeat the output-cap diagnostic on a locally retained compact-only request, run `python -m experiments.compaction_budget PRIVATE-REQUEST.json "$out/caps.jsonl"`.
