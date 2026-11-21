# Persistent seats on a directed floor and at a social table

For a three-seat discussion playtest on this workstation, start with 9B/4k, 30 seconds of discussion and 45-second decisions. The most useful exchange to read is turn two, event 12 of the [longer discussion game](three-9b-30s/game.json). The [clock comparison](#calibrating-a-shared-discussion-clock) shows how often each model could actually reply. The [frozen proposal comparison](#the-same-movement-decision-with-and-without-the-landing-in-the-update) separates reading a movement opportunity from building a route.

The initial persistent listener could carry a recent ballot through compaction. This panel starts a builder at setup and moves the listener's dispute to the following turn. A single local Qwen3.8 27B RANA instance handles the requests. The starting configuration uses an 8,192-token context, a 240-token output limit, temperature zero, inference seed one and thinking disabled. Later comparisons change model size, context size and the compaction allowance as indicated. Each game with one model-controlled seat uses a real 30-second decision clock. Social discussion gets 15 seconds. Request times include prompt evaluation. Sums of prompt tokens count the repeated context on each call. Missing backend counters stay unknown.

This panel ran on one RTX 4090 (24,564 MiB) with Ollama 0.40.15. The installed model IDs were `05ec8ea1b9a8` for the 27B RANA layout, `a8ee95bc3592` for Qwen3.5 9B Q8_0 and `d8b0f5e9760c` for Qwen3.5 4B. Changing the context can reload a model. Live clocks start after warmup.

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

On the full east corridor, 9B/4k eventually built and entered the correct bridge on turn two. The first placement had already timed out. Seven ordinary replies hit the 240-token limit without supplying one complete tool call. The seat repeatedly chose to compact voluntarily after those failures. It finished one step short when the store emptied. [9B/4k corridor](9b-4096-east/)

## The same movement decision, with and without the landing in the update

A scripted opening prepares an enterable bridge by inspecting, rotating, placing and returning. Clone that exact private conversation at the first proposal, hold the referee clock fixed in the prompt, and alternate which presentation goes first across the three directions. Both arms can read the state. Only the movement update differs. Each has 30 real seconds to submit a proposal. The committed destination and tool sequence are replayed from the saved record.

| Seat | Toward EXIT without landings | Toward EXIT with landings | Extra calls | Elapsed inference per proposal across the six |
|---|---:|---:|---|---:|
| [27B, 8k](proposals-27b-8k.jsonl) | 3/3 | 3/3 | One illegal first attempt on north without landings | 1.84–4.23 s |
| [9B, 8k](proposals-9b-8192.jsonl) | 3/3 | 3/3 | None | 0.71–1.09 s |
| [9B, 4k](proposals-9b-4096.jsonl) | 3/3 | 3/3 | None | 0.66–1.05 s |

This isolates a decision the models could solve once given a successful build prefix. It says little about choosing that build themselves. The shared inference cache and the ordering of arms affect latency.

## A dispute about the older of two votes

The persistent listener is Blue P3. This historical fixture retains START at (0, 0) and EXIT at (2, 0) for comparison with the earlier listener trials. The ordinary solitaire and three-seat games use EXIT at (0, 0). P0 proposes an eastward step toward EXIT on turn one. P1 proposes a return to START on turn two. Scripted P0 casts opposite ballots on these steps. Red P2 then nominates P0 and says that P0 voted No on the *first* move. The original listener can page public ballots and inspect each entry’s turn. The revised lookup can select the turn explicitly. P3's first nomination on turn one provides an opportunity to compact before P2 names the disputed voter. A No on the first ballot does not establish a Red role. P0 is Blue in both games.

The first false-claim run stopped on an Ollama HTTP 500 during late compaction. The record is an explicitly unfinished prefix. During discussion P3 correctly described the *second* ballot in its reply to a claim about the *first*. We retained that prefix and modified the experiment host to log transient errors and let the referee clock continue. In the complete repeat its private summary had even retained that everyone approved the first step. It still defended P0 by citing P0’s more recent No on the backward proposal. After the removal vote it lost a nomination and its final movement vote to timeouts during repeated backend errors. The matching true-claim run also voted against removal. It passed its first nomination before the outer experiment loop could request compaction. We treat that run as a different memory condition. Moving the scheduling decision to the exact snapshot used for inference fixes the race. [Interrupted prefix](older-false-interrupted/game.json) · [Complete false claim](older-false/game.json) · [True claim without the scheduled early compaction](older-true/game.json)

The revised 27B listener compacted at the intended point in both games. In each, it made all six decisions on time and voted against removal. Neither first summary retained P0's ballot, neither listener queried the public record, and neither spoke about the accusation. The true-claim listener later endorsed the winning move out loud. Timely ballots and relevant speech can coexist with a complete absence of evidence checking. [False accusation](revised-false/game.json) · [True accusation](revised-true/game.json)

The 9B seat spoke six times and met all eight deadlines in each false-claim game. Its own removal nominations created two additional ballots relative to the 27B games. At 8k it publicly agreed with the false claim first, then fetched both revealed movement ballots, queried an empty range of removal ballots repeatedly, and ultimately voted Yes. Red repeated its accusation when P3 nominated P0 again. At 4k P3 made just one history query, before the accusation. It later asserted the false claim and voted Yes. In that game it twice described a removal nomination as selecting a builder. The native tool already says removal in its description. [9B at 8k](9b-8192-false/) · [9B at 4k](9b-4096-false/) · [Nomination terminology follow-up](https://github.com/othercriteria/footsteps/issues/106)

The 8k listener used four compactions and 50.9 cumulative inference seconds. The 4k listener used seven compactions and 54.0 seconds. The maximum reported prompts were 6,682 and 3,624 tokens respectively. The 4k compact requests really used the 409-token allowance. One run at each size establishes feasibility and identifies specific errors. Differences in the nominations and messages also change the later inputs.

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

## Seven-turn solitaire under a real decision clock

On ordinary deal 9811 both versions moved twice and finished at (−1, −2), three steps from EXIT. The old runner missed eight of 22 decisions and logged 27 failed backend requests. The revised 27B runner completed six private compactions and recorded zero backend failures. It still missed five of 22 decisions, all placements on turns 3–7. For example, on turn three it read the board, inspected different rotations seven times, then used another 13.3 seconds to compact. The 30-second placement period had elapsed. Providing a viable summary allowance addresses the backend failure and leaves a separate question about how much wall time to allow for investigation and action. [Original](landing-ordinary/) · [Revised](revised-ordinary/)

With a 60-second decision period on the same deal and revised client, the first two turns matched exactly. Only one of 22 decisions expired, a placement on turn four. At 30 seconds there were five expirations. Inference time rose from 248.5 to 287.8 seconds. The marker again finished at (−1, −2). The extra allowance helped the builder commit a choice and did little for its route planning on this deal. [60-second game](ordinary-60/)

## All three seats share one local inference queue

Blue P0, Red P1 and Blue P2 each hold their own seat credentials and persistent conversation. The referee gives 45 seconds per decision and 15 seconds for discussion. The three sessions use one FIFO inference worker. Queue time counts against the allowance. START is two steps west of EXIT and the store supports three turns. The same private opening hands and draw seed are used for the smaller-model repeat.

In the 27B game Blue P0 built the direct bridge. All three players approved stepping onto it. Red P1 then built to the side and stayed even though a step to EXIT was available. On the last turn Blue P2 inspected six times across held pieces and squares, built off the route, proposed EXIT and won the ballot 2–1 against Red. Each role cast the winning-move ballot in its team's interest. No one spoke or nominated. All 20 owed decisions arrived on time and all 75 requests returned accepted calls. The sum of per-seat queue times was 305.5 seconds out of 542.5 total request-seconds. These sums overlap in wall time. The original private traces span about 241 wall seconds from file creation (Unix second 1795231423) to the final write (1795231664). Later runs store an explicit monotonic measurement in `timing.json`. [Replay record and per-seat receipts](three/)

## Calibrating a shared discussion clock

In the 9B and 4B table runs, each request that began from a discussion update records whether `speak` appeared in its offered tools. The harness polls that same authenticated seat at the front of the GPU queue and when inference returns. A positive `seconds_after_reply` means a reply was ready while this seat could still speak in that ballot. A seat choosing to wait, query, or speak counts once toward the number of seat-windows with a timely reply. A completed `speak` counts as a remark only if it appears in the referee record. Zero offered requests and a reply after closing are distinguishable. These probes do not add anything to the model prompt. The play clock excludes model loading.

In the first 9B/4k full table all nine seat-windows had at least one reply ready while the seat could still speak. Six public remarks landed. Red's opening objection to the bridge coincided with Blue P2 also voting No. On the next turn all three publicly supported the same step and approved it. This sequence does not establish that the speech changed a ballot. The game took 301 seconds and 195 requests, including 44 compactions. Three of 23 required decisions expired. The working memory, frequency of checking state and differing game paths all affect full-table throughput. [9B/4k, 15 seconds](three-9b-4096/)

At 30 seconds, 9B spoke in all 11 seat-windows. Two Blue players explicitly echoed earlier remarks. In the opening vote all three called the southward step progress even though it increased the distance to EXIT. On the second turn everyone opposed Red P1's further southward proposal, including P1 itself. Blue P0 later nominated P1 and P1 publicly supported its own removal. Red won after removal when the last turn ended away from EXIT. The game took 369 seconds, included an extra removal ballot, and missed two of 24 decisions. With a single diverging game per clock we can measure the invitations and replies delivered under each setting, but cannot attribute a change of winner or judgment quality to the clock. [9B/4k, 30 seconds](three-9b-30s/)

Turn two, event 12 is a useful example to review with roles hidden. P1 proposed going south to (−2, −2) and floated repositioning as a reason. P0 correctly identified the destination's north entrance and south exit, asked what the extra distance would buy, and announced a conditional No. P2 explicitly answered P0. All three voted No. A separate check was already decisive: after turn one the marker at (−2, −1) was three Manhattan steps from EXIT with two movement opportunities remaining. No tile or ballot could close that gap in base-1. The transcript supports judging conversational relevance, reading the tile and recognizing a forced game result separately. Generate a public viewer with `python -m footsteps view experiments/persistent-panel/three-9b-30s/game.json -o /tmp/footsteps-public.html`.

The removed Red seat in the 30-second game made 23 more inference requests, consuming about 25.5 seconds of service time after subtracting its queue waits. At that point it had no remaining opportunity to speak, vote or build. The runner now lets a removed seat observe the table until the result without invoking its model again. Commit `83e2546` reproduces the earlier spectator behavior for these clock controls.

The 4B/4k run used the original 15-second discussion clock. All 12 seat-windows had a reply ready before closing. Ten remarks landed. Red P1 both said that reaching EXIT was its objective and voted to approve the winning step. Two removal ballots added work. A faster model offered more speaking and tool opportunities, and still missed four decisions. [4B/4k, 15 seconds](three-4b-15s/)

| Three seats, 4k context and 45-second decisions | Timely speaking opportunities | Remarks | Timely decisions | Requests / minute of play | 95th percentile request time including queue | Game wall time |
|---|---:|---:|---:|---:|---:|---:|
| 9B, 15 s discussion | 9/9 | 6 | 20/23 | 38.9 | 8.21 s | 301 s |
| 9B, 30 s discussion | 11/11 | 11 | 22/24 | 42.8 | 8.14 s | 369 s |
| 4B, 15 s discussion | 12/12 | 10 | 22/26 | 50.5 | 3.30 s | 340 s |

For discussion studies on this workstation, use three 9B seats with a 30-second window as the starting condition. It leaves room to hear someone else's remark, inspect the state and answer. The 15-second window is a cheaper baseline for seeing whether seats speak at all. Use 4B when testing the plumbing or collecting more tool calls per minute. Its role confusion makes it a weak stand-in for a more capable social player. The table runs are one game per condition with different nominations, so a future paired prompt or repeated deal panel should evaluate persuasion and skill separately. The shipped table clock remains configurable.

## How much game time goes into summaries?

Sum each request's elapsed time less its queue wait. Compaction calls used 75.4 of 301.0 service-seconds in the 9B/4k table with 15-second discussion and 111.6 of 368.7 with 30-second discussion. That is 25% and 30% respectively. The corresponding 4B/4k share was 64.9 of 200.4 seconds (32%). A request's elapsed inference time ends when inference returns, before the client waits for another event. Service time does not include deliberate idle time. Starting a fresh message history after compaction keeps the seat credentials and the loaded model. Subsequent prompt evaluation is charged to the subsequent call, so these numbers measure the cost of producing the summaries themselves.

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
run ordinary-60 ordinary --decision-seconds 60 --inspect-rotations --movement-context --implicit-wait
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
python -m experiments.persistent_table "$out/three-9b-30s" "$out/three-9b-30s-private" --model qwen3.5:9b-q8_0 --context 4096 --discussion-seconds 30
python -m experiments.persistent_table "$out/three-9b-8k-30s" "$out/three-9b-8k-30s-private" --model qwen3.5:9b-q8_0 --context 8192 --discussion-seconds 30
python -m experiments.persistent_table "$out/three-4b-15s" "$out/three-4b-15s-private" --model qwen3.5:4b --context 4096
```

To repeat the output-cap diagnostic on a locally retained compact-only request, run `python -m experiments.compaction_budget PRIVATE-REQUEST.json "$out/caps.jsonl"`.
