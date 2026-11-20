# Can a local seat see the guest's trap and play it?

At the [guest table](../blind-guest/README.md), Red P2 recognized before the turn-two ballot that the proposed landing had one open side, that P2 would build next if everyone survived, and that a tile already in hand could close that side. P2 then built exactly that trap. We tested those as two decisions for Qwen3.5 9B Q8. We also replayed a disputed stay and ran the same five local seats at two EXIT offsets. The probes receive a single legal seat view at a fixed event boundary.

## Seeing the opportunity

Before the turn-two vote, ask whether **you** can block every immediate exit on the next build with a tile already in hand. Cross two changes. Give the landing an exit back to START, and shift the focal Red seat behind the next builder by swapping two seats' hands and roles. Only the original position permits the tactic. Reverse the two answer choices for each of the four positions.

| Factual task | Ordinary prompt | Stage-specific wording | Tool offered | Tool output supplied |
|---|---:|---:|---:|---:|
| Next-build block, four positions × two orders | 6/8 | 6/8 | 8/8 | 8/8 |
| Marker after placement, before vote reveal, after reveal | 5/6 | 6/6 | — | — |
| Deliberate stays by P1 and P2 at the disputed removal vote | 0/4 | 0/4 | 0/4 | 0/4 |

The ordinary and stage-specific seats answered “no” even when they held the trap. The voluntary seat requested the landing comparison all eight times and answered correctly in both orders on the positive case. The tool checks the public turn order and tile arrows plus the requesting seat's hand. It conditions the next build on all players surviving. It cannot certify how a hidden hand or a future draw will be played. [Answers and tool selections](probe.csv)

## Executing the build

At the start of the guest's third build, use the actual hand and a second setup where its face 246 was dealt in a different printed orientation. Also swap Red P2 and Blue P3's roles as a Blue control. In every position a legal placement can permanently confine the marker, and another opens an immediate step with an optimistic route within the remaining turns. The latter assumes helpful future tiles. It does not establish a Blue win.

Each cell below has four decisions per side, from two orientations and two menu orders. The Red column counts certified permanent traps. The Blue column counts builds that open the immediate step and possible route.

| Placement interface | Red trapped marker | Blue opened route |
|---|---:|---:|
| Full indexed menu and ordinary guide | 0/4 | 0/4 |
| Full menu with stage-specific wording | 0/4 | 0/4 |
| Full menu with voluntary preview | 0/4 | 3/4 |
| Full menu with blocking placement explicitly given as three legal indices | 0/4 | 0/4 |
| Three whole placements with literal tile, rotation and square | 1/4 | 1/4 |
| Same three with geometric consequences printed beside them | 0/4 | 4/4 |
| Same three with consequences as the selectable names | 1/4 | 2/4 |
| Same three with the certified trap labeled as an assured Red win | 3/4 | 1/4 |

The smaller menu takes the first legal representative of each of three effects in a deterministic enumeration. The third effect leaves no immediate step with a route in time, while permanent confinement is unproved. The seat chooses a whole placement. The code supplies the geometry. The payoff arm additionally explains the posthumous Red win in one sentence. The effect and payoff arms expose the same literal moves to both teams. We chose these follow-ups after inspecting the full-menu failures. A Red seat may still prefer a delay or a less revealing move. The endpoint here is specifically execution of the guest's decisive tactic. [Full-menu actions](build.csv) · [Three-placement actions](menu.csv)

We then froze the named and payoff menus and tried the two archived three-seat deals 8101 and 8102. Both have an eligible turn for P2 with either alignment in the existing role-swapped runs. Across those two deals and two menu orders, Red made the permanent block **1/4 with geometric names and 3/4 with the Red-win label**. Blue opened a route 2/4 under each and trapped itself once with the Red-win label. These positions were selected for the presence of a real choice. They give no estimate of how often the tactic occurs in a game, nor of a seat's MMR. [Transfer actions](transfer.csv)

## Verifying a public claim

At event 23 of the [original discussion game](../public-discussion/five-colors/8602-red1+3.json), P0 says P2 has stayed three times. P2 has yet to build. P1 stayed once. With the live-sized context, Qwen answered “3” for either builder, including when given the requested builder’s referee history. It never requested the optional lookup on these four questions. An independently prompted fact check with the same log and **only the verification task** got 4/4 with player claims omitted and 2/4 with the claims included. In both answer orders, restoring speech changed P2's count from zero to two. This is an opportunity to compute and present the exact public fact before asking what to say or how to vote. A seat can knowingly bluff after it has checked the floor. [Focused verification](verification.csv)

When instructed which outcome to cast on two live ballots, the ordinary approve/reject interface realized the stated intention on 5/8 checks, the action-specific interface on 8/8. This includes both directions of each ballot and both orderings. The original missed both instructions to keep the nominee in play. These eight choices measure translating an intention into a ballot. Choosing a sound intention during a game is a separate test.

## The same five seats on a shorter floor

