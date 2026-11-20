# What is a good reason for a bad player to cooperate?

At event 5 on deal 8401, P2 can vote either way and the opening move still passes. Both other seats have publicly promised to approve it and to nominate dissenters. In the original policy P2 voted no, was removed, and never got to build. With its team and the ballot outcomes spelled out, P2 voted yes and kept playing. At event 45 P2 was the builder, one step from EXIT on the final turn. It proposed staying and won. Event 15 is a useful check on any overly tidy interpretation: P2 opposed its own nomination of P0. These are a model's decisions against scripted opponents. [P2's game](fresh-8401-payoff-trust/8401-P2-bad.json) · [Original policy, identical deal](fresh-8401-baseline/8401-P2-bad.json)

## Trust, survival, and the team result

We started with the actual 8201 turn-two ballot, including P0's public speech. We also swapped seat assignments and reversed menus on shorter, referee-legal positions. On the quiet opening, everyone just approved the same helpful step. On the decisive controls, a vote can enter EXIT, irreversibly trap the marker, or remove the last good player. The two-bad/one-good controls make the identities of bad teammates relevant. After entering a sealed region a bad player need not stay alive to win. We assigned neither self-removal nor self-preservation a required answer in that position.

| Qwen3.5 9B condition | Reject own removal on 8201 / 2 | Bad supports ordinary progress / 4 | Good passes after unanimous progress / 2 | Favors team result on decisive ballots / 24 |
|---|---:|---:|---:|---:|
| Guided movement and prior elimination receipt | 0 | 0 | 2 | 14 |
| Add shared cue about earning trust | 0 | 0 | 2 | 12 |
| Add human motives to trust cue | 0 | 0 | 2 | 13 |
| Add instrumental motives to trust cue | 0 | 0 | 2 | 13 |
| Seat-relative consequences and trust, model chooses | 2 | 4 | 0 | 14 |
| Assisted policy | 2 | 4 | 2 | 24 |

The human cue says the player wants their team to win and wants to keep playing and make a difference while the outcome is open. The instrumental cue describes future builds, votes and credibility as resources valuable to the team. Both explicitly allow a posthumous win. Neither wording repaired the self-vote on its own. The paired orders are repeated presentations of the same positions. The notes are statements a model made about its choices. An observer cannot infer a native drive, or even a stable intention, from an agreeable vote.

Several plausible prompt edits exchanged one mistake for another. Labeling a proposed result from the seat's perspective corrected the self-vote but got a bad seat to approve entering EXIT four times out of four. Asking for the name of the desired outcome made the model reject all four EXIT presentations as good. Llama 3.1 8B also approved EXIT as bad in all four tests with the human wording. The CSVs retain the menu reversals, both roles, intermediate presentations and the second-model check.

**How the assisted player works.** Construction uses the existing player. On social decisions a compact private prompt identifies the seat's objective, options and public history. An explicit announcement such as “I intend to vote yes.” is treated as a conditional prediction for that ballot. The model remains responsible for nominations, for its defense on 8201, and for a vote that would only signal agreement if the other players keep their word. Before a proposal or ballot, a deterministic policy prefers a known team win over an unresolved outcome, and either over a known team loss, conditional on the choice taking effect. It checks the EXIT square, remaining moves, sealed components, and a last-good removal identifiable from that seat's information. Staying executes immediately. With multiple equally preferred commands the model chooses among them. With a unique preferred command the policy submits it and identifies itself in opt-in replay notes. A tied forecast from two different personal votes (the same public result either way) leaves the menu open for signaling. Players can misstate their intentions. These are preferences of one player; the referee still accepts all legal commands.

In the table above, the software made all 24 assisted decisive choices. The 8201 self-defense, ordinary opening votes and quiet nominations remained model decisions. Giving the raw payoff labels to the same model did not achieve that decisive-ballot result.

## Opponents who act on visible evidence

The paper floor remains at (4, 2) under base-1. Every builder uses the same shortest optimistic build and least-connected discard. One model seat chooses its own proposal, movement votes, nominations and elimination ballots. Two scripted opponents announce their own movement intentions; both support closer moves and nominate a player who explicitly voted no on a closer move. They support that removal. The bad script delays on its own proposal. No policy sees another hand, ballot-in-progress or private note.

Each deal crosses model seat P1/P2 and model role good/bad. P0 is always good. We used six post-deal tiles for a tight clock and ten for the standard three-seat store. A tight game takes the first six tiles of the shuffled post-deal store. In the tight setup a bad builder can spend one move to make reaching EXIT impossible. This deliberately creates an opportunity where survival is useful. Shared seeds hold the deal and random streams fixed up to divergence.

