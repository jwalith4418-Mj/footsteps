# Can a seat discover a move budget before the deal?

Ask the model for a private 100–200-word strategy note before it learns its team, hand, starting square or future board. The public EXIT is at (0, 0). The writer gets the draw, placement, return, proposal, ballot, removal and termination procedures. The human rulebook explicitly states the Manhattan bound and a solitaire corollary about net depletion, so the study uses procedural prose that gives neither deduction away. The exact inputs live in the [runner](../pregame_analysis.py).

The open prompt asks for a note useful to either team. The second prompt adds one sentence asking for invariants that distinguish winnable and unwinnable states. Both use inference seeds 1, 2 and 3 at temperature 0.7. The checkpoint blocks are Qwen3.5 9B Q8_0 and the ordinary Qwen3.8 27B RANA layout. Each uses an 8192-token context. The initial notes use thinking disabled, as in the playing seat. We preserve the writer's final wording. Five of the fifteen finished notes met the suggested length. The range was 175–368 whitespace-delimited words. Model-supplied private analysis channels are excluded from saved notes.

## What changed at the ballot

| Model | Seat prompt and preparation | Ballots | Team-serving votes | Yes votes | Correct future move count | All four facts correct |
|---|---|---:|---:|---:|---:|---:|
| 27B | Original | 8 | 4 | 0 | 0 | 0 |
| 27B | Original + open note | 24 | 11 | 1 | 18 | 6 |
| 27B | Original + invariant note | 24 | 11 | 1 | 12 | 6 |
| 27B | Clock | 8 | 4 | 0 | 8 | 4 |
| 27B | Clock + invariant note | 8 | 3 | 1 | 8 | 3 |
| 27B | Clock + distance lesson | 8 | 4 | 0 | 8 | 4 |
| 27B | Original + two-pass 16k note | 8 | 3 | 1 | 8 | 4 |
| 9B | Original | 8 | 3 | 3 | 3 | 0 |
| 9B | Original + open note | 24 | 10 | 8 | 4 | 1 |
| 9B | Original + invariant note | 24 | 7 | 7 | 4 | 1 |
| 9B | Clock | 8 | 5 | 3 | 3 | 0 |
| 9B | Clock + invariant note | 8 | 3 | 1 | 4 | 2 |
| 9B | Clock + distance lesson | 8 | 4 | 0 | 2 | 0 |

The short board and the detour each need opposite votes from Blue and Red. A seat that always rejects earns four of eight. An open or invariant note supplies eight votes per seed, so each 24-ballot row repeats the same positions three times. The rightmost column requires the landing distance, future opportunities and both branches' feasibility to be correct on the same trial.

The clock clarification helped 27B count future moves on every bare-seat trial. On both short boards it correctly reported the consequences of both outcomes from either team. Still, as Red it rejected the very step that would make EXIT unreachable. Adding the distance lesson produced eight explicit No votes on each checkpoint. On 9B the clock alone produced five team-serving votes including one board/orientation where it switched correctly with its role. The distance lesson lost that switch. We kept the clock clarification in the live prompt and kept the geometric lesson experimental.

These are silent tactical decisions on two floors. Each role swap and board rotation reuses much of the same evidence. The study measures how a model answers here, with a separate private factual check after committing. It cannot establish what the seat believed before voting, the effect on whole-game win rates, or how it would respond to another player's argument. The [role and ballot follow-up](https://github.com/othercriteria/footsteps/issues/101) tests translating a predicted outcome into a vote for one's own team.

## What the ordinary pregame notes found

Neither checkpoint wrote a sound store-to-distance bound in its six original notes. Open-ended notes favored movement toward EXIT, bottlenecks, information asymmetry and watching for obstruction. The invariant cue produced substantially more specific claims, including errors that could be acted on.

- The 9B writer compared remaining steps with distance in seed 3, then claimed an elimination vote could prolong play. It never derived how many steps the store buys. Seed 1 instead added the seat's hand to its budget for the path.
- The 27B writer put store size and Manhattan distance in the same inequality in seed 2, then claimed that too few tiles would guarantee the path if Blue controlled the build. Seed 3 proposed comparing the tiles needed for a connection with the remaining store. Counting additional placements is a useful construction test and can miss an impassable directed detour from the marker.
- Other notes identified real mechanisms, including how the builder breaks a movement tie and how mismatched directed edges can strand the marker. Several imagined coordinating with other Red players at a one-Red table, or planning how to vote on a second proposed destination during the same ballot.

## What would count as discovery?

