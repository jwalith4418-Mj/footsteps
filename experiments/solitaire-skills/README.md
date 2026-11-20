# From a stalled decision to a solitaire policy

The [previous traces](../model-solitaire/traces.md) distinguish an inability to move from a choice to stay. We tested changes first on frozen decisions, then on complete games. The public goal, tile distribution, hand size, post-deal store and draw stream match the single-model benchmark. Each role here is a sole good player. [Movement protocol](https://github.com/othercriteria/footsteps/issues/45) · [Complete-plan protocol](https://github.com/othercriteria/footsteps/issues/46)

## Movement

The recorded panel contains the first elective stay with a closer unsealed move on each of the first four qualifying 32B edge-aided evaluation games. We tested the 9B model on those same seat views. Approaching EXIT on a doomed last turn is still credited on this *local* metric. The tactical panel uses four reflections of a tight detour with exactly one winning first step. We presented every menu in ordinary and fully reversed order, including the position of stay.

| Qwen3.5 9B Q8 movement prompt | Closer unsealed step on recorded cases | Winning detour on tight cases |
|---|---:|---:|
| Original geometry report | 8/8 | 4/8 |
| Movement card with edge, distance and trap flags | 8/8 | 0/8 |
| Movement card with optimistic path length | 7/8 | 8/8 |

The last card uses a public search. It preserves the orientation and both directed connection requirements of every existing tile and treats each unbuilt square as fully open. If this optimistic floor cannot connect a proposed landing to EXIT before the last move, no sequence of future base-rule placements can do so. A route within the bound still needs suitable draws and placements. The model sees a statement of each action's prospects, then returns an action name. The tool does not remove a losing choice. [Original and movement-only replies](probe.csv) · [Bound-aided replies](bound.csv)

The bound-aided movement policy won two of four development games. It lost all eight new deals 5001–5008 despite passing the tactical gate. The previous placement and discard prompts still controlled its builds and hand. Scripted movement controls used the same model for those decisions and the same set of legal destinations. Uniform sampled every destination including stay. Shortest chose the lowest optimistic length and sampled between ties, using Manhattan distance when every destination was outside the horizon. Each later decision used the board that arm had produced. The uniform and shortest movement controls also won 0/8. Three of the model arm’s final positions, five of the uniform arm’s and four of the shortest arm’s were certified sealed. Changing voters or movement alone cannot repair those builds.

## Complete turn plans

A model can instead choose a placement and its intended movement together at the beginning of the turn. The generator tries every legal combination of square, true hand face and rotation, then every legal move or stay on the resulting board. It groups plans by destination, remaining optimistic route length and permanent confinement. One deterministic representative per group enters the menu. Grouped plans can leave different hands or floor layouts, so the reduction can discard a better long-term choice. All losing classes remain in the menu. Menu order is seeded and shuffled. Each plan log preserves the complete offered menu and the selected index.

The model picks one named plan. The referee applies its placement and proposal at the normal stages. A scripted discard returns the remaining face with fewest set bits, breaking ties by face number. The number of moves available after the current turn includes the coming discard when the builder drew two. Only the public draw count and the acting seat's view reach the generator. Uniform and shortest use the identical plan generator, discard and chance mechanism. The shortest control also breaks ties by landing distance and then a seeded draw. Neither scripted plan selector calls Ollama.

The complete-turn tactic starts before the mandatory placement, with an all-closed hand. The straight step enters a dead end. One perpendicular step can reach EXIT in exactly four moves, provided the mandatory placement leaves that route open. Staying or building on the required detour can lose immediately. Reflections and reversed shuffled menus test preference for the action separately from preference for a slot.

## Reproduce

The model arms used local Ollama with temperature zero, seed 1, 8192 context tokens and direct structured answers. Use empty output directories. The scripted plan arms run offline.

```sh
python -m experiments.skill_probe
python -m experiments.skill_probe --policy bound
python -m experiments.skill_games --policy model --seeds 5001 5002 5003 5004 5005 5006 5007 5008 --out /tmp/footsteps-movement-repeat
python -m experiments.plan_tactics
python -m experiments.turn_plans --policy model --seeds 100 101 102 103 --out /tmp/footsteps-plans
python -m experiments.model_solitaire_audit experiments/solitaire-skills/*/
```
