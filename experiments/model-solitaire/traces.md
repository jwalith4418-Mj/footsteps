# Where did play first stall?

On the eight held-out Qwen2.5 32B deals, the geometry report moved the bottleneck from placement to movement. For a placement opportunity, we require a legal hand face and rotation on a closer square that can be entered immediately and whose destination component is unsealed. An unsealed component can still be too slow to finish, and an intentional detour can be better than moving closer. At proposal time a forced stay means there was no legal destination. We can distinguish these conditions from the recorded board and the acting seat's hand without inferring motives or querying a model.

| Eight matched deals | Qualifying build used / offered | Forced stays | Elective stays | Elective stays with an unsealed closer move | Placements that sealed the marker |
|---|---:|---:|---:|---:|---:|
| 32B literal JSON | 14/48 | 37 | 16 | 4 | 0 |
| 32B with edges | 25/26 | 0 | 60 | 46 | 0 |
| 9B with edges | 26/35 | 18 | 19 | 5 | 3 |

For 32B with edges, 46/60 elective stays passed up local progress. For 9B, its three certified trapped finishes all began with a placement. Counting proposals to enter a dead end would miss every one. The decision denominators changed as the games diverged. Referee-selected fallbacks are counted separately.

* **Rules presentation.** Say how many movement opportunities remain, including the pending one. A stay spends one. Explain a tight detour with a worked four-move finish.
* **Action presentation.** Show the tile's orientation after the proposed rotation and the effect on the marker's existing exits. On 9B deal 4006, event 21, face 86 at (2,2) rotation 0 sealed the marker's component. Rotation 1 at the same square with the same face supplied an enterable, unsealed closer tile. [Game record](9b-test-edges/game-4006.json)
* **Prompting.** Separate movement instructions from placement instructions. Use the actual stalled positions and the short-clock detour before paying for another full game. [Prospective experiment](https://github.com/othercriteria/footsteps/issues/45)
* **Observability.** Keep the action menu, a concrete legal alternative, prompt version and whether an action was selected or forced. On 32B development deal 100, event 2, the hand offered 20 qualifying builds. The chosen face east of START had no west entrance. The resulting stay at event 4 was compulsory. Running a movement prompt against event 4 would teach us nothing about willingness to move. [Game record](dev/game-100.json)

The aggregate and event modes below reconstruct the choice set before applying each event. Placement options count face/rotation/square triples, including legal rotations that yield the same connectivity. On a movement row the option count excludes stay. A reported alternative is the first qualifying witness in enumeration order. It has no claim to optimality.

```sh
python -m experiments.solo_trace experiments/model-solitaire/{test,test-edges,9b-test-edges}
python -m experiments.solo_trace --events experiments/model-solitaire/9b-test-edges/game-4006.json
```
