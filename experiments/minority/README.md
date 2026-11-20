# When does it cost Red to say what they want?

At two Blue and two Red, the Blue seats cannot remove a revealed Red if both Reds vote to keep them. A strict majority requires a defection. Three Blue seats can remove a Red over unanimous Red opposition at either 3/1 or 3/2. That creates an incentive to conceal an allegiance while the result is open. A bad public argument can still pay off if nobody acts in time.

We kept two 8602 openings distinct. The quoted argument for removing P0 to prevent a Good win came from **the printed kit**, after a northward step. The fresh full games used **the fixed 29/29 kit**, whose original 2/2 game began with a step south. P0, P2 and the added P4 are always on the exit team. P1 always obstructs; P3 obstructs only in the two-Red layouts. The starting four hands, eight-tile store, draw seed, fixed goal (4,2), Qwen3.5 9B Q8 and assisted social policy are matched. The ordinary five-seat deal uses the same sixteen tiles and leaves six turns. For this matched experiment we explicitly enable `--paired-fifth-hand` and independently sample two physical faces from the kit and give P4 extra copies (140 and 58 here). The resulting eighteen-tile supply has 33 entrances and 32 exits. Each seat receives only its legal view.

## A lone Red, removed at different times

With Good/Bad names, P1 explicitly identifies itself as Bad at event 6. Its nomination of P0 fails and nobody nominates P1 that turn. P1 gets to build and stays at event 14. The marker is seven steps from EXIT with six moves left. On event 17 all four, including P1, approve P1's removal. The team's victory is already assured. The actual rules award it at depletion on turn eight. [Good/Bad game](four-classic/8602-bad1.json)

With Blue/Red names, P1 likewise opens with an explicit admission. At event 10 P0 nominates P1; at event 11 all three Blues vote to remove P1, over its own no. Both other Blue listeners voted no on this removal in the matched query with only P0's remark muted. The actual ballots pass it before P1 can build. All-Blue survivors then stay at event 15, making EXIT unreachable. At event 17 they also remove another Blue. The players knew that eliminations hide roles, so they could not simply look up whether Red had gone. [Blue/Red game](four-colors/8602-bad1.json) · [Actual and muted votes](four-colors/choices.csv)

Was the earlier removal in time? We kept the entire history through event 11, the same turn-two draw, the same draw RNG and the same three private hands. All survivors switched to a cooperative builder, approved each move and passed on nominations. The local exits policy reached EXIT on 64/64 tie-break seeds; route reached it on 20/64. All runs start from one position. Later discards can change later draws. The saved exits continuation reaches the goal on the final turn. This is a legal example of the opportunity that Blue earned. [Recovery record](recovery.json)

## Replaying the quoted remark

We reconstructed the first nomination in the printed-kit game. P1 nominates P0 after a unanimous move north. Good/Blue P2 is the listener. We crossed three rosters, two naming conventions, both menu orders and three speech conditions. P1 stayed silent, gave the quoted argument for preventing the exit team from winning, or prefaced that same argument with an explicit admission. We asked for P2's removal ballot. Separately we applied a fixed failed ballot (only P1 supported removal) and asked for P2's next nomination. Every seat in that second query sees the same named votes for its roster.

P2 rejected the removal of P0 in **36/36** presentations. Its own next nomination was much more sensitive to option order. With pass first, it passed **18/18** times. With the menu reversed, it never passed. Under silence it named P3 or P4 in **6/6**. After the quoted partisan remark it named P1 in **5/6**; after the explicit admission, **6/6**. The one exception named P0 at 3 Blue/2 Red with color names. The speaker's words could redirect an accusation while the choice to accuse depended on menu order. All 72 outputs concern the same opening and one listener. [Listener choices](listener.csv)

## A teammate votes for removal

In the 3 Blue/2 Red color game, P1 opens by arguing that removing P0 will prevent a Blue win. P0 tries to remove P1 at events 11–12. Only two of the three Blues support it, and both Reds oppose it. P1 survives to build and stays on turn two. By event 18, all three Blues and Red P3 approve removing P1. P3 then nominates P0 and invokes the group's shared desire to reach EXIT. Two Blues help remove P0 at event 20. At event 22 a Blue nomination takes out another Blue, leaving P3 and P4. P3's ally vote at event 18 was redundant and the clock already favored Red irreversibly. Its public argument could pass for Blue advocacy, but the sequence alone gives little reason to infer a planned sacrifice. [Five-seat color game](five-colors/8602-bad1+3.json) · [Ballots](five-colors/choices.csv)

