# What changes while a seat waits for a ballot?

On the [responsive-wait deal](../required-wait/README.md), P2 asked for movement ballots 23 times during the first discussion and 19 times during the second. The first lookup always returned an empty page. The second always returned entry 7, the first movement tally. Those 42 calls consumed 38.1 seconds of inference service with P2 still able to speak. Earlier traces show the converse error. In the idle-budget game a voter read movement history 50 times while its ballot was due. In the control game a seat tried to vote 28 times during discussion. [Earlier games](../game-efficiency/README.md)

A matching history page now explains when the current ballot becomes public and what the seat can do. It still returns the requested evidence immediately. A seat can speak, listen, cast its own sealed ballot or wait for collective reveal depending on the opportunity. Successful reads can expose the presence of this guidance in the study receipts. For rejected calls the shared receipts omit model-supplied arguments and unoffered function names.

## Frozen ballots and an off-turn transfer

At revisions 4 and 12 of the responsive-wait game, give P2 its projected board, role, hand, and the recorded remarks. Open a fresh conversation for each trial. Script one movement-history request, then give the 9B model five free calls. Test the discussion with P2 still able to speak, the opening with P2's ballot due, and the period after P2 has voted. Both other seats have already spoken in each position. The fixed clock advances to the next boundary on a blocking wait. Stop on a remark, ballot, phase transition out of discussion or revision change. The three positions per revision are separate conversations.

| History reply and tool | Free calls over six positions | Extra history reads | Spoke in discussion | Cast owed vote | Blocked after own vote |
|---|---:|---:|---:|---:|---:|
| Plain history, `wait` | 23 | 15 | 1/2 | 2/2 | 0/2 |
| Explained, `wait` | 8 | 2 | 2/2 | 2/2 | 2/2 |
| Explained, `wait_for_change` | 7 | 1 | 2/2 | 2/2 | 2/2 |
| Explained, `await_change` | 7 | 1 | 2/2 | 2/2 | 2/2 |

A voluntary silent wait would also be a valid discussion choice. The plain-history model spent all five calls rereading the first tally during the second discussion. Both longer names saved one read in the first post-submission position. Across these probes nobody requested a forced wait. [Calls by position](choices.jsonl)

To test the names without a reply suggesting the tool, give off-turn P2 one fresh board read during P0's first build and P1's second build on the same deal. Offer exactly one waiting tool at a time. The model failed to block within five calls in all ten presentations, including `poll` and `monitor`. It queried state, compacted notes or attempted unavailable actions. Every spelling used the same description, cursor and force semantics. We kept the existing name. In concurrency terms the model waits for a condition on its seat projection. The local client does the repeated host polling. A stale cursor or owed decision satisfies the ordinary wait immediately. [Off-turn calls](off-turn.jsonl) · [Python condition waits](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Condition.wait_for)

## Live games

All runs use seed 11301, the same three original roles and hands, the same three-tile store and initial draws, a two-square offset and two-tile starting hands. Three or four independent conversations share one FIFO inference queue and one resident Qwen3.5 9B Q8_0 at 32k context, temperature zero, model seed one. Discussion is 30 seconds and the decision window is 45 seconds. Discussion can close early when every living seat has spoken. The extra seat receives two unused paper-kit tiles. Model calls, wall-clock scheduling, nominations, returns and subsequent play can diverge across runs.

| Interface and seats | Wall seconds | Timely choices | Timely/min | Remarks / seat-windows | Matching history reads / consecutive repeats | Longest queue for owed choice, s |
|---|---:|---:|---:|---:|---:|---:|
| Previous wait, three | 166.28 | 15/15 | 5.41 | 4/6 | 43 / 40 | 6.88 |
| Ballot guidance, three | 169.20 | 24/24 | 8.51 | 15/15 | 0 / 0 | 6.39 |
| Refreshed tools, three | 134.80 | 15/15 | 6.68 | 4/6 | 2 / 0 | 5.53 |
| Refreshed tools, four | 288.33 | 28/28 | 5.83 | 12/12 | 8 / 1 | 9.76 |

