# Distance-six solitaire pilot

**Question.** How much can intent, a larger hand, or four extra turns change the odds of reaching an exit six squares away? Can a player salvage a weak opening by reasoning about outgoing edges only near the exit?

Eight configurations cross exit (6, 0) or (4, 2), hand size 2 or 4, and 6 or 10 tiles in the bag after dealing. Each configuration uses seeds 0–199, with five players tried independently on every setup (8,000 games). Each incoming and outgoing bit is independently present with probability 0.55. This provisional mix favors connected faces slightly, keeps all 256 true faces possible, and imposes no guarantee of an entrance or onward exit.

| Player | Placement, movement and discard |
|---|---|
| random | Uniform legal square, distinct hand face and rotation. Uniform choice among stay and legal moves. Uniform distinct discard face. |
| greedy | Prefer a traversable placement next to the marker that minimizes distance to the exit. Move or stay to minimize distance. Discard the face with fewest set bits. |
| exits | Same local candidates. Prefer tiles with at least one usable onward edge, then closeness, then an exit that gets closer. Movement scores destinations the same way, with first priority to entering the goal. An edge into an empty square counts as an opportunity. |
| switch | Use greedy until the first turn starting within distance two. Switch permanently to exits for that suffix. The paired greedy run has the same setup, decisions and RNG state up to the switch. |
| route | Search the directed portion of the built floor reachable from the marker. Try a hand tile at an accessible frontier, ranking onward exits, estimated travel (built steps plus remaining distance), then exit direction. Walk along a shortest built path to the goal if possible, otherwise toward a frontier with the smallest estimated total distance. Can backtrack and build away from the marker. |

All intentional players discard as greedy does. When intentional placement has no usable candidate, it falls back to the random placement rule. Ties are sampled. Setup, bag draws and policy choices have separate random streams. Paired starts give policies identical private deals. Later discards may change the bag, so two policies that diverge can draw different faces. The same seed across configurations does not hold the entire future constant.

## Results

With ten turns available, exits won 789 of 800 games, all in six turns. Greedy won 62, also all in six. Route won 792, including 258 that finished in seven to ten turns. The fraction finishing on the last turn was 4/800 for route. In the six-turn diagonal configuration with a two-tile hand, exits won 189/200 while route won 59/200. An explicit search can spend movement on approaches that the tight budget cannot afford. Inspecting more board positions alone does not establish policy strength.

Of 1,600 greedy openings, 441 reached a turn starting within two squares of the exit. Switching there converted 116 of those positions from losses to wins. No win changed into a loss in this sample. Most openings never qualified for this intervention. That denominator matters if the question is whether to improve the opening or the finish.

These results support trying both tight and loose budgets with a cooperative table. The concentration of finish times depends on how the player chooses its route. Private hands, changing builders, distrust and vetoed moves are absent here. The sample also reuses seeds across configurations, so the pooled counts are descriptive. A failed policy is a lower bound on what a stronger player could achieve on these deals.

The generated tables include every configuration and the finish-time distribution. A certified trap means the entire directed component reachable from the final marker excludes the goal and has no outgoing edge into unbuilt space. That is a sufficient certificate of permanent immobility or confinement even with an unlimited future bag. Other losses include time exhaustion on a potentially recoverable board and traps this certificate misses. [Counts](counts.md) · [Per-game CSV](pilot.csv)

## Reproduce

Run from the repository root. The pilot used CPython 3.14 and the shell pins a CPython 3.13 toolchain. Each CSV row includes the policy, setup parameters, seed, winner indicator, finish turn, remaining store, final distance, trap flag, and first turn within the switch radius (blank if never reached).

```sh
python -m experiments.run --seeds 200 --out /tmp/pilot.csv
cmp /tmp/pilot.csv experiments/pilot.csv
python -m experiments.summary /tmp/pilot.csv
python -m footsteps solo --policy route --seed 59 --goal 6 0 --hand 2 --store 10 --save /tmp/59.json
```

The last command reconstructs an eight-turn win on a straight-line goal. To test a mechanic change, hold the seed panel fixed during development, then repeat the selected comparison on fresh seeds. Preserve full records of representative failures when investigating a policy.

For multiplayer trials with model seats, see the [matched self-play games, mixed lineups and timing measurements](model-panel/README.md).

The [ballot experiment](ballots/README.md) tests order sensitivity on frozen votes and compares model voters with scripted voters on matched live deals.

The [single-model solitaire benchmark](model-solitaire/README.md) uses the same private deals for local Qwen models and four scripted policies, plus reflected detours and rotated-replay checks.

The [turn-plan comparison](solitaire-skills/README.md) traces a movement failure through frozen tactics to unseen deals, with uniform and shortest-path controls on the same menus.

The [three-seat social experiment](social/README.md) pairs the same elimination ballot with silence, a truthful accusation, or a false one, then compares scripted and model-controlled floors.

The [social behavior trials](social-behavior/README.md) test whether a seat can earn trust on an inconsequential vote, use the opportunity to act, and recognize when its team can win after its own removal.

The [common-knowledge check](known-roles/README.md) tests what Blue and Red players can infer about another seat and whether the distinction survives an elimination.

The [tile-density comparison](tile-density/README.md) tests uniform supplies of exactly 29 entrances and exits against 35 of each, the printed totals, and the older per-side probability generator.

The [minority-team games](minority/README.md) compare a lone obstructing player with a pair of obstructing players on a five-seat floor, and the color names with the earlier vocabulary. They include the exact printed-kit listener position and a cooperative continuation after the lone Red is eliminated.

The [public discussion comparison](public-discussion/README.md) follows a checkable accusation through three speakers after both teams were explicitly told they could bluff.

In the [blinded guest-seat trial](blind-guest/README.md), an independent agent called a trap before voting to enter it, then used a true public correction to deflect suspicion after closing the floor.

The [guest tactic and ballot comparison](action-language/README.md) tests whether local model seats can see a permanent block coming, execute it, and check an accusation against the public floor history.

The [EXIT-origin comparison](exit-origin/README.md) tests distance reading, directed detours, matched solitaire deals and a five-seat table in two coordinate systems.

The [placement check](placement-check/README.md) asks builders to classify a directed edge and, optionally, locate the marker before committing. Frozen positions and matched five-seat tables measure what players can read and what they then build.

The [rotation comparison](rotation/README.md) pairs printed-only and freely rotated games, then compares automatic orientation tables with observed private tool calls on matched model decisions.

The [native action comparison](native-actions/README.md) follows each private rotation and preview through to the committed placement. It pairs literal native calls, a rotatable hand and indexed menus on the same tactical floors and complete social deals.

The [goal-pursuit gate](goal-pursuit/README.md) tests model-authored first landings, corrections to individual plans, and outcome-assisted decisions on held-out solitaire deals before applying the frozen setup to multiplayer play.

The [removal ballot perspective experiment](voter-perspective/README.md) checks whether a voter recognizes itself and distinguishes other players' claims from their recorded ballots.

The [pivotal removal ballots](pivotal-votes/README.md) measure whether the same voter changes its actual choice when a private roster or two public final-turn policies are exchanged, then revisit the five-seat game with a stronger local model.
