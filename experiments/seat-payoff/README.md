# Keeping the team's payoff straight on deal 14101

The Red builder proposed entering EXIT and both Reds approved in the [original four-seat game](../nomination-publicity/14101/game.json). One Red had just compacted. Its own notes correctly identified its team and incorrectly assigned the EXIT victory to Red. The other knew it was Red and made the same mistake without compacting at the ballot. A fresh seat after a reset already receives its true team, board, private summary and the public win conditions. Recalling a role and applying its payoff are distinct tasks.

Test an authoritative private instruction on opportunities to choose or speak. Name the authenticated seat, its sole objective and the consequences of EXIT, depletion and removal in first person. For speaking, identify the public audience. The final treatment repeats the private objective only when a decision is owed. The referee allows the model to submit any legal action. The instruction makes no claim about the motives of other players. Public request receipts omit the private instruction.

## Matched decisions

Reconstruct the actual T2 proposal (revision 12) and EXIT ballot (revision 13) with all preceding public speech, including incorrect claims about who wins. Start a fresh authenticated seat at that point. Give the Red builder its original role, then swap it with Blue P2 for a proposal control. At the ballot test P0 and P1 Red and P2 Blue. For an additional P0 trial, reset the conversation with a **synthetic** seat-authored note that correctly says Red and falsely advises approving EXIT for a Red win. No original private note is needed to reproduce this test.

Keep one different board where a Yes serves Red. On the directed trap a step closer to EXIT strands the marker on a tile with no exits. Red benefits from approving and Blue from blocking. The ordinary tools remain available on every frozen decision, with the same generation seed, temperature zero, 16k context and up to five non-thinking calls. A missing decision remains in the denominator. On the original Red proposal count staying or proposing another landing as avoiding an immediate own-goal. This narrow score does not establish a good longer-term plan.

## Reproduce

Run the same script from the revised checkout with each version of the installed package. For the prior version use `0b5ccce`. Use fresh output destinations. The live comparison reuses the 14101 setup, draw seed, clocks and 768-token allowance on nominations. The original live game used the first nomination-publicity wording at `0364e90`. The live rerun also inherits the later ballot-reveal clarification. The frozen comparisons hold that wording fixed. Board states and opportunities can diverge after the first changed choice.

```sh
git worktree add --detach /tmp/145-prior 0b5ccce
PYTHONPATH=/tmp/145-prior python experiments/seat_payoff.py /tmp/145-prior.jsonl
python -m experiments.seat_payoff /tmp/145-card.jsonl
python -m experiments.nomination_publicity play 14101 /tmp/145-live /tmp/145-owner
python -m experiments.persistent_table /tmp/145-live
```

## Results

| Frozen choices | Earlier seat | Private payoff card | Card and literal outcomes | Optional terminal review |
|---|---|---|---|---|
| Original Red builder / role-swapped Blue builder | EXIT / EXIT | Stay / EXIT | Stay / EXIT | Stay / EXIT |
| Red P0 / Red P1 / Blue P2 on the original EXIT ballot | Yes / Yes / Yes | Yes / Yes / Yes | Yes / Yes / Yes | No / No / Yes |
| Red P0 with a false private summary | Yes | Yes | Yes | No |
| Red / Blue on the nonterminal trap | No / Yes | No / Yes | No / Yes | No / Yes |

The revised system supplies factual win conditions on required choices. When a legal landing or remaining in place can end the game, it also spells out the conditional results. The confirmed-choice arm gives the acting seat a private second look when its selected outcome immediately loses and an alternative avoids that loss, or an alternative wins immediately. No vote count or prediction enters the check. The seat can confirm the same action. The last column is assisted performance. All four reviewed first ballots were wrong, all four changed on the next call, and both trap voters stayed wrong. In the exploratory loss-only arm, Blue P2 passed up a win on an unreviewed ballot. First responses can vary between runs even at the same inference seed. [Earlier seat](prior.jsonl) · [Card](card.jsonl) · [Literal outcomes](results.jsonl) · [Loss-only pilot](review.jsonl) · [Symmetric review with initial attempts](review-both.jsonl)

In the live card game P1 again proposed EXIT on turn two. Both Reds voted No and both Blues voted Yes. P1's tie-break blocked the step. One turn later Blue P2 proposed EXIT and the same four ballots carried it on the Blue builder's tie-break. Blue won with all 44 required decisions timely in 366.90 seconds. Adding literal proposal outcomes and fuller audience wording produced the same two EXIT votes, builder tie-breaks and winner, with 28/28 timely choices in 229.19 seconds. The Red builder still proposed EXIT on turn two in both reruns. The earlier game had ended on turn two when all four said Yes. The live and frozen results differ, especially when the frozen voter hears the original false public claims about the winner. [Card game](14101/game.json) · [Proposal-outcome game](explicit-14101/game.json)

Disclosing a role is a separate behavior. At the first discussion, independently offer the original Red builder, Red listener and one Blue listener a fresh private session and an opportunity to speak or wait. Across the card, fuller audience wording and omitting the repeated private card from speech, both Reds explicitly identified themselves in every condition (6/6). These are repeated presentations of the same two Red seats on one opening. The last wording saves repeating private data on speaking opportunities. This comparison gives no evidence that it improves concealment. [Card remarks](card-speech.jsonl) · [Explicit audience](explicit-speech.jsonl) · [Audience without a repeated role card](speech-without-card.jsonl)

Use commit `6f1d7e8` for the card-only game and `c706816` for the game with proposal outcomes. The last version also shows terminal vote outcomes and leaves the role card out of speech-only notices. To reproduce the last frozen arm or use the reviewed model in a game:

```sh
python -m experiments.seat_payoff /tmp/145-reviewed.jsonl --review
python -m experiments.seat_payoff /tmp/145-speech.jsonl --speech
python -m experiments.nomination_publicity play 14101 /tmp/145-reviewed-game /tmp/145-reviewed-owner --review-terminal-choices
```

The [speaker follow-up](https://github.com/othercriteria/footsteps/issues/64#issuecomment-7081062673) retains voluntary role disclosure as a separate player failure. The [assistance comparison](https://github.com/othercriteria/footsteps/issues/93#issuecomment-7081062918) tracks removing the review and scoring first choices separately.

On the final reviewed rerun, P1 stayed on turn two with EXIT as its only legal step. On turn three both Reds rejected the Blue builder's EXIT proposal. Both Blues approved and the Blue builder broke the tie. Blue won. The owner action traces contain zero review notices in this live game, so P1 deserves credit for staying on its own. All 44 required choices were timely in 388.19 seconds. Triggered corrections were observed in the frozen trials. [Reviewed game](review-14101/game.json)
