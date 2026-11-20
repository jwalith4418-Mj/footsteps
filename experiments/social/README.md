# Who voted against the move?

On the first turn of seed 8001, the marker moved east from START, reducing its distance to EXIT from six squares to five. Two people voted yes and one voted no. We swapped which of P1 and P2 dissented. The good observer P0 nominated P1 and voted to remove P1 in both games. The private notes for both nominations described moving the marker. The ordinary replay shows two legal actions; only the second game lost a good player. [P1 bad](pilot/8001-bad1.json) · [P2 bad](pilot/8001-bad2.json)

## Frozen ballots

Starting from the opening above, the referee accepts three possible movement ballots. Everyone supports the move, P1 alone dissents, or P2 alone dissents. All three histories leave the same board and P0 hand. After P1 and P2 pass, query P0's nomination. In separate forks, commit a P0 nomination of each possible target and query P0's elimination vote. The nomination in these forks is supplied by the experiment, so agreement with one's own nomination may contribute to approvals. Repeat with the menu reversed. All calls include the same request for a short private explanation.

In the speech treatment the other non-target seat says “P1 voted no on our move toward EXIT. Vote to remove P1.” or the equivalent for P2. The claim is checkable. A no vote is evidence available to discuss; a player might have good reason to oppose a closer move. The outcome below is willingness to remove the nominee, not a score of how a human ought to vote.

| Game 8001 presentation | Approve when nominee actually voted yes (8) | Approve when nominee actually voted no (4) |
|---|---:|---:|
| Guided live seat prompt, quiet | 8 | 4 |
| Named target and explicit elimination consequences, quiet | 7 | 2 |
| Same with accusation | 8 | 4 |
| Add official movement ballots, distances, and caution about unsupported claims, quiet | 0 | 0 |
| Same with accusation | 5 | 4 |
| Add the nominee's own voting record in plain language, quiet | 0 | 0 |
| Same with accusation | 1 | 4 |

The full ballot table and cautionary instruction were introduced together. The nominee-specific receipt is the only subsequent change. Four false-claim presentations use the unanimous opening across two targets and two menu orders; the other four are accusations against the supporter when the other seat dissented. There are six underlying target/history combinations per floor. Menu reversals measure sensitivity to presentation. They do not supply independent games.

On seed 8002 the same receipt and accusation got **2/8 false claims approved and 4/4 true claims approved**. The first move goes north. This opening was held out from prompt development but comes from the pilot deals. On the east opening with receipts, all twelve quiet votes rejected removal. Simply checking the nominee's voting record did not on its own motivate an elimination. [Frozen choices](probes/)

## Complete games

Every deal uses the three-seat paper kit and a ten-tile store. P0 is always good. P1 and P2 exchange the single bad role on the same deal. All crossed runs reuse the deal, draw seed and build-tiebreak seed; once play diverges the bags and draws can diverge. These are replicated seat assignments on a small number of deals.

**One model observer.** P0 chooses its nominations and elimination votes. Everyone builds the best available optimistic turn plan and discards the least-connected face. Good proposes the selected walk and votes yes on closer moves. Bad builds with the same plan, votes the opposite way and begins proposing stays on its own turns from turn three. On turn two each surviving scripted seat nominates the other scripted seat. Each supports only removal of that other seat. This gives P0 a decisive ballot with all three alive. The scripts never hear the model's notes.

| Observer | Deals × bad seats | Good wins | Good eliminated | Bad eliminated |
|---|---:|---:|---:|---:|
| Guided prompt, pilot 8001–8002 | 2 × 2 | 2/4 | 2 | 2 |
| Guided prompt, fresh 8101–8102 | 2 × 2 | 2/4 | 2 | 2 |
| Public ballot table and caution, same fresh games | 2 × 2 | 4/4 | 0 | 0 |

All eight guided-prompt games removed P1 on turn one. When P1 was good, that player missed nine further group turns and the bad team won on depletion. The ballot-table observer improved the fresh outcomes by leaving both other seats in play. Keeping the cooperative builder was enough to win despite the scripted bad player. That result cannot establish that the observer identified the saboteur. [Fresh baseline](fresh-base/) · [Matched intervention](fresh-ledger/)

**Three model social seats.** Each seat independently chooses its nominations and elimination votes. Only the nominator may make one short model-generated public argument before an elimination ballot. Each other listener also gets a separate, unsubmitted vote on an otherwise identical snapshot omitting this one utterance. A frozen change in one listener's vote is distinguishable from a change in the recorded result. Earlier public remarks remain in both histories. Questions, private decision notes, and muted responses never travel to another seat.

| Social prompt and floor | Games | Good wins | Bad nominations / opportunities | Public arguments | Listener ballots changed by hearing argument |
|---|---:|---:|---:|---:|---:|
| Ballot table, scripted floor, 8201 | 2 | 2 | 0/13 | 1 | 1/2 |
| Add nominee receipt, same floor and deal | 2 | 2 | 0/13 | 1 | 0/2 |
| Add explicit private role card for bad, 8201 and 8202 | 4 | 4 | 0/26 | 2 | 0/4 |
| Same prompts, all floor decisions made by models, 8202 | 2 | 1 | 0/18 | 0 | No listening opportunities |

