# Voting as soon as discussion is exhausted

**Question.** What happens to game duration, missed decisions and listeners' access to the last remark if voting opens once every living player has spoken?

Compare two complete games on seed 11301. Both start with the same hands, turn order (Blue, Red, Blue), first draw, and EXIT two steps east of START. Three independent Qwen3.5 9B Q8_0 persistent sessions share one FIFO inference queue at 32k context. Choices have a 45-second wall deadline. Discussion before each ballot can last 30 seconds. The early-clock game ran first. The fixed-clock game keeps all 30 seconds on every ballot. Both use the shipped player, the same private tools and the same model seed. All player choices and remarks are live.

After the last accepted remark the early clock starts a full 45-second voting window. A silent player retains the remaining discussion time. The host appends each remark to every seat's history under the same lock that handles choices. For each actual model request offering a vote the measurement inspects the last public history entry in the submitted prompt. It records only the speaker number when the entry is a remark on that same revision. The audit compares it to the final speaker in the referee record. Receipt of a remark establishes that the voter could read it. Understanding the argument is a separate question.

## Results

| Clock | Wall time | Timely decisions | Timely decisions/minute | Remarks / eligible seat-windows | Timely votes with last remark in prompt |
|---|---:|---:|---:|---:|---:|
| Early | 279.06 s | 11/15 | 2.37 | 5/6 | 6/6 |
| Fixed | 255.71 s | 12/15 | 2.82 | 6/6 | 6/6 |

Both games moved twice and Blue won on turn two. Early closure cut roughly 16 seconds from the first discussion, but the early game finished 23 seconds later overall. P1 missed the same nomination, build and return in both games. P0 also missed a nomination in the early game. Comparing one pair cannot establish which policy improves average throughput. Keep the option experimental.

### Was the old discussion window providing a buffer?

In the fixed game the final speaker finished inference with 16.61 seconds remaining in the first discussion and 19.57 in the second. Seats could use that time to inspect the floor or prepare. In the first discussion the last tools each seat requested were waits. The receipts show no additional history or board reads starting after the final speaker's reply. Preparation during generation or a benefit on more contested ballots remains possible.

P1's early-game trace distinguishes two waits across events 5–6. Its off-turn wait after voting woke with the nomination open and an action owed. P1 issued a fresh wait on that nomination with 43 seconds left. That call returned only after the referee recorded a timeout. P1 later waited with 36 seconds left on its build and 43 on its return, and P0 with 44 left on its nomination. All six movement votes were timely under each clock. [On-turn wait follow-up](https://github.com/othercriteria/footsteps/issues/124)

## What the early game shows

On the T1 move ballot, the third speaker (P2) finished inference with 16.23 seconds left on the original 30-second discussion clock. All three accepted vote requests included P2's remark. On the T2 move ballot only two seats spoke, so the table held that window open to its original cutoff. Its last remark also appeared in all three accepted vote requests. Both moves passed. Four other decisions expired (two nominations, a placement and a return). In every case the seat invoked `wait` while it owed the choice. Early voting can remove the tail of a fully used discussion. These four waits expose a separate source of lost time.

The worked-clock tests also play the same speech schedule through the fixed and early modes, check a final submission just before or exactly at the cutoff, and exercise a ballot after a removal. In particular, the removed seat still sees the last remark while its absence cannot hold open discussion or grant it a vote.

## Reproduce

From the repository root, choose unused directories. Keep the model warm and run the games sequentially on the same device. Only the seat metrics and postgame records belong in the public result. The directory whose name ends in `-private` holds owner-only inference traces.

```sh
python -m experiments.early_ballot /tmp/116-early /tmp/116-early-private --early-ballot
python -m experiments.early_ballot /tmp/116-fixed /tmp/116-fixed-private
python -m experiments.early_ballot experiments/early-ballot/early
python -m experiments.early_ballot experiments/early-ballot/fixed
```

For a local table with human players, run `python -m footsteps table --early-ballot --save /tmp/early-table.json`. Omitting the flag selects the fixed clock. Both modes produce ordinary base-1 records. A [separate design experiment](https://github.com/othercriteria/footsteps/issues/121) considers explicitly yielding the floor in a discussion that permits multiple remarks.
