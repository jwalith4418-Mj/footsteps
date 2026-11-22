# Decisions behind the first rules

The [design review after the social trials](design-review.md) ranks the open questions and specifies an opening-protection comparison for human play.

| Decision | Design reason | Evidence to revisit |
|---|---|---|
| The exit is a special open tile and cannot seed construction. | A single unenterable tile on the exit would be permanent sabotage. Growing only from the start keeps the expedition on one connected floor. Traps on the approach remain possible. | Whether a Red team can create a consequential obstacle in a forgiving setup. |
| Last draw takes one and skips discard. | Hand size stays constant and a post-deal bag of S tiles provides S opportunities to move. | A proposed effect changes hand size or bag depletion. |
| Every living player gets one nomination opportunity; roles stay private on removal. | The procedure is bounded and unambiguous. Elimination ends play for that seat, so its timing matters. | Turn and evidence at first nomination, duration sitting out, cascading eliminations. |
| Timeouts are visible. | Silence counts as no on a ballot. Staying and passing are ordinary actions; required construction has a legal fallback. Visibility preserves public evidence about reliability. | Repeated missed deadlines dominate an otherwise playable agent game. |
| Store realized randomness and versions. | An old example should survive a changed generator and be usable from the perspective of a specific seat. | New tile effects, hidden information, or replay migrations. |

Footsteps is the provisional title. The floor and exit suggest an indoor setting. The [minority-team trials](../experiments/minority/README.md) informed the choice of Blue and Red for all play.

The [seat rating design](ratings.md) specifies matched substitutions on both teams and the evidence needed before publishing skill estimates.

New games anchor coordinates at EXIT by default. The [matched origin trial](../experiments/exit-origin/README.md) checks the distance calculation and route choice separately. Public speech, actions and referee records share the origin chosen at setup.

An optional live-table placement check asks the builder to read a specific edge. A second question asks whether the marker is on the chosen origin. Keep both available for model trials. Track first answers, corrections and random fallbacks separately from whether the move helped the team. [Placement trials](../experiments/placement-check/README.md)

Keep quarter turns in base-1. Requiring printed orientation reduced cooperative wins on matched paper-kit deals. Hand rotation tables and private lookup are optional seat interfaces. [Matched games and model choices](../experiments/rotation/README.md)

Offer native placement and reversible per-copy orientation as opt-in seat interfaces. Keep indexed play available as a control. The first model used its hand to solve explicit port puzzles, and rarely turned pieces during tactical play. Distinguish finding a useful square from reading the tile that fits it when evaluating future aids. [Native action trials](../experiments/native-actions/README.md)

For social model trials use an explicit consequence for each floor action when studying play above basic pathfinding. Keep the ordinary seat as a control. A stated first landing and feedback on a single build were insufficient in the short solitaire probes. The assisted seat preserved directed detours and reached EXIT on held-out games. [Goal-pursuit gate and social transfer](../experiments/goal-pursuit/README.md)

Revisit each strategic aid before promoting any assisted client to normal play. The graduation trial removes the best-landing hint, automatic enumeration and team-specific strategic coaching separately while preserving the public clock, legal action explanations and private piece manipulation. [Training-wheels removal criteria](https://github.com/othercriteria/footsteps/issues/93)

For the persistent client, spend inference time on choices the player makes for itself. Give it access to current legal actions, its held pieces and attributed public evidence. Keep player-requested inspections visible in the experiment receipts. Test a strategic hint separately, then remove it on a fresh board or disputed ballot to see whether the behavior transfers. Report elapsed table time alongside missed decisions and speaking opportunities so a faster run cannot conceal a silent table. [Persistent runner trials](../experiments/persistent-panel/README.md)

Try early voting when no living player can still speak. Today's single remark per player makes that point observable. With multiple remarks, a player could instead explicitly surrender the floor while continuing to listen. Compare a small reserve bonus for yielding early with uncompensated yielding before choosing a mechanism. [Early ballot](https://github.com/othercriteria/footsteps/issues/116) · [Floor cession and reserve](https://github.com/othercriteria/footsteps/issues/121)

### Should a living Red majority end the game?

Keep the base-1 ending while testing this alternative. A strict majority of Reds can reject every step until the bag empties and block every attempt to remove a Red. This gives them a winning strategy even without another nomination opportunity. On a timed table, every Red could stop responding and their missing ballots would still count as No. At parity the builder can break a tied movement ballot, so the same argument does not apply. With only one starting Red, that Red can first have a strict majority when the last Blue is gone, which already ends the game.

An immediate majority win would convert the ability to force a win into an awarded result. It would save real table time and eliminate late Blue wins caused by a Red ballot mistake or defection. It would also make continuation public evidence about hidden roles. From two Blue and two Red, if the first removal leaves three players and the referee continues, everyone could deduce that the removed player was Red. Base-1 keeps that deduction open. Starting a variant with more Red than Blue would end it at setup.

The [nomination study](../experiments/nomination-publicity/README.md) includes a replayable position with two Red and one Blue left, one tile in the bag and an open route to EXIT. Changing one Red vote changes the winner under base-1. To test a majority ending as game design, announce it before setup and compare how people nominate and vote while the teams are still even. Scoring an existing transcript can measure the play it would cut, but players in that transcript had the base-1 incentives. [Announced-variant playtest](https://github.com/othercriteria/footsteps/issues/142)
