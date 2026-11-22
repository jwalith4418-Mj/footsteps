# Footsteps project stocktake

Reviewed against `main` at `7dde8f1` on November 22, 2026. The next model experiment I would run is a single removal ballot. The most useful independent game-design study can start from saved replays, and the next client migration test can run with scripted transport. None requires waiting for a new full-table game.

## What deal 14101 tells us

On the reviewed replay, Red P1 stayed when its only step was EXIT. No review fired in that game. Earlier in the same game, P1 voted to remove P0, its known Red teammate, after publicly describing P0 as Blue. The vote alone is compatible with a deliberate sacrifice. Checking the authenticated private roster alongside what P1 tells the table would distinguish explanations that a win rate cannot. [Reviewed game and comparison arms](../experiments/seat-payoff/README.md) · [Roster test #148](https://github.com/othercriteria/footsteps/issues/148)

In frozen EXIT ballots, all four first choices that triggered review changed on the next call. On a nonterminal trap, Blue still approved the step that confined the marker and Red rejected it. Earlier forecast probes even reported that EXIT was unreachable while predicting an immediate Red win. Under base-1 play continues. These are repeated decisions on a few positions. We have evidence for assisted correction on immediate outcomes and a counterexample to generalizing that result to route strategy. [Payoff study](../experiments/seat-payoff/README.md) · [Trap and terminal forecasts](../experiments/exit-interest/README.md)

## Where to spend the next round

| Order or opportunity | Smallest informative result | Decision it informs |
|---|---|---|
| 1. Private ally knowledge | Freeze T1/8–9 from the reviewed game. Compare Red considering a known ally and a known opponent, with a Blue seat lacking either fact. Keep private identification, public statement and actual vote separate. | If Red gets the private fact right, investigate its public or ballot decision before changing the role reminder. [#148](https://github.com/othercriteria/footsteps/issues/148) |
| 2. Directed-trap vote | Compare each team's first vote on a trap and on a similar-looking tile with an onward edge. Separately ask where the marker lands, whether play continues, and which steps remain. Hold out a floor. | Distinguish reading the tile from acting on the consequence. Try a fresh table once the distinction survives the controls. [#151](https://github.com/othercriteria/footsteps/issues/151) |
| In parallel, game design | Locate the first public proof that EXIT is unreachable on a few archived deals. Count decisions still played. Validate the bound against a last-turn Blue win. | Mark a frame for a human facilitator to ask whether the remaining choices were interesting. A certificate measures inevitability. Enjoyment needs a player. [#152](https://github.com/othercriteria/footsteps/issues/152) |
| In parallel, client reliability | Lose the reply to an accepted sealed ballot and follow the ordinary persistent seat through refresh. Deliver an opt-in owner replay from that same CLI with accepted, rejected and pending attempts distinguished. | Unblock retirement of the per-decision client after checking remaining live callers and preserving archived reproduction paths. [Recovery #28](https://github.com/othercriteria/footsteps/issues/28) · [Private evidence #109](https://github.com/othercriteria/footsteps/issues/109) · [Migration #104](https://github.com/othercriteria/footsteps/issues/104) |
| When a reader or playgroup is available | Give a blind reader a public prefix and lock their suspicion and cited evidence before advancing. At a live table, observe the first nomination and ask anyone eliminated what choice they got to make. | Learn what a spectator can infer, and separately what makes participation enjoyable. Start with the existing kit and base rules. [Reader pilot #153](https://github.com/othercriteria/footsteps/issues/153) · [Local session #3](https://github.com/othercriteria/footsteps/issues/3) · [Paper session #8](https://github.com/othercriteria/footsteps/issues/8) |

## Other open directions

| Area | What would justify the next work |
|---|---|
| Public evidence and speech | #64 separates private factual belief from what a speaker volunteers. Both Reds disclosed their own roles in all three wordings at the same opening. A different opening and a private check give the next comparison leverage. #91 asks whether a voter recovers the correct fact after compaction. #55 asks what the voter does with it. #106 retains nomination consequences and builder order as its test. Public attribution and ballot timing were already clarified and probed. [Speech](../experiments/seat-payoff/README.md) · [Nomination readbacks](../experiments/nomination-publicity/README.md) |
| Compute and table size | #117 has a four-seat fixture for queue delay. Score missed decisions, service delay and receipt of the last remark before testing #114's per-seat time reserve or #121's floor-cession bonus. #143 varies roster and hand size separately with fixed post-deal store. A small one-Red game cannot exercise mistaken identification of a Red teammate or an early Red-majority ending. [Queue measurements](../experiments/ballot-polling/README.md) |
| Transfer and mechanical balance | #93 needs a frozen candidate on unseen positions and separate counts for first choices and reviewed choices. #76 then tests matched seat substitutions using the existing rating schedule. #1 compares rotating cooperative hands across table sizes at fixed store. #4 compares recovery from held-out detour and discard prefixes. Both can use scripted policies. |
| Human play and variants | #142 needs groups told of the majority rule *before* they play. An archived branch already shows how the base result can differ. Use the first paper observations to decide whether to spend effort on spacing (#13), board boundaries (#14) or rotation (#54). Compare virtual tabletops (#7) when there is a concrete playtest workflow to reproduce. [Worked majority fork](../experiments/nomination-publicity/README.md) · [Facilitator protocol](design-review.md) |
| Access and maintenance | #18 remains the human-facing request to open an example or saved transcript without a CLI export. The viewer already supports private evidence and scrubbing. The stale connection alert (#30) has a proposed fix in #112. The maintainer is holding that fork PR pending an external-contribution policy decision in #154. #5 remains a small shell convenience. |
| Longer horizon | #40 and #41 need a stable unassisted evaluation and suitable training data before investing in SFT or RL. #123 is a place for formalization once there is a specific property worth proving. A shared regression scorecard becomes worthwhile when a second candidate needs the same cross-study controls. A first tile effect could wait for a paper table to identify a base-game choice it wants to change. |

Use the [open tracker](https://github.com/othercriteria/footsteps/issues) for current ownership. The mutable replay bug was fixed in [#110](https://github.com/othercriteria/footsteps/pull/110). Terminal payoff, nomination publicity and thinking-trace placement each have landed results. An experiment cited here as a baseline can still supply a fixture for a different question. [EXIT study](../experiments/exit-interest/README.md) · [Publicity study](../experiments/nomination-publicity/README.md) · [Trace placement #149](https://github.com/othercriteria/footsteps/pull/149)

## Coverage review

On `7dde8f1`, the locked Python 3.13 environment passed all **185 tests**, including the two offline Chromium viewer interactions. Coverage includes statements and branch destinations. The previous split baseline was 138 tests at 93.7% shipped, 85.0% study infrastructure and 93.0% combined. The denominators have changed as code landed. [Scope and reproduction commands](../CONTRIBUTING.md#check-test-coverage)

| Measured scope | Coverage |
|---|---:|
| Shipped Python package | 94.0% |
| Shared persistent study runtime and table accounting | 81.3% |
| Combined configured scope | 92.9% |

Keep both current scopes. The referee measures 99.6% and the persistent seat 95.5%, but a lost sealed response is still an unverified user-visible path. The decision-note module measures 74.6%. Use the CLI migration to test mismatched tables, malformed sidecars and attempted versus committed actions through replay export. Keep the operational evidence conversion under coverage as it moves into the supported client. Frozen prompts, seed panels and reporting scripts can retain their focused checks outside the aggregate. Browser JavaScript has separate interaction tests.