At the beginning of a build with S tiles left, each completed build consumes exactly one net tile. Barring earlier termination, the group has S opportunities left, including that build's move. One step can cut Manhattan distance to EXIT by at most one. If the distance exceeds the opportunities left, Blue cannot reach EXIT. At a movement ballot the build is already over. Compare the distance **from each possible landing** with the current store count for the future moves after this ballot. A distance inside the budget still leaves tile connectivity and votes to resolve.

Grade the original note before attributing skill to its ballots. Distinguish a correct necessary bound, an explicit incorrect comparison, and advice such as “move closer” or “watch the store” that supplies no usable threshold. Look separately for net depletion and a geometric lower bound. A note may also discover something useful about directed reachability, removals, or ties.

## Transfer after compaction

Each note is written once. Clone it into fresh private P3 seats on the [short game and built detour](../move-budget/README.md), original and clockwise-rotated, as Blue and Red. In the short game the outward step leaves three squares to cover in two moves. In the detour, moving outward now opens the only viable five-step route. Referee witnesses and optimistic bounds validate both cases. The seat sees its actual role, own hand, public floor and history, with no public remark in any arm.

All seats first pass through the same successful compact tool with a scripted rolling summary. A prepared seat receives its own predeal note verbatim in a separate private field after the reset. The no-note seat gets the same rolling summary and normal projection. A later compact or recovery also restores the note alongside the latest rolling summary. Only the experiment's seat subclass adds this field. Notes never enter referee events, peer projections, public discussion or shared receipts. Each playing seat uses the same checkpoint as its writer, native tools, a five-call cap, frozen clock, temperature zero, seed one and thinking disabled. Only after the ballot does a private fork answer the four factual questions from the earlier study.

One note supplies eight correlated ballots. Each bare model control supplies eight. Report votes that preserve Blue's chance or foreclose it for Red, and independently score whether the private answer identifies the landing distance, number of future moves and both feasible branches. Eight correct choices would require acting appropriately for both teams on both boards in both orientations.

The initial 27B invariant panel produced a directionally reversed bound and one draft hit the 512-token allowance. We added a 1024-token retry for unfinished drafts and a separate exploratory panel of three invariant prompts on the same 27B checkpoint with thinking enabled during preparation. None of the three deliberative seeds finished a memo. Seed 1 exhausted both 3072 and 6144 tokens. Seeds 2 and 3 each exhausted 3072. This measures preparation reliability under those limits. There was no finished strategy to grade or transfer in that condition. Thinking stays disabled on the ballots. Each note still faces every ballot, including notes containing errors. Hashes identify the exact text restored to the session.

## Reproduce

Use the tagged local models and new paths. Run one model at a time. Owner files contain the finished memos verbatim. Shared note receipts contain word counts, model/seed and hashes. A transfer run verifies the private panel and its hashes before creating its output. The four-field assessment uses a separate post-vote request and never enters a later playing conversation.

```sh
python -m experiments.pregame_analysis generate 27b /tmp/131-27-private.jsonl /tmp/131-27-notes.jsonl
python -m experiments.pregame_analysis transfer 27b /tmp/131-27-private.jsonl /tmp/131-27-ballots.jsonl
python -m experiments.pregame_analysis generate 9b /tmp/131-9-private.jsonl /tmp/131-9-notes.jsonl
python -m experiments.pregame_analysis transfer 9b /tmp/131-9-private.jsonl /tmp/131-9-ballots.jsonl
python -m experiments.pregame_analysis generate 27b /tmp/131-deliberate-private.jsonl /tmp/131-deliberate-notes.jsonl --deliberate
python -m experiments.pregame_analysis transfer 27b /tmp/131-deliberate-private.jsonl /tmp/131-deliberate-ballots.jsonl --deliberate
python -m experiments.pregame_summary
```

The 27B bare seat voted No on all eight original positions. All six original 27B notes together produced two Yes votes in 48 ballots. Both were wrong for the seat. The open notes nevertheless improved reports of the remaining move count from 0/8 without a note to 18/24. Facts supplied privately after the vote and enacted choices measure different behavior.

The [note review](note-review.csv) is a single reader's qualitative coding. “Correct” requires a sound necessary store/distance bound (or equivalent), without a false exception. “Partial” identifies a relevant inequality with a missing or mistaken premise. “Incorrect” makes a material error in the proposed budget or conclusion. “None” includes sensible strategic advice that never gives a threshold. A separate column records explicit recognition of one net tile consumed per turn. The writing models received no test positions. The reader who coded the notes knew the study question.

## Clearing up the public rules