On the same five-seat deal with Good/Bad names, neither team lost a player. P1 still spent the decisive second turn. Ten of the twelve public remarks said a Good player had just saved the group and removing them would help Bad, even as the speakers were nominating a player. Repetition and failure to track the subject limit what can be inferred about concealment. [Five-seat Good/Bad game](five-classic/8602-bad1+3.json)

## Asking speakers to consider their audience

We replayed P1's first opportunity to speak after nominating P0, on both the northward printed opening and the southward fixed opening. Every player had just approved the move. One prompt added a request to consider what opposing listeners would infer, why they might support the proposal, and whether silence would be preferable. Both prompts already permit silence and tell the speaker to keep their role private.

In the ordinary speaker condition, P1 explicitly identified as the obstructing side in **4/12** statements. These were the four lone-Red cases. In the other eight P1 nevertheless argued publicly for preventing the exit team's win or stopping progress. With the audience cue P1 explicitly named its actual allegiance **10/12** times. It claimed Good in the remaining two, both 3/1 games under the old names. In one it invented a nominated teammate and asked the table to save that teammate, even though P1 had itself nominated P0. None of the 24 outputs was silence. The two floor states and repeated allied rosters supply concrete contrasts, not independent samples. [All public statements](speakers.csv)

We played out the lone-Bad Good/Bad condition because it produced a false Good claim on both openings. With the audience cue for every speaker, P1 claimed Good at event 6. P0 tried to remove P1, and the nomination failed. P1 survived to spend the decisive second turn. At event 26 P1 openly identified as the sole Bad player, with the win already assured. It remained alive at depletion. The baseline lone Bad also secured the clock, despite explicitly disclosing on turn one. Changing every speaker's prompt and following a single trajectory cannot establish that the false claim caused P1 to survive. [Audience-cue game](four-audience/8602-bad1.json)

The listener experiment motivates testing whether deciding to nominate and selecting a target should be separate choices in the model interface. [Nomination follow-up](https://github.com/othercriteria/footsteps/issues/67)
## Reproduce

The local model is `qwen3.5:9b-q8_0`, temperature zero, seed one, thinking disabled, 4,096-token context. The game harness uses real inference and a virtual decision clock. Construction and ordinary social choices use the requesting seat's view. The assisted outcome policy can submit a unique preferred option and identifies its choices in optional local notes. Public discussion in these games is limited to the nominator speaking before the elimination ballot. The listener's muted query changes only the latest utterance. A counterfactual vote never enters the game.

```sh
out=$(mktemp -d)
notes=$(mktemp -d)
game() {
  panel=$1
  layout=$2
  shift 2
  python -m experiments.social_evidence --start-origin --roles "$layout" --arm receipt --debate --model-floor \
    --outcome-policy --kit-counts 29 29 --kit-seed 8700 --seeds 8602 \
    --out "$out/$panel" --private-notes "$notes/$panel" "$@"
}
game four-classic GBGG
game four-colors GBGG --color-teams
game five-classic GBGBG --paired-fifth-hand
game five-colors GBGBG --paired-fifth-hand --color-teams
game four-audience GBGG --audience
python -m experiments.social_summary "$out"
python -m experiments.minority_probe "$out/listener.csv"
python -m experiments.minority_probe --speakers "$out/speakers.csv"
python -m experiments.minority_recovery "$out/four-colors/8602-bad1.json" "$out/recovery.json"
python -m footsteps view "$out/five-colors/8602-bad1+3.json" --omniscient \
  --notes "$notes/five-colors/8602-bad1+3.jsonl" -o "$notes/five-colors.html"
```

The legacy layout letters `G` and `B` always identify the exit and obstructing teams respectively. `--color-teams` changes the names delivered to the players. A live host also accepts this option. Stored base-1 roles, ballot rules and the text players actually said remain replayable. The saved game records are full postgame accounts. The publication includes the attempted public speeches from the frozen probes and the votes; private explanations are kept locally.

Every full game here uses one deal, one model and fixed seat positions. Most games diverge after the opening. Replications across menus provide a sensitivity check on one position. The results do not establish how often people or other models conceal their roles.
