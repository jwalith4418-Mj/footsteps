# Who sees a nomination?

Everyone sees who nominated whom or who passed as soon as the choice commits. Individual ballots appear together by seat at the reveal. Before #141 the history implemented both facts, the rulebook called the vote public and the tool said it nominated a player for removal. The rulebook and model interface now explicitly describe the audience, attribution and timing of the nomination itself.

## Design

Use two fresh deals, seed 14101 (two Blue, two Red) and 14102 (three Blue, two Red), with the ordinary printed kit, two tiles per hand, three in the bag and EXIT two squares east. Role shuffling uses its own seed. Both tables use base-1, named nominations, one remark per seat before each ballot and early opening when all have spoken. The majority rule is an offline comparison. Each living model gets its own persistent conversation with Qwen3.5 9B Q8 at 16k context, a shared inference queue, a 60-second decision clock and 30 seconds for discussion. Only a seat being offered the nomination decision gets native thinking, up to 768 generated tokens across calls on that revision. If it exhausts that allowance, the ordinary fast policy can still act before the deadline.

Separately ask the first nominator in the four-seat deal what an uninvolved P2 would see after P1 names P0, passes, or P0 casts the first removal ballot. Swap P1's role with the first available opposite-team seat and repeat. Reconstruct a fresh conversation at the same referee revision with the seat's normal private state and available function descriptions. Omit prior table speech in both conditions. Request a private, structured explanation with thinking off and no action execution. Score whether the answer attributes both the nomination and pass to P1, distinguishes a nomination from removal, keeps P0's pending ballot private and identifies it at reveal. The two roles share a board and the questions call attention to observability. This tests what the model can report when asked. Organic use of that knowledge is a separate question.

## What the nominator could report

On the earlier wording, Red attributed the nomination and pass correctly. Blue named only the target and said passing produced no event. With explicit publicity, both said P2 sees P1 nominate P0 or pass. Blue then asserted that P2 sees *whether* P0 voted before reveal and learns *which seat* P0 voted for afterward. The referee actually withholds submission status and reveals a Yes, No or timeout on the one nominee. After making that precise, both seats described attribution, the sealed vote and the revealed value correctly. None explicitly said what happens to P0 pending the vote, so this readback does not settle #106. [Earlier wording](prior.jsonl) · [Explicit nomination wording](explicit.jsonl) · [Explicit ballot timing and values](reveal.jsonl)

## Live observations

In the four-seat game, P1 told the table on the first movement ballot that both P1 and the builder P0 were Red. Both were. Everyone approved the step. All four then passed on nomination. Blue P3's private trace noticed the claim and judged the evidence insufficient to nominate. It was a claim anyone could make under the rules. On turn two P1 proposed entering EXIT and all four approved. All 18 required decisions were timely, with 160.15 seconds of play. These seats heard the disclosure, but this game provides little evidence that they could exploit the public authorship of a nomination. [Four-seat referee record](14101/game.json) · [Nomination calls](14101/nomination-thinking.jsonl)

In the five-seat game, P3 cast the only Yes on P1's second proposal to move farther from EXIT. Red P2 then nominated Blue P3 and called attention to that observable vote. Blue P0 and P4 joined P2 to remove P3 by 3–2. Next, Blue P0 nominated Red P1. Both Reds voted to keep P1 and both surviving Blues voted to remove P1. The 2–2 tie failed. P1 then nominated P0 and publicly acknowledged doing so. All four voted No. The origin of the accusation was public, but the sequence alone cannot establish that the last nomination was retaliation. Red won at depletion on turn three. There were three nominations, six passes and 43/44 timely required decisions. The sole timeout was a return, and total play took 490.14 seconds. Neither fresh game reached a living Red majority. The two times combine roster size, different decisions and different histories. [Five-seat record](14102/game.json) · [Nomination calls](14102/nomination-thinking.jsonl)

## Strict-majority comparison

Audit each distinct completed multi-Red history under `experiments`, counting a setup and event sequence once even if it has multiple paths or speech tracks. Record the first revision with strictly more living Red than Blue, including revision zero. On the pre-study main (`32f57e6`), only one of 21 such histories reached the threshold. Red took a 2–1 lead at event 18 and removed the last Blue at event 20. These archived fixtures and selected model games are a convenience sample. [8602 record](../four-seat/fixed/8602-red1+3.json)

For a counterexample with an open EXIT, start from the worked crossing. Give P0 and P3 Red, P1 and P2 Blue. P1 nominates P2 after the first move. P2 is removed at event 7, leaving a 2–1 Red majority. P3 and P0 pass, P1 builds and proposes EXIT. P1 votes Yes and P3 votes No. If P0 votes No, Red wins at depletion. If P0 votes Yes, Blue wins at EXIT. Both branches replay through the referee. The proposed majority ending would award Red both games at event 7. [Design implications](../../docs/decisions.md#should-a-living-red-majority-end-the-game)

At the pending EXIT vote we also started each surviving 9B seat independently on its own projection, with the ordinary fast movement policy, no remarks and up to five calls. P0 and P3 (Red) both rejected EXIT, P1 (Blue) approved it, and each voted on its first call. Applying these three votes gives the same Red result as the automatic ending on this particular continuation. [Frozen ballot receipts](majority-ballot.jsonl)

## Reproduce

The two live games and the majority ballot used commit `0364e90`, before the final reveal-wording revision. Use a fresh output directory for each run. The model host runs the deals serially. The archive command prints one row per qualifying history.

```sh
mkdir -p /tmp/141-public /tmp/141-owner
python -m experiments.nomination_publicity play 14101 /tmp/141-public/14101 /tmp/141-owner/14101
python -m experiments.nomination_publicity play 14102 /tmp/141-public/14102 /tmp/141-owner/14102
python -m experiments.nomination_publicity majority /tmp/141-public/{14101,14102}/game.json
python -m experiments.nomination_publicity witness
python -m experiments.nomination_publicity majority-ballot /tmp/141-public/majority-ballot.jsonl
python -m experiments.nomination_publicity archive experiments
python -m experiments.persistent_table /tmp/141-public/14101
```

For the wording comparison, run the same study file against two package checkouts. Use the saved four-seat record in both. The `prior` checkout supplies both the former live system prompt and former tool descriptions.

```sh
git worktree add --detach /tmp/141-prior 32f57e6
git worktree add --detach /tmp/141-explicit 0364e90
study="$PWD/experiments/nomination_publicity.py"
record="$PWD/experiments/nomination-publicity/14101/game.json"
PYTHONPATH=/tmp/141-prior python "$study" readback "$record" /tmp/141-public/prior.jsonl
PYTHONPATH=/tmp/141-explicit python "$study" readback "$record" /tmp/141-public/explicit.jsonl
python -m experiments.nomination_publicity readback "$record" /tmp/141-public/reveal.jsonl
```

Use the omniscient viewer to see each private thinking call at the pending nomination, including calls that ended without an action. The public receipts store the length and digest of each trace. For example, to view the four-seat game in Bash:

```sh
notes=()
for file in /tmp/141-owner/14101/thinking-*.jsonl; do notes+=(--notes "$file"); done
python -m footsteps view /tmp/141-public/14101/game.json --omniscient "${notes[@]}" -o /tmp/141-owner/14101.html
```
