# Where the clock goes in complete games

Five games ask which work could be removed while preserving timely decisions and opportunities to speak. All seats use independent persistent conversations with Qwen3.5 9B Q8_0 at 32k context, drawing from a single FIFO Ollama queue on an RTX 4090 (24 GiB). Each required decision has a 45-second wall deadline. Simultaneous voters share that deadline. Each social ballot has a 30-second discussion window. The model sees the remaining whole seconds on every request. Both model settings and the referee are identical across arms. Mild concurrent CPU use was reported during the study. Its effect was unmeasured.

## Deals and comparisons

Seed 11301 supplies one deal per mode. In solitaire EXIT is two east and one north of START, with a two-tile hand and four tiles left in the store. Each directed entrance and exit bit has independent probability 0.55. The social deal uses the shuffled paper mix, with P0 Blue, P1 Red, P2 Blue, two tiles per hand, three tiles left in the store, and EXIT two east of START. Both use EXIT at (0, 0). All seats play their own builds, returns, proposals, remarks, nominations and votes. The ordinary referee supplies a choice or No on timeout and records it.

Each control uses the persistent session as it stood at the start of this study. The repeat treatment returns a short reminder and available commit tools for consecutive identical reads at the same private-view cursor. A changed query, intervening tool, visible change or context reset restores a full result. The separate social idle treatment permits one background inference per unchanged seat view. After using it a seat sleeps until the view changes. A right to speak or a required choice permits ordinary inference immediately. The three treatments keep the same rulebook and replay format.

The game order was solitaire control, social control, solitaire repeat, social repeat, social idle. A game starts after warming the model and ends when all seats observe termination. Each timing record includes the model digest, allocated context and VRAM residency. Identical seed, temperature zero and model seed one do not freeze the real-time conversation. A different second on a clock, a different tool or a different return can produce different subsequent play.

## Complete games

| Game | Wall seconds | Timely / owed | Timely per minute | Remarks / speaking opportunities | Marker steps | Result |
|---|---:|---:|---:|---:|---:|---|
| Solitaire control | 78.7 | 11/12 | 8.39 | — | 1 | Red T4 |
| Solitaire repeat | 62.1 | 12/12 | 11.60 | — | 1 | Red T4 |
| Social control | 188.8 | 14/15 | 4.45 | 5/6 | 2 | Blue T2 |
| Social repeat | 300.0 | 24/24 | 4.80 | 15/15 | 2 | Blue T2 |
| Social idle | 437.5 | 21/24 | 2.88 | 14/15 | 2 | Blue T2 |

## Reproduce

From the repository root, start Ollama with the model installed. Choose empty output directories. Each invocation plays one game. Run them serially when sharing one accelerator. Private files contain the seats' private data. Committed seat receipts retain serving times, tool categories and the kind of opportunity at submission.

```sh
mkdir -p /tmp/footsteps-113-games /tmp/footsteps-113-owner
for mode in solo social; do
  python -m experiments.game_efficiency "$mode" "/tmp/footsteps-113-games/$mode-control" "/tmp/footsteps-113-owner/$mode-control"
done
for mode in solo social; do
  python -m experiments.game_efficiency "$mode" "/tmp/footsteps-113-games/$mode-repeat" "/tmp/footsteps-113-owner/$mode-repeat" --repeat-aware
done
python -m experiments.game_efficiency social /tmp/footsteps-113-games/social-idle /tmp/footsteps-113-owner/social-idle --idle-budget
python -m experiments.efficiency_reads /tmp/footsteps-113-owner/social-repeat
```

The committed games can be inspected without a model. Run the table report on any game directory to inspect per-seat and discussion outcomes. The audit takes optional `--base`, `--cap` and `--refill` values in seconds.

```sh
python -m experiments.efficiency_audit experiments/game-efficiency/{solo-control,solo-repeat,social-control,social-repeat,social-idle}
python -m experiments.persistent_table experiments/game-efficiency/social-control
python -m footsteps view experiments/game-efficiency/social-control/game.json --omniscient -o /tmp/113-control.html
python -m footsteps view experiments/game-efficiency/social-repeat/game.json --omniscient -o /tmp/113-repeat.html
python -m footsteps view experiments/game-efficiency/social-idle/game.json -o /tmp/113-idle-public.html
```

## What the calls tell us

