# What happens when the pathfinder is removed?

The [previous plan selector](../solitaire-skills/README.md) saw a shortest possible route length and whether each proposed turn could still win. Here the generator groups legal plans by destination and immediately usable outward edges of the landing. The model sees the literal build, move, distance and connected edges, including unbuilt neighbors. The generator and player perform no path search. The evaluator checks the tight fixture after selection. A regression test disables both path search and the sealed-component checker while generating local menus.

| Qwen3.5 9B Q8 and controls | Development wins, seeds 100–103 | Final distances in order |
|---|---:|---|
| Model using local edges | 1/4 | 0, 2, 3, 2 |
| Uniform local plan | 0/4 | 5, 8, 6, 4 |
| Scripted immediate-exit score | 4/4 | 0, 0, 0, 0 |

Each reflected tactical menu contained six plan representatives, one of which made the winning four-move detour. The model stayed on all eight presentations, including the reversed menus. The earlier pathfinder menus contained four representatives, one of which won. The experiment changes both grouping and displayed information, so it cannot attribute the difference to either alone. The scripted selector prioritizes entering EXIT, a landing with an outward edge, lower current distance and then lower next-step distance. It uses the same menu as the model.

The local model missed both advancement criteria. We kept seeds 7001–7008 unused. The model's 7/8 performance on the earlier prospective panel applies to the assisted interface. The cheaper local facts still suffice for a scripted player on these four development deals. [Tactical choices](tactics.csv) · [Worked local-model win](dev-model/game-100.json) · [Protocol](https://github.com/othercriteria/footsteps/issues/47)

```sh
python -m experiments.plan_tactics --local
python -m experiments.turn_plans --local --policy model --seeds 100 101 102 103 --out /tmp/footsteps-local-model
python -m experiments.turn_plans --local --policy exits --seeds 100 101 102 103 --out /tmp/footsteps-local-exits
python -m experiments.turn_plans --local --policy uniform --seeds 100 101 102 103 --out /tmp/footsteps-local-uniform
python -m experiments.plan_audit --local experiments/local-plans/dev-*
python -m experiments.model_solitaire_audit experiments/local-plans/dev-*
```