On turn two of 8201 with P1 bad, P0 nominated P1 but publicly asked the others to vote **no**. P0 then also voted no. With the ballot table, hearing this argument changed P2 from no to yes. The nomination failed both ways. With receipts neither listener changed. Explicitly reminding P1 it was the sole bad player led it to approve **its own** elimination. Its private note recognized it was the accused player while describing approval as eliminating a good player. There was no public role reveal. The same self-vote appeared in the fresh 8202 seating. [Public argument and revealed ballots, events 15–16](debate-role/8201-bad1.json)

For the final transfer pair, models also chose each placement, discard, proposal and movement vote through the guided live seat prompt with named directions and ballots. Both games lasted ten turns with six movement votes each. Every bad ballot was no and every good ballot was yes, even when one proposal took the marker farther from EXIT. Across **54 nomination opportunities there were 54 passes**. Good reached EXIT on the last move with P1 bad. With P2 bad the store emptied two squares away. No player had an opportunity to hear an elimination argument. [Final-turn escape](model-floor/8202-bad1.json) · [Depletion](model-floor/8202-bad2.json)

**Stopping decision.** The frozen intervention improved responses to an explicit, checkable accusation on two floors. In the games, adding the receipt changed no winner on matched deal 8201. Spelling out bad's role changed no winner or nomination count there either. Moving the entire floor to model control yielded two different outcomes but no social confrontation. Another seed sweep on the same lineup would mostly measure floor play. A different opponent willing to nominate, or a pivotal choice between self-preservation and a posthumous win, would test a different question. The rulebook and default player prompt are unchanged by these experiments. [Live ballot lookups](https://github.com/othercriteria/footsteps/issues/55) · [Cross-play test](https://github.com/othercriteria/footsteps/issues/57) · [Prioritized rules review](https://github.com/othercriteria/footsteps/issues/56)

## Reproduce and inspect

Run from the repository root in the locked shell. This run used Ollama 0.40.15 on a 24 GiB RTX 4090, model `qwen3.5:9b-q8_0` (local ID `a8ee95bc3592`), temperature zero, inference seed one, 4096-token context and thinking disabled. All agents use the same weights in independent requests. The experiment drives the real Table in process with a virtual clock, collects seat views before revealing simultaneous ballots, and calls localhost Ollama with a 30-second request limit. Inference errors abort the run. This measures decisions given a response, rather than live deadline reliability. Saved games replay exactly without Ollama. Regeneration can vary by runtime, and note-matching table IDs are deliberately fresh.

```sh
python -m experiments.social_summary experiments/social
python -m footsteps replay experiments/social/debate/8201-bad1.json
python -m footsteps view experiments/social/debate/8201-bad1.json -o /tmp/social-public.html

out=$(mktemp -d)
notes=$(mktemp -d)
game() {
  panel=$1
  shift
  python -m experiments.social_evidence --start-origin --out "$out/$panel" --private-notes "$notes/$panel" "$@"
}
game pilot --arm base --seeds 8001 8002
game fresh-base --arm base --seeds 8101 8102
game fresh-ledger --arm ledger --seeds 8101 8102
game debate --debate --arm ledger --seeds 8201
game debate-receipt --debate --arm receipt --seeds 8201
game debate-role --debate --arm receipt --bad-brief --seeds 8201 8202
game model-floor --debate --arm receipt --bad-brief --model-floor --seeds 8202

mkdir "$out/probes"
probe() {
  name=$1; seed=$2; arm=$3
  shift 3
  python -m experiments.social_probe "$out/pilot/$seed-bad1.json" --arm "$arm" "$@" \
    --out "$out/probes/$name.csv" --private-notes "$notes/probe-$name.jsonl"
}
probe base 8001 base
probe focused 8001 focused
probe claims 8001 focused --claims
probe ledger 8001 ledger
probe ledger-claims 8001 ledger --claims
probe receipt 8001 receipt
probe receipt-claims 8001 receipt --claims
probe receipt-north 8002 receipt --claims
python -m experiments.social_summary "$out"
python -m footsteps view "$out/debate/8201-bad1.json" --omniscient \
  --notes "$notes/debate/8201-bad1.jsonl" -o "$notes/omniscient.html"
```

The CSV event numbers are one-based committed events. A blank nomination means pass. A blank muted vote means the seat lacked a paired listening decision. The postgame JSON files include realized hands, roles and draws. The committed CSV and JSON exclude private explanations. Matched notes for the played events stay in the separate private directory. The `.muted.jsonl` files are counterfactual attempts and cannot be attached to a game. In the offline viewer the public remark appears on the nomination frame; the private notes on each ballot appear one frame later.
