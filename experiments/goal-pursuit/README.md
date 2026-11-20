# From EXIT to a first action

## Trial design

Start with the two archived corridors, then reflect to west and south. Compare a seat-authored placement with a compact clock and coordinate worksheet against assistance that calculates consequences for candidate builds. Both interfaces keep literal legal placements available. The consequence report preserves the best route from every legal landing after the candidate build, including staying. Construction, movement proposals and ballots are separate model decisions.

Before social play, require wins on at least three of the four two-turn headings including both new headings, a viable away-first detour on at least six of eight presentations (four reflections in both orders), and wins on at least four of six ordinary new solitaire deals. Use seeds 9801–9806, a two-tile hand, seven movement opportunities, displacement (3,2), and independent per-port probability 0.55. Test the same deals with an unaided builder and a uniform selector over the displayed outcome groups. Keep development results separate if the setup needs revision. Measure timeouts apart from choices.

Upon passing, freeze the setup. Reuse the four 9600-series role-swapped positions and four new qualifying floors beginning at 9700. Score Red for a permanent seal and Blue for a legal step with a route still in time. Count both roles right on the same floor. Compare complete social tables on archived deal 9501 and a fresh deal with two Reds among five seats. Keep the seat, role, ballots, remarks and draw process intact. Inspect reversals, eliminations, attributions and fallback events before drawing conclusions from a team win.

## Pilot and freeze

The initial 8,192-token request alternated with 4,096-token requests from other stages. The Ollama service started the same model blob ten times at each context size over a ten-minute window. We stopped the three pilot processes and kept their partial logs under `pilot/`. The original candidate preserved the away-first detour in 3/8 presentations. We added one plain-language sentence per candidate explaining the best remaining route for Blue or why every landing lost it. The initial five completed presentations succeeded. We froze that wording, used 4,096 tokens throughout, and moved the ordinary-deal gate to untouched seeds 9811–9816. Pilot timing and interrupted games are excluded from the comparison.

## What the player received

All runs use local Ollama `qwen3.5:9b-q8_0`, temperature zero, inference seed 1, and 30 seconds per decision. The table and action fallbacks are the same ones used for live play. Ballots have independent per-seat inference budgets on a virtual table clock. Equal setup seeds hold the initial hands and draw stream fixed. Later returns and timeouts can change which faces are available to draw.

- **Baseline** uses the previous native private-hand builder and structured model decisions at other stages.
- **Ledger** supplies the actual marker, EXIT, current and remaining proposals, and distance and budget for each neighboring landing. It includes the compass ports of every private face in all four orientations. The model names its own literal action.
- **Repair probe** separately asks for a build, landing and remaining clock. It shows the model the legal landings and optimistic consequences of that single build, then accepts a revised legal placement. Only the placements were submitted. We scored the model's proposed landing on the resulting board.
- **Forecast** enumerates legal builds from the acting seat's hand and visible board. For each, it lists all possible landings, including staying, their optimistic distance to EXIT within the remaining clock, and permanent confinement. The public directed search treats future unbuilt tiles as fully open. An existing directed wall stays a wall. A possible route still depends on tiles and votes. For display, identical landing/length/confinement lists share one representative build. These builds can leave different private hands and future layouts. The model can also specify any literal legal build via `custom`. Group order is seeded and shuffled.
- **Brief** adds one sentence giving the best possible landing or stating that every landing is lost. The same facts go to either team. The prompt asks Blue to keep the shortest available route and explains why a build that seals every landing could suit Red. Proposals and movement ballots are newly evaluated on the actual board. The player makes a separate choice at each stage and can contradict its earlier placement. This is assisted play.
- **Uniform** samples the same displayed groups for placement, proposals and movement ballots. All three ordinary-deal arms use the same model client for returns. On social tables, the model still chooses nominations and removal votes and can make a separate public case for a nominee. Nobody is scripted to agree with another seat.

## Reproduce

Run `python -m experiments.goal_audit` to replay the archived games, validate the seat decisions and public fallbacks, and count decisions with omitted earlier speech. To regenerate the model observations at the standard context size, use new output paths. The pilot used the larger context before the change documented above.