Deal 8602, P1 and P3 Red, fixed kit seed 8700 with 29 entrances and 29 exits among the original sixteen tiles, paired fifth hand, and eight build turns. Shortening the displacement from (4,2) to (2,2) changes minimum travel from six steps to four. All comparisons use the assisted outcome policy with public debate. Its decisive automatic choices are part of the evaluated policy. The new brief also reaches speakers. Only the short lookup run offers the extra tool during nominations and removal votes.

| EXIT | Interface | Marker steps | Players removed | Winner |
|---|---|---:|---:|---|
| (4,2) | [Original wording](../public-discussion/five-colors/8602-red1+3.json) | 1 | 3 | Red |
| (4,2) | [Action-specific](long-actions/8602-red1+3.json) | 2 | 0 | Red |
| (2,2) | [Original wording](short-legacy/8602-red1+3.json) | 1 | 3 | Red |
| (2,2) | [Action-specific](short-actions/8602-red1+3.json) | 1 | 0 | Red |
| (2,2) | [Action-specific, social lookup offered](short-lookup/8602-red1+3.json) | 1 | 0 | Red |

The lookup arm recorded zero calls in 35 nomination and 25 removal-vote decisions. A tool offer can also end without a selection if the consultation times out. All five games ended by depletion on turn eight. The shorter offset alone did little on this deal. Keeping all five seats alive was a substantial change in the two matched wording contrasts, but Blue still struggled to build and walk a route. Public discussion diverges after an early changed move, and all five games reuse the same hands, role layout and initial bag. These are traced examples rather than independent estimates of seat skill or balance.

Turn five of the short action-specific game exposes another wording problem. P4 places face 100 at (1,−1) on event 41. On event 42 P4 privately returns a tile. P0 publicly accuses P4 of returning the tile just placed. The placed face is still visible on the floor. The omniscient record identifies the private return as 140. P0 could establish the floor fact from its own seat without knowing the private face. P2 and P4 vote to keep P4 on event 45.

## Language to keep distinct

| Decision or evidence | Player-facing wording |
|---|---|
| Place versus move | The builder places a floor tile. The shared marker stays on its square. A later proposal can target any connected neighbor, including an older tile. |
| Movement versus removal ballot | Name the effects with destinations or seats. For example, “Move marker to (0,1)” / “Keep marker at (0,0)” and “Remove P2” / “Keep P2 in play”. A movement tie follows the builder's own ballot. A removal tie keeps the nominee in play. |
| Stay versus pass | A builder chooses to stay. A nominator passes on an opportunity to name someone. Describe a resolved ballot by what happened, such as “step rejected”. Distinguish a missed proposal or missing vote in the recorded evidence. |
| EXIT versus a tile exit | EXIT is a destination square. “Outgoing side” describes an arrow on a particular floor tile. |
| Return versus remove | The builder returns a remaining hand tile to the bag. The placed tile stays on the floor. A removal ballot concerns a player. |
| Builder, nominator, nominee and speaker | Name who built, who accused whom, and whose ballot or words were revealed. A speaker's statement is evidence of what they said. The public floor log records what was placed and where the marker went. |

The optional live Ollama switch is `--action-brief`. The browser's two ballot controls also name the affected square or player. Existing replay ballots still encode true, false and missing, including a builder voting against their own proposal. These presentation changes use base-1 adjudication and format 1 records.

## Reproduce

Run from the repository root with the local Ollama tag `qwen3.5:9b-q8_0`. Model calls use temperature zero, seed one and thinking disabled. Start with new output paths. A virtual clock controls game progression here. These runs did not measure realtime reliability.

```sh
work=$(mktemp -d)
python -m experiments.action_probe "$work/probe.csv"
python -m experiments.guest_build_probe "$work/build.csv"
python -m experiments.guest_build_menu "$work/menu.csv"
python -m experiments.guest_build_menu "$work/transfer.csv" --transfer --arms named payoff
python -m experiments.verify_accusation "$work/verification.csv"

play() {
  arm=$1
  x=$2
  shift 2
  python -m experiments.social_evidence --start-origin --roles BRBRB --paired-fifth-hand \
    --arm receipt --debate --model-floor --outcome-policy --kit-counts 29 29 \
    --kit-seed 8700 --seeds 8602 --goal "$x" 2 --out "$work/$arm" \
    --private-notes "$work/notes/$arm" "$@"
}
play long-legacy 4
play short-legacy 2
play long-actions 4 --action-brief
play short-actions 2 --action-brief
play short-lookup 2 --action-brief --social-tools
python -m experiments.social_summary "$work"
python -m footsteps view "$work/short-actions/8602-red1+3.json" --omniscient \
  --notes "$work/notes/short-actions/8602-red1+3.jsonl" -o "$work/short-actions.html"
```

The long legacy cell uses the already-published discussion game. The archived records, choices and probes are the observations. Re-running inference may differ across Ollama versions or hardware. For a skill comparison that can distinguish a stronger seat from an easier deal, see the [matched seat-substitution design](../../docs/ratings.md).
