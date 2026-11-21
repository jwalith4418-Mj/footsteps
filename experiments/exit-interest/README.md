# Who benefits from the proposed step?

The open tables gave opposite examples. On 13401 Red P2 voted against a Blue builder's EXIT proposal. On 13402 Red P0 approved one. The other voters carried the move in both games. In the archived 9901 game, Red P3 proposed entering EXIT and Red P1 joined the unanimous Yes. These examples motivated testing the same public move under different private team assignments. [Open tables](../open-tables/README.md) · [Archived game](../pivotal-votes/9b-game/five-9901-clear-r320.json)

## Positions and paired votes

We froze the actual final proposal from 9901 and the fresh 13401 game before the ballots were revealed. We also built a five-seat nonterminal control. Its marker at (−1, −1) can step east onto face 8 at (0, −1). The landing is one square closer to EXIT. It has a west entrance and zero exits. Approving that step makes EXIT permanently unreachable, although two future turns remain. After rejection the referee accepts a continuation that builds north of START, steps north, and enters EXIT on the last turn. Red therefore benefits from approving the closer step. The runner checks the winning continuation and the losing branch offline.

On each floor the builder and one fixed observer each take the ballot in fresh sessions. We preserve the starting team counts. The five-seat tables allow all four combinations of voter and proposer team for the observer and two for the builder. The three-seat table has one Red, so distinct Red voter and Red proposer cannot coexist. One legal roster per pair is chosen by fewest changes from the recorded roles. Blue observers get identical input when the only change is a hidden proposer card. Red observers can see their Red teammates. Two players remained alive at the fresh terminal ballot. The observer's individual vote there cannot overrule the builder. We score whether the seat casts a ballot in its team's interest, separately from whether that ballot can decide the outcome.

Each seat uses the ordinary persistent system prompt, own projection, a frozen referee clock, zero discussion, 16,384-token context, thinking disabled, inference seed one and temperature zero. Historical remarks are omitted from all conditions. Seats can consult their normal tools, with up to five calls to cast a vote. We record the received boolean or a missing decision separately. No other ballots are submitted. A second request forks the seat's last pre-action messages and asks for its own team, who would win immediately on approval, and whether Blue could still reach EXIT. The fork gets neither the actual submission nor a referee outcome. Its answer never enters the voting conversation. This tests what a seat can report when asked, without establishing what caused its choice.

## Reproduce

Run sequentially against localhost Ollama in fresh paths. Omit the model argument for the offline check, which reconstructs the position and expected team pairs from the saved referee records. The shareable receipts contain submitted choices, structured predictions and tool names. Each live model saw only its own game information.

```sh
python -m experiments.exit_interest /tmp/101-9b.jsonl --model 9b
python -m experiments.exit_interest /tmp/101-27b.jsonl --model 27b
python -m experiments.exit_interest experiments/exit-interest/9b.jsonl
python -m experiments.exit_interest experiments/exit-interest/27b.jsonl
```

## What the models voted for

| Checkpoint | Archived EXIT | Fresh EXIT | Closer dead end | Correct own team | Correct immediate winner on EXIT |
|---|---:|---:|---:|---:|---:|
| Qwen3.5 9B Q8_0 | 5/6 | 5/5 | 0/6 | 17/17 | 11/11 |
| Qwen3.8 27B RANA layout | 6/6 | 5/5 | 0/6 | 17/17 | 11/11 |

The first three columns count submitted votes serving the focal team's interest. All 34 seats submitted. On EXIT the sole error was the archived Red proposer in the 9B block, who approved its own step. The 9B Red observer on that same board rejected it, including when the proposer was Red. On all three boards neither checkpoint's nonbuilder changed its ballot when only the proposer's team changed and the observer's team stayed fixed. For Blue this comparison includes identical projected inputs. For Red the roster difference was visible.

The control reverses which team benefits from a step toward EXIT. Every Blue approved the dead end and every Red rejected it. All twelve forecast forks reported that Blue could never reach EXIT after approval, but all twelve also predicted **immediate** Red victory. The referee continues play after entering the cul-de-sac. A team can be certain to lose before its loss is adjudicated. The reported prediction and the team's actual choice diverged on every trap ballot. The sample has one trap and two EXIT positions, with correlated role swaps. These decisions are consistent with a preference for a superficially favorable direction and do not identify an internal policy.

The terminal forecast exposed an ambiguity worth testing. Even after naming Blue as the immediate winner, 9B answered false to the inclusive question about whether Blue could still reach EXIT on all eleven terminal rows. 27B answered true on all six Blue rows and false on all five Red rows. We therefore scored the immediate-winner, own-team, reachability and actual vote fields separately.