We used recurring mistakes in the first drafts to revise the normal persistent-seat prompt. It explains what consumes a movement opportunity, what happens after a rejected proposal, when an empty store ends play, and where an eliminated hand goes. It supplies no preferred direction, route or vote. The movement section in the human rules now explicitly names the same count. The original experimental conditions restore the [earlier system prompt](original-system.txt) so later changes cannot retroactively supply the missing clock explanation.

We repeated the silent control for each model on the revised live prompt, then repeated it with an invariant-seeking pregame note written by the same model under the revised rules (seed 1, thinking disabled). This last comparison has a single note per model. The clock is given during writing and play, so getting it right under these conditions measures comprehension rather than independent discovery.

```sh
python -m experiments.pregame_analysis generate 27b /tmp/131-27-clock-private.jsonl /tmp/131-27-clock-notes.jsonl --clarified
python -m experiments.pregame_analysis transfer 27b /tmp/131-27-clock-private.jsonl /tmp/131-27-clock-ballots.jsonl --clarified
python -m experiments.pregame_analysis generate 9b /tmp/131-9-clock-private.jsonl /tmp/131-9-clock-notes.jsonl --clarified
python -m experiments.pregame_analysis transfer 9b /tmp/131-9-clock-private.jsonl /tmp/131-9-clock-ballots.jsonl --clarified
```

The 27B clarified note identified a second useful necessary condition. If connecting START and EXIT needs more additional tile placements than remain, Blue cannot win. A connected floor can still be unwinnable for a marker on the wrong side of a one-way passage. The 9B clarified note correctly observed that staying spends a turn, then used the number of living Blue players to adjudicate exhaustion. Neither note derived the marker's distance bound.

## Teaching the distance bound

A final pair of silent controls gives exactly the same clock rules and explicitly teaches the lower bound from each possible landing. The prompt also explains that a viable directed route may start by moving away. It gives both teams the same information. This condition measures whether a seat can use a supplied rule when casting its ballot. No seed, note or new board is required.

```sh
python -m experiments.pregame_analysis teach 27b /tmp/131-27-taught-ballots.jsonl
python -m experiments.pregame_analysis teach 9b /tmp/131-9-taught-ballots.jsonl
```

## Giving the writer a larger context

We retried the first 27B invariant prompt with thinking enabled, the same procedural rules and the same seed. At 16,384 tokens the writer can generate up to 14,336 tokens, leaving 2,048 for the input. The increase changes both the space available and the output allowance. It tests whether the seat can finish and use the analysis at this cost. Transfer uses the original clock-unassisted ballot prompt, an 8,192-token context and thinking disabled. Only the finished memo crosses that boundary.

```sh
python -m experiments.pregame_analysis generate 27b /tmp/131-16k-private.jsonl /tmp/131-16k-notes.jsonl --preparation-context 16384
python -m experiments.pregame_analysis transfer 27b /tmp/131-16k-private.jsonl /tmp/131-16k-ballots.jsonl --preparation-context 16384
```

The 16k writer consumed 455 input tokens and all 14,336 allowed output tokens in 572.71 seconds. It still had no finished note for the seat. Ollama reported a resident context of 16,384 and a 10% CPU / 90% GPU split on the RTX 4090. Context and output limits are separate controls. A longer single request bought substantially more computation without producing a playable artifact.

We then tried a bounded two-pass writer on the same seed and 16k context. Give the thinking pass 3,072 output tokens. If it reaches that limit, return its transient draft to the same model and ask it to deliver its 100–200 word note, now with thinking disabled and up to 1,024 output tokens. The finisher sees the same procedural rules. It receives no board, role, correct answer or editorial feedback. The intermediate draft stays out of both files and the ballot context.

```sh
python -m experiments.pregame_analysis generate 27b /tmp/131-finish-private.jsonl /tmp/131-finish-notes.jsonl --finish-draft
python -m experiments.pregame_analysis transfer 27b /tmp/131-finish-private.jsonl /tmp/131-finish-ballots.jsonl --finish-draft
```

The two-pass writer delivered a 242-word note after 118.85 seconds of preparation and 13.56 seconds of writing. It identified the need for an EXIT-facing edge, distinguished source exit from destination entrance, and recognized the one-tile deadline. Its proposed invariant went wrong at the draw itself: it said drawing two and returning one leaves the store constant. The procedural rules were explicit about both operations. The writer consequently supplied no sound bound on marker movement. We retained the note exactly as written for the eight ballots.

After compaction the 8k seat with this memo reported the correct future budget on all eight ballots, despite the error in its own note. It cast three team-serving votes, one fewer than the original bare seat. The revised live clock prompt achieved the same eight correct counts without a preparation pass. With one extended seed, two boards and no ballot gain, we kept pregame preparation opt-in. The runner supports a 32k retry, but this study stopped at 16k.