```sh
out=$(mktemp -d)
mkdir -p "$out/games" "$out/private"
python -m experiments.goal_repair "$out/repair.jsonl"
python -m experiments.goal_probes detours "$out/detours-brief.jsonl" --arm brief
python -m experiments.goal_pursuit "$out/games" "$out/private" --cases east north west south --arms brief forecast ledger
python -m experiments.goal_pursuit "$out/games" "$out/private" --cases solo --arms brief uniform baseline --seeds 9811 9812 9813 9814 9815 9816
python -m experiments.goal_probes social "$out/social.jsonl" --arm brief
python -m experiments.goal_probes social "$out/social-room.jsonl" --arm brief --max-reply 320
python -m experiments.goal_probes social "$out/social-card.jsonl" --arm personal
python -m experiments.goal_probes social "$out/social-last.jsonl" --arm last --max-reply 320
python -m experiments.goal_probes ballots "$out/ballots.jsonl" --arm brief
python -m experiments.goal_pursuit "$out/games" "$out/private" --cases four --arms brief --seeds 9501
python -m experiments.goal_pursuit "$out/games" "$out/private" --cases five --arms brief baseline --seeds 9901
python -m experiments.goal_pursuit "$out/games" "$out/private" --cases five --arms last --max-reply 320 --seeds 9901
python -m experiments.goal_audit "$out"
```

## What survived the solitaire checks

The clock and rotation worksheet alone won **1/4** corridor games. Its only win was south, where the printed straight already points toward EXIT. Forecast and brief each won **4/4**, including the two held-out headings. One mandatory build in the east forecast game fell back after the reply limit, so its table win includes a random placement. The brief arm needed no fallback on the headings. On the four detour reflections in both orders, the brief arm produced **8/8** time-viable build and proposal pairs, including the step that initially increases Manhattan distance.

The self-authored probe named the correct remaining clock in all eight first answers, but none of the eight original build/landing combinations could finish in time. After one private check, six placements were legal and two plans were viable. One was the printed southbound corridor. This distinguishes reading the arithmetic, picking a location and preserving a directed route. The system that passed the gate enumerates outcomes and gives a time bound to the model. Its wins cannot be attributed to unaided planning.

## What the 12-entry history can omit

The client supplies its own message list to Ollama at every decision. The floor, current marker, EXIT and private role are reconstructed from the seat view. Individual history entries and statements older than the last twelve can drop out. Model notes from previous decisions are not included. A cached prompt prefix helps evaluate requests that share text. It cannot supply an old observation that the client left out of the new request.

In one measured interval of the 4k run, all 121 completed runner requests reported zero input truncation and the largest sequence was 1,675 tokens. One sampled structured forecast hit its separate 140-token reply cap. On the archived 9501 all-native social table, 23/28 nomination decisions omitted at least one earlier public remark. The first lost remark was P1’s opening case for removing P0. The experiments preserve the existing history projection. [Matched 4k/8k and history follow-up](https://github.com/othercriteria/footsteps/issues/91) · [Ollama chat request and response fields](https://docs.ollama.com/api/chat)


## Social transfer

The frozen brief scored on **8/8 Blue** placements across four earlier role-swap floors and four new ones. **Red scored 0/8**, even though every affected hand contained a permanent seal. Four Red replies missed the separate output allowance. We compared three follow-ups on the same paired floors. The model always received its assigned role. The personal condition repeats that role and its objective at the very start of the system message. The final condition changes only the order of the two generated JSON fields relative to the longer-reply control.

| Presentation | Reply cap | Blue witnesses | Red seals | Timely Red commitments | Floors correct for both roles |
|---|---:|---:|---:|---:|---:|
| Frozen brief, choice then reason | 140 | 8/8 | 0/8 | 4/8 | 0/8 |
| Same brief with more reply room | 320 | 8/8 | 0/8 | 7/8 | 0/8 |
| Personal role at head of brief | 140 | 8/8 | 2/8 | 5/8 | 2/8 |
| Same 320-token brief, reason then choice | 320 | 8/8 | 4/8 | 7/8 | 4/8 |

The last condition recovered two Red seals on each four-floor panel. In the longer choice-first control on 9600, Red submitted the same productive build as Blue, then its private note identified the candidates that sealed EXIT. Changing field order let it choose one of those seals. These are small paired interventions on a single model. Seat-private notes are accounts of a choice and can be wrong. The group labels P1, P2 and so on also overlap with player names in public history. Some notes speak about candidates as if they were proposers, a reason to try distinct action labels in later trials. [Role-swapped decisions](social.jsonl) · [Longer reply](social-room.jsonl) · [Personal role](social-card.jsonl) · [Reason first](social-last.jsonl)

### A backward step with a defensible Yes vote

We replayed three real ballot positions from the all-native 9501 game to the same four seats. At event 5, a step east reduces Manhattan distance but leaves an optimistic route of five further steps, versus four after staying. All three Blue seats approved again. Red missed the reply cap. At event 16, going back to START leaves a six-step optimistic route and staying leaves no route in time. The historical Blue Yes and Red No each served their respective teams on that floor, despite the private claim that START was closer to EXIT. With the brief, **all four** approved the return, including Red. By event 26 both outcomes are out of time and all four seats approved. A substantive spatial error in a note and a strategically defensible ballot can coexist. [Ballot receipts](ballots.jsonl) · [Original issue and correction](https://github.com/othercriteria/footsteps/issues/55#issuecomment-7051619999)