In solitaire the control made 75 requests, 39 of its successful reads repeating the immediately previous arguments and referee revision. Its paired seat took 54 requests and submitted all 12 decisions. **That seat never triggered the shortened receipt.** Both seats moved once and lost on turn four. The 17-second wall-time difference cannot be credited to the treatment. In social repeat, seats actually received 35 shortened replies, still used 177 seconds on background requests, and spoke in every one of 15 eligible seat-windows. Three additional removal ballots alone introduced 90 seconds of scheduled discussion.

In social control, six valid opportunities to speak produced five remarks. During the second movement discussion P2 attempted to cast its vote 28 times before the ballot opened. A reply before the deadline and a useful turn at speaking are different measures. The audit counts actual remarks from the referee record. An unrestricted FIFO gave background requests roughly 60% of all service in both the control and repeat social games, including time seats used to read what others said.

## Replays to discuss

* **Social repeat, T1 events 6–11.** Red P1 nominates P0, then tells the table that P0 should stay and casts No. Everyone votes No. P2 then nominates P1. P0 responds as though P0 were the nominee. Finally P0 nominates P1. Three genuine removal ballots give the conversation a different shape even though the marker follows the same route as the control. At T2 events 15–16, P1 proposes EXIT, publicly asks for Yes and casts No. The other two approve and Blue wins. The record establishes the discrepancy between speech and ballot. Whether the speaker intended deception remains open. For a blind reading, omit `--omniscient` from the viewer command.
* **Social control, T1 event 3 and T2 events 12–13.** The random return belongs to P0. The referee record identifies the timeout, while the call receipts identify the waiting time. At EXIT, P1 again urges Yes. This time P1 also votes Yes. A short game can contain both an infrastructure failure and an entirely on-time decision that costs a team the game.

* **Social idle, T1 events 6–9.** P1 identifies as Red while arguing for P0's removal. P0 calls the nomination a Red move. P2 then nominates P1 and argues that P1 is Blue. P1 again says they are Red. All three vote to retain P1. This makes a short blind test of whether a listener can attribute a claim, recognize it could be a bluff, and act on it. [Social-evidence follow-up](https://github.com/othercriteria/footsteps/issues/64#issuecomment-7067305562)

## A seat's time reserve

The offline calculation starts each seat with 30 seconds in reserve. Each required decision gets 15 seconds of its own inference service free. Extra service draws down the same seat's balance. It refills by three seconds per numbered turn up to 30. Extra nominations grant no refill. The audit approximates own inference service as request latency minus time queued. It caps the charge at the remaining whole seconds after queueing. Each draw records how much wall time remained when the first request pushed the decision over 15 service seconds. There can be a subsecond discrepancy at the deadline. Voluntary discussion, background work and time spent blocked in the wait tool cost no reserve in this calculation. All saved games used the original fixed wall deadline.

The solitaire control's T2 placement spent 44.24 service seconds. Its first draw on reserve would have been visible with about 29 wall seconds left. On the owner's trace, 33 of 35 rotation inspections on this placement requested H4 at the same square. The social control's T1 return hit the same deadline after only 6.52 service seconds and 37.87 seconds queued. The seat attempted an unavailable tool six times. An own-service reserve would correctly leave its balance full. The submission clock and queued time give a separate signal that the opportunity to submit is disappearing. A trace that ends in a timeout cannot establish what a seat would do with additional seconds. [Live time-control experiment](https://github.com/othercriteria/footsteps/issues/114)

In the idle arm, P0 completed the return after 61 unavailable calls with just 1.37 seconds queued. P1 instead missed a movement ballot after 50 history reads, 49 of which returned no earlier movement ballot. On T2 P1 called `wait` while owing a build and a return with 33 and 40 wall seconds left. Each wait woke at the next revision after the referee had chosen for P1. Those two misses had only 7.64 and 2.71 service seconds charged. Across five games the shadow reserve would have started drawing on five decisions. Enforcing the proposed balance would have cut off one vote P0 actually completed. A visible balance is worth testing before imposing a penalty. A waiting seat also needs to know when the next visible change will be the expiry of its own choice.

## Where to spend the next experiment