A matching read asks for the current stage's ballot kind. A consecutive repeat requires the same seat, revision, phase, filters and returned IDs on successive calls. The original 43 reads include one after voting opened. Some reads retrieve useful older evidence. In all three new games every accepted vote's request included the last public remark. Each row is one trajectory on one small deal.

The first guided game had three additional removal ballots. All failed unanimously. At its second nomination P2 named P1, P0 responded as though P0 were the nominee, and P1 claimed everyone was Red. There were no ballot-history queries anywhere in that game, so its throughput alone cannot establish an effect of the history reply. Five unoffered ballot calls got phase-specific guidance and all five seats voted on the very next call. This exposed a second defect. While inference was running, voting opened, but the rejection could still list tools from discussion. The refreshed client now lists tools from the same snapshot as its recovery message. Rejected calls never submit a vote. [First guided game](early/game.json) · [Refreshed three-seat game](refreshed/game.json)

### Four seats and a decisive first vote

Blue P0 inspected four distinct piece/square pairs before proposing a westward step. All four players spoke in favor, then voted Yes. P3 called moving to (-3, 0) progress toward EXIT at (0, 0). The store held two tiles, giving the table at most two further moves. Even with perfect future tiles and unanimous cooperation the marker could only cover two of the three squares. Red won on turn three, one square short. On the final proposal P0 still described the board as open for future expansion. These are statements and choices from the replay. They leave open whether the Red speaker was bluffing. [Four-seat game](four/game.json)

Rejecting the opening step preserves a real chance. In a scripted continuation the three Blue ballots reject it, everybody passes nomination, P1 bridges (-1, 0) with its held face 44 in printed orientation, and P2 proposes entering EXIT on the final turn. The referee gives Blue the win. This is an existence proof conditional on later cooperation, including P1's. Only events through the first proposal and its discussion are observed in this alternative. [Counterfactual replay](decline-west.json) · [Paired horizon probe, #128](https://github.com/othercriteria/footsteps/issues/128)

The four-seat run also had 111 background calls out of 179. Those used 146.42 seconds of inference service after subtracting queue time. Of 56 off-turn board reads, eight immediately followed a board read at the same visible cursor. The other reads include changed states and reads separated by other actions. This narrow measurement identifies a repeat without classifying the remaining time as strategy or waste. The fourth seat and third turn changed both the work available and the queue load. The original identical-page loop was rare here, but inference for background seats remains worth measuring independently of the move-budget mistake. [Queue experiment, #117](https://github.com/othercriteria/footsteps/issues/117)

## Reproduction

The frozen comparison and first live guidance run use the interface at `2f3f79f`. The refreshed three- and four-seat games use the interface at `40d77e0`. Run each game separately against localhost Ollama, with fresh output directories and the owner-trace parent already present. The audit commands use only the shared records. Clocks and scheduling can change play even with the same model seed.

```sh
# Frozen and first guided live run, at 2f3f79f
python -m experiments.ballot_polling /tmp/126-choices.jsonl
python -m experiments.ballot_polling /tmp/126-off-turn.jsonl --off-turn
python -m experiments.early_ballot /tmp/126-guided /tmp/126-private-guided --early-ballot

# On the refreshed interface
python -m experiments.early_ballot /tmp/126-three /tmp/126-private-three --early-ballot
python -m experiments.early_ballot /tmp/126-four /tmp/126-private-four --early-ballot --extra-blue
python -m experiments.early_ballot experiments/ballot-polling/four
python -m experiments.efficiency_reads /tmp/126-private-four
python -m footsteps replay experiments/ballot-polling/decline-west.json
```

Read the actual games in the offline viewer with `python -m footsteps view experiments/ballot-polling/four/game.json --omniscient -o /tmp/four.html`. The study contains the full referee records for analysis, projected and redacted call receipts, and model residency summaries. Only the local owner gets raw seat traces.
