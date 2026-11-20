# A blinded guest takes a seat

One Codex sub-agent joined four Qwen3.5 9B Q8 seats in a fresh five-player game. A fresh seed determined seating and the private deal. The guest seat and role shuffle used separate random streams. We used the first generated deal. The guest received a clean conversation, the public rulebook and a dedicated seat terminal. It had no access through that terminal to the RNG seed, full record, other hands, other players' notes or their withheld votes. The agents shared a host filesystem; blinding relied on the guest following its instruction to use only its seat terminal and rulebook. The guest supplied its own actions and private observations. Other seats used the existing assisted policy.

P2 drew Red and was told P1 was the other Red. That gave P2 perfect knowledge of every alignment from setup. The test therefore concerns decisions and interpretations of behavior from an informed seat. It cannot measure whether a Blue guest would correctly identify Red.

## Worked turn

On turn two the marker could step north onto face 37 at (0,1). Its single outgoing arrow points east. Before the movement ballot resolved, the guest recorded that approving an apparently helpful step would let it close the eastern square on its own upcoming build. At event 24 P2 used face 246 at (1,1) in printed orientation. That face has four exits but accepts entry only from the east and south. The marker had to enter it from the west. The board is write-once, so no future tile could repair the trap. Quarter-turning that same face once or twice would have allowed the marker through.

P3 later credited P2's placement with moving the marker. P2 publicly challenged the claim by pointing to the marker still at (0,1). The correction was accurate and omitted P2's own responsibility for the trap. Both the time-stamped observation before voting and the subsequent construction are available in the owner's omniscient export. The public record shows the legal move, oriented arrows, ballot and words heard by the other seats.

P2 alone backed that accusation at event 34. At event 51 the other four seats, including its Red ally, voted P2 out. Red still won by depletion on turn eight. Before seeing any result, the guest distinguished three things in its debrief. It knew P1's role, it could verify that the marker stayed, and it could only speculate about whether P1 had deliberately set up the trap or whether P3 had misunderstood it. One practical ambiguity was that the first store count was shown after the draw and before the return. [Postgame record](game/1244867160-bad1+2.json) · [Ballots](game/choices.csv)

Four guest decision notes originally lacked the record identifier. The local viewer notes were recovered by matching each original private request, revision, seat, turn, command and observation, then checking all 114 notes against the replay. The runner now sets the identifier before dispatching every decision, with an end-to-end regression for guest build notes. The public events and ballots needed no repair.

## Run another blind seat

Start a host with a fresh empty exchange directory and separate destinations for the postgame record and private notes. Provide the guest only the copied rulebook and the terminal in the exchange directory. A new game chooses a fresh seed; add `--seed 1244867160` to reconstruct this deal. Decisions still depend on the participants. The virtual clock advances through referee phases when a decision is submitted. This playtest does not measure workstation timeouts.

```sh
work=$(mktemp -d)
python -m experiments.guest_game --exchange "$work/seat" --out "$work/game" --private "$work/notes"
```

The guest runs `python seat.py next` in its seat directory and responds with `python seat.py submit ID 'JSON'`. Requests include the new seat history since its previous packet and the exact legal values for the present decision. An observation accompanies each reply. Only the `speech` field of a speech reply is spoken publicly. The final request asks for a debrief before the host reveals the lineup or winner. A Red guest keeps the team knowledge it was granted from setup. The host saves the response in `guest-debrief.md` beside the private notes. Keep the seat exchange private as well.