| Pair | Bad model gets a build | Bad model's team wins | Good model's team wins |
|---|---:|---:|---:|
| Baseline, 8401 tight and 8402 standard | 0/4 | 0/4 | 2/4 |
| Model selects from labelled payoffs, same deals | 4/4 | 2/4 | 2/4 |
| Baseline, confirmation 8411 tight and 8412 standard | 0/4 | 0/4 | 2/4 |
| Assisted, same confirmation deals | 4/4 | 2/4 | 2/4 |

Both confirmation bad wins were on 8411. The model decided to signal cooperation in both opening seatings; the outcome policy then spent a turn to put EXIT beyond reach. With the standard clock, staying alive did not secure either bad win. Good model seats already advanced the ordinary step and survived in both conditions. The opponents respond to a known public signal and ignore subtler sabotage. Different lineups will assign that signal a different value.

In a separate frozen dilemma the two announced votes split. Supporting a move onto a sealed tile assures the bad team a win and exposes the focal seat to a stated threat of removal. Baseline, trust-only, human and instrumental all rejected it 4/4. Payoff labels alone produced two approvals; the assisted policy selected all four mechanically. In the P2 seating, a legal continuation actually does eliminate P2 and awards it a posthumous win. Vetoing instead allows good P1 to enter EXIT next turn. When P1 is bad it also has a later chance to force depletion as builder, so this seating does not strictly require the sacrifice. The regression test adjudicates both P2 continuations.


## A whole table of models

On fresh deal 8501 we ran each presentation twice, swapping the bad seat between P1 and P2. All seats controlled their own floor play and had the opportunity to speak. The baseline produced no remarks or bad nominations and one good win. The raw payoff prompt produced 25 remarks, ten bad nominations and two good wins. Assisted seats produced 17 remarks, twelve bad nominations and two bad wins. One good player was removed in each assisted game. The fixed opening, two seatings, and deterministic model make this a transfer check. They give little basis for estimating team balance or claiming that more accusations are better play. The frozen positions and paired scripted opposition isolate the change in first-turn behavior more clearly.
## Reproduce

The original wording and all experimental arms are pinned at commit `7a5d377`. Subsequent improvements to agent-facing role information can change regenerated choices. Saved game records replay without a model service, and the audit compares the cross-play CSVs with the actual events. All model arms used a local RTX 4090, Ollama 0.40.15, 4096-token context, temperature zero, inference seed one, and disabled thinking. The main model tag was `qwen3.5:9b-q8_0` (ID `a8ee95bc3592`). All compared model decisions requested a private note. The in-process Table uses a virtual clock and real inference; the experiment does not measure live timeout rates.

```sh
python -m experiments.behavior_summary experiments/social-behavior
python -m footsteps replay experiments/social-behavior/fresh-8401-payoff-trust/8401-P2-bad.json
out=$(mktemp -d)
notes=$(mktemp -d)
for arm in baseline trust human instrumental outcomes combined perspective perspective-trust payoff payoff-trust intent intent-trust assisted; do
  python -m experiments.behavior_probe --strategy "$arm" --out "$out/$arm.csv" --private-notes "$notes/$arm.jsonl"
done
for arm in baseline trust human instrumental payoff-trust assisted; do
  python -m experiments.behavior_probe --tradeoffs --strategy "$arm" --out "$out/dilemma-$arm.csv" --private-notes "$notes/dilemma-$arm.jsonl"
done
for arm in human payoff-trust; do
  python -m experiments.behavior_probe --model llama3.1:8b --strategy "$arm" --out "$out/llama-$arm.csv" --private-notes "$notes/llama-$arm.jsonl"
done
games() {
  python -m experiments.behavior_crossplay --seeds "$1" --store "$2" --strategy "$3" --out "$out/$4" --private-notes "$notes/$4"
}
for arm in baseline trust combined; do games 8301 6 "$arm" "tight-$arm"; done
for arm in baseline payoff-trust; do
  games 8401 6 "$arm" "fresh-8401-$arm"
  games 8402 10 "$arm" "fresh-8402-$arm"
done
for arm in baseline assisted; do
  games 8411 6 "$arm" "confirm-8411-$arm"
  games 8412 10 "$arm" "confirm-8412-$arm"
done
table() {
  panel=$1
  shift
  python -m experiments.social_evidence --start-origin --debate --arm receipt --bad-brief --model-floor --seeds 8501 \
    --out "$out/$panel" --private-notes "$notes/$panel" "$@"
}
table table-base
table table-payoff --social-guidance
table table-assisted --outcome-policy
python -m footsteps view "$out/fresh-8401-payoff-trust/8401-P2-bad.json" --omniscient \
  --notes "$notes/fresh-8401-payoff-trust/8401-P2-bad.jsonl" -o "$notes/8401-P2-bad.html"
```

The postgame JSON includes realized roles, hands, draws and public speech. Only the separately stored, owner-readable note files can populate the private commentary in an omniscient export.