1. **Help a seat recover from an unavailable tool and a deliberate wait.** On the social control return P0 requested `discard_tile` six times. The stage is called `discard`, the callable tool is `return_tile`, and the original reply said only “choose one available function.” On that dealt position, script one, six or sixteen bad calls, change only the last error reply and then allow five real calls. With the original wording the seat returned its tile only after the one-error prefix. Listing the currently offered functions recovered all three prefixes in one, three and two calls respectively. The persistent client now gives that list on unknown calls. The experiment retains the original wording for reproducibility. The next cheap test is showing the consequence of an owed `wait` before it can sleep through the deadline. These are different ways to lose a turn.
2. **Give decisions priority on the shared GPU and expose the seat's reserve.** The one-background-call limit reduced background service to 58 seconds from 113 in control and 177 in repeat. The idle game nevertheless took longest and missed three decisions. Priority with revalidation at dequeue could preserve useful preparation and let a new voter see an accurate clock. Measure timely choices, time queued, and ability to hear and answer a remark together. [Queue experiment](https://github.com/othercriteria/footsteps/issues/117) · [Time control](https://github.com/othercriteria/footsteps/issues/114)
3. **Open the ballot once all living players have spoken.** In social repeat, the last successful speaking request finished with roughly 76 of the game's 300 wall seconds cumulatively left on fully used discussion windows. In idle it was 97 seconds across four windows. These are upper bounds taken just before submitting the final remark. Listeners still need to receive it and deliberate. Keep the original deadline for silence. [Discussion timing experiment](https://github.com/othercriteria/footsteps/issues/116)
4. **Test a cheaper representation before changing models.** On a frozen movement decision after 16 reads, removing JSON whitespace from seat messages reduced the prompt from 11,282 to 8,722 tokens (23%) and empty-cache prefill from 1.01 to 0.80 seconds. Exact-repeat prefill was 0.071 seconds for both. The model requested state with one encoding and proposed a step with the other, so even a lossless re-encoding needs a play check. On the social control, 12 calls reaching the output cap consumed 46 service seconds. Shorter replies and faster models deserve trials on frozen recoveries and ballots before a full table comparison. The earlier panel found a substantial role-reading cost to using 4B. [Model panel](../persistent-panel/README.md)

Run the two small comparisons separately on the same local model. The prefill study unloads and rewarms the model for each encoding. The recovery study uses the same T1 placement, held pieces, 45-second frozen clock and scripted mistaken calls. Elapsed inference times are real. Its five-call limit tests recovery, independent of the live table clock.

```sh
python -m experiments.persistent_prefill /tmp/113-original.jsonl --contexts 32768 --reads 16
python -m experiments.persistent_prefill /tmp/113-compact.jsonl --contexts 32768 --reads 16 --compact-json
python -m experiments.return_recovery /tmp/113-return.jsonl
```

## Does it help to state that winning is the seat's only objective?

The persistent system prompt describes both victory conditions and how removed players share the result. The private state includes the seat's team. The system prompt leaves the imperative to pursue that victory implicit. Restore the social control board and its actual T2 proposal to enter EXIT. Start a fresh session just before its movement ballot. Hold the other two ballots at a sealed split, making the focal voter decisive. A Yes ends the game for Blue. A No prevents immediate Blue victory. The seat sees only its own projection, with the ordinary tools and up to five model calls.

Cross the voting seat (P1, the builder, or P0) with its team, retaining one Red, then repeat with the two actual public EXIT remarks from P1 and P0 restored. Each advocates Yes. In swapped-roster cases their words are held fixed. The eight cases share the same board and do not recreate the original private model conversations. Each treatment changes only the opening system instruction. The extra named-team arm substitutes the seat's already-known team name.

| Added instruction | Blue approved EXIT | Red blocked, silence | Red blocked, with remarks |
|---|---:|---:|---:|
| Original prompt | 4/4 | 2/2 | 0/2 |
| “Your only objective is for your team to win the game.” | 4/4 | 0/2 | 0/2 |
| Same sentence plus zero-sum and avoid giving opponents a win | 4/4 | 0/2 | 1/2 |
| “Your only objective is for Blue [or Red] to win the game.” | 4/4 | 0/2 | 0/2 |

The extra risk wording helped the Red proposer once in the discussion condition. Both generic and named short instructions instead elicited Yes from every seat. A correct Blue vote alone therefore tells us little here. Keep the existing wording for now. The next test should also include the preceding *proposal*, where Red can simply stay instead of offering Blue an immediate win, and a second board where a risky step is worthwhile. All runs used one deterministic model configuration. They measure a local ballot response, not team strength. [Pivotal EXIT question](https://github.com/othercriteria/footsteps/issues/101)

```sh
python -m experiments.team_objective /tmp/113-objective.jsonl
python -m experiments.team_objective /tmp/113-objective-remarks.jsonl --exit-remarks
python -m experiments.team_objective /tmp/113-named.jsonl --named-only
python -m experiments.team_objective /tmp/113-named-remarks.jsonl --named-only --exit-remarks
```
