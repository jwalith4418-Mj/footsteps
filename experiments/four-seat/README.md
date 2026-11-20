# Two Red teammates at a four-seat table

After the common-knowledge update we played deal 8602 twice. P0 and P2 were Blue. P1 and P3 knew the whole lineup. On the printed kit nobody was removed in eight turns. On a generated 29-entrance, 29-exit kit, the Red team removed both Blue players on turn two.

**The pivotal listener.** In the 29/29 game, P3 had already publicly claimed to be Red on turn one. All four seats were still alive when P3 again nominated P0, after event 17. This time its public argument explicitly described P0 as Blue and identified the speaker with Red. At event 18 both Red players approved removal. Blue P0 voted no. Blue P2 supplied the third yes. In the matched listener query where only that last statement was muted, P2 voted no. With that vote substituted the 2–2 tie would have kept P0 in play. The remainder of such a counterfactual game was not played. P1 immediately nominated P2, and both Red seats voted to remove the last Blue player at event 20. The assisted outcome policy supplied those two final votes. [29/29 record](fixed/8602-red1+3.json) · [Actual and muted ballots](fixed/choices.csv)

**A falsifiable accusation.** On the printed floor all four seats approved a northward opening. The marker never moved again. Both Red seats nominated a Blue player at every opportunity, fourteen times in all. No nomination passed. At event 37 P1 nominated P2, then publicly claimed P2 had already been eliminated and called for a vote on P0. At event 38 the actual nominee P2 voted against their own removal. The public record is enough to identify all three seats involved and check the claim. Whether the speaker was bluffing or lost track of the nominee requires a separate probe. [Printed-kit record](printed/8602-red1+3.json) · [Follow-up question](https://github.com/othercriteria/footsteps/issues/64)

## Reproduce and inspect

Both runs used Qwen3.5 9B Q8, disabled thinking, temperature zero, and the assisted social policy. Each live seat made construction choices through its private view. The outcome policy can submit a uniquely preferred move, and records its own authorship in an opt-in note. Only a nominator could speak, immediately before the elimination ballot. For each other player who heard a remark, the experiment also obtained a vote on an identical snapshot with that remark omitted. Only the vote after the actual remark took effect.

```sh
out=$(mktemp -d)
notes=$(mktemp -d)
run() {
  panel=$1
  shift
  python -m experiments.social_evidence --start-origin --roles BRBR --arm receipt --debate --model-floor \
    --outcome-policy --seeds 8602 --out "$out/$panel" --private-notes "$notes/$panel" "$@"
}
run printed
run fixed --kit-counts 29 29 --kit-seed 8700
python -m experiments.social_summary "$out"
python -m footsteps view experiments/four-seat/fixed/8602-red1+3.json -o /tmp/four-seat-public.html
python -m footsteps view "$out/fixed/8602-red1+3.json" --omniscient \
  --notes "$notes/fixed/8602-red1+3.jsonl" -o "$notes/omniscient.html"
```

The saved postgame records include public remarks, roles, hands and explicit chance outcomes. Private explanations from the run are kept separately. The two setups used the same deal and draw seeds and equal total permissions. They change both the allocation across faces and the entrance/exit split. They supply inspectable examples of play. Estimating a balance effect would require multiple kits, deals and role layouts.
