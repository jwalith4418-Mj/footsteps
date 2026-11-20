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
python -m experiments.goal_probes ballots "$out/ballots.jsonl" --arm brief
python -m experiments.goal_pursuit "$out/games" "$out/private" --cases four --arms brief --seeds 9501
python -m experiments.goal_pursuit "$out/games" "$out/private" --cases five --arms brief baseline --seeds 9901
python -m experiments.goal_audit "$out"
```
