# What can a model seat ask?

A seat has one authenticated snapshot per decision. Its legal menu, current hand, its own role and allies when applicable, and public history are the inputs available to an assistant. The referee remains responsible for accepting an action and ending the game. The design below covers solitaire first and extends to the two kinds of social ballot.

## Available now

| Interface | Question and result | Availability |
|---|---|---|
| Legal menu and seat history | Which actions can I submit now? What did I observe? The live adapter includes the current menu, visible board and hand, and twelve recent entries. | Every live model decision |
| Preview a placement | Given literal hand face, rotation, x and y, validate the combination, then return the oriented face, enterable destinations and whether this build seals the current marker. | Callable as `preview_placement` on a live placement |
| Inspect rotations | Give the literal number of a face in your hand. Read its entrance and exit compass sides at each of the four clockwise quarter turns. | Callable as `inspect_rotations` on a live placement with `--rotation-aid tool` |
| Compare landings | For each legal destination or stay, report distance, EXIT arrival, permanent confinement, and the optimistic route length with fully open future tiles. On a movement ballot compare approval and rejection from the pending move. The search covers the smaller of 16 steps and the actual remaining moves. A null length means no route within that horizon. | Callable as `compare_landings` on a live proposal or movement ballot |
| Check a builder’s turns | Enter a seat number to retrieve its completed turn count and latest four floor results. Each lists the tile square, requested step, actual marker squares and result. This distinguishes a deliberate stay, a missed proposal and a rejected step. | Callable as `check_builder_turns` on nominations and removal ballots |
| Compare complete plans | Enumerate builds with subsequent legal walks and group their immediate prospects. The selector picks one plan. The referee executes the stages separately. The local variant shows only immediate outward edges. | Precomputed experiment menus in `experiments.turn_plans` |
| Private decision note | Optionally generate one sentence identifying an observation behind a specific attempted action. Attach chosen notes at their event during an omniscient export. | Live Ollama seat and experimental model plan selector |

A placement preview also checks the original floor for a held tile and rotation that close the marker’s only unbuilt outgoing side and leave no immediate step. Comparing landings performs the same check if this seat gets the next build assuming everyone survives. A missing witness leaves other ways to obstruct play open. These calculations use the caller’s hand and the visible floor.

The live `--tools` switch offers the relevant function through Ollama's native tool-call interface. A preliminary request can select one read-only query. The final request receives its result and the ordinary structured action schema. The preliminary request gets at most half the available budget. Both requests share the original deadline. The host still checks its own clock. Unsupported or missing tool selection falls through to the action request. An illegal tool argument gives an error result and leaves all legal actions available. [Ollama tool-call protocol](https://docs.ollama.com/capabilities/tool-calling)

The 7/8 prospective result used precomputed complete plans with path lengths. The live callable subset has a separate smoke test. Supplying a report to every decision and letting a model decide whether to request it are different experiments. [Assisted performance](../experiments/solitaire-skills/README.md) · [Pathfinder ablation](../experiments/local-plans/README.md)

A builder can also use `--rotation-aid table` to see all four orientations of every distinct held face on each placement. The client sends fresh context per decision, including faces it has seen before. With `--rotation-aid tool` it offers a private lookup on one held face. Add `--tools` to offer the placement preview alongside it. Only one call can be made. Add `--named-rotations` to submit literal turn names in either mode. The referee still receives ordinary clockwise quarter turns. With `--private-notes`, the receipt on a completed decision records the requested face and outcome. The omniscient viewer shows it beside the choice. Explicit skips (`{}`), truncated replies, other replies without a call, invalid requests and unavailable lookups have distinct statuses. [Rotation experiment](../experiments/rotation/README.md)

## Further tools worth evaluating

| Decision need | Proposed input → output | First test |
|---|---|---|
| Learn an edge or timing rule | Rule name and stage → short adjudication plus one legal example; show remaining movement opportunities including the pending one. | Tight detour and final two-draw/discard cases |
| Inspect a placed tile | Occupied coordinate → oriented compass ports, legal connections and why a specified neighboring step fails. | Require facing entrance and exit on both sides across rotations |
| Find candidate builds and repairs | Marker or target plus a result limit → candidate moves, current frontier, reachable built floor and each proposed repair's assumptions. Return alternatives that require backtracking. | Frozen boards where walking closer loses and a remote build helps |
| Compare whole turns on demand | A tool request for one destination or several plans → legal placement and proposal pairs, grouping rule, optimistic bounds, and retained alternatives. | Matched tool-on/tool-off and same-menu scripted controls; record selection overhead |
| Compare discards or sample a continuation | Own hand, visible discard information, declared tile prior, simulation budget and analysis seed → distribution over explicitly hypothetical draws and resulting positions. | Compare against the bit-count discard on unseen deals; never sample the actual hidden bag |
| Retrieve private memory and public evidence | Event range, seat or nomination → bounded snippets of what this seat actually observed, including absences, timeouts and revealed votes. | Can two seats recover their own prior actions while another seat's private discard stays hidden? |
| Evaluate a ballot | Pending proposal and public voting rule → possible outcomes for the seat's vote under specified hypothetical other votes. Use proposer tie-breaks or strict majority as appropriate. | Tied movement votes, self-vetoes, strict-majority failures and eliminated seats |
| Participate in discussion | Public evidence references and the seat's chosen claim → one explicitly public remark during a speaking window. | Does another seat change its decision when the same board is paired with different public statements? |
| Inspect an experiment after play | Record, perspective and authorized note attachments → replay frame, legal alternatives, selected action, tool timing and missing replies. | Compare forced stays with elective stays, distinguish a pre-placement lockout from moving into a trap |

Keep read-only tool calls separate from submitting an action or saying something publicly. Tool requests use the same seat perspective as prompts. An eliminated seat's private record remains private. A host can analyze omniscient information after the game; giving that information to a player would invalidate a trial.

For each new tool, freeze the decision prefixes first. Compare models with the same visible state and legal choices, counterbalance menu order and include an unassisted or same-menu scripted control. Measure how often the model asks, invalid queries, tokens, wall time and missed decisions, followed by fresh-deal outcomes if the frozen test improves. When notes are enabled, report that as a separate prompting condition. A model's explanation can be checked against its action and the board and can itself be mistaken.

The native action client also lets a builder commit directly through Ollama, optionally after several private preparations. Use `--action-tools hand` for per-copy orientation or `--action-tools direct` for a single placement carrying an explicit turn. Add `--all-decisions` to use native calls during returns, movement, nominations and ballots. The native preview uses a held handle and its receipt reports legal steps from the marker. The decision deadline includes preparation and commitment. [Live protocol](table.md#native-action-calls-and-private-hand-pieces) · [Matched comparisons](../experiments/native-actions/README.md)

## Persistent seat tool conventions

The persistent player receives one function schema for each action available to its seat. Coordinates in state, placement previews and movement updates use named integer `x` and `y` fields. A position returned by `get_state()` can supply those same two arguments to a placement or proposal. Checked placements name a second square with `origin_x` and `origin_y`. A held `piece` is a seat-local handle such as `H1`; multiple handles may have the same printed face.

| Tools | How the values fit together |
|---|---|
| `get_state()`, `get_role()` | Read authoritative facts for this seat. Held pieces show their printed face, current rotation, entrances and exits. Board tiles show the face after rotation. State supplies build squares, possible steps or nomination targets when the seat can use them. |
| `inspect_rotations_at`, `orient_tile`, `preview_placement`, `place_tile` | Inspection compares one held piece at one candidate square. Its rows use the same `rotation` value accepted by `orient_tile`. Only orienting changes the copy in hand. Both preview and placement take that handle and square; placement commits its current rotation. The marker stays on its original square throughout. |
| `return_tile` | Return the named held copy to the store. Its handle leaves this seat's hand. |
| `propose_step`, `stay`, `vote_move` | A step takes one destination. Stay takes no arguments. On a step proposal, `approve: true` votes to land on that square and `false` votes to stay. |
| `nominate`, `pass_nomination`, `vote_removal` | Nominate takes another living seat's integer ID. Pass takes no arguments. The removal ballot identifies the nominee; `approve: true` votes to remove that player. Ballots remain private until the group reveal. |
| `speak`, `history` | Speech is public and attributed. History pages distinguish a speaker's claim from a revealed ballot. Use `{"kind":"move_vote","turn":1,"voter":0}` to check P0's first-turn movement ballot when a later vote is also visible. A revealed null ballot denotes a missed vote. |
| `compact`, `wait` | Compact takes short player-authored notes. Wait normally takes no arguments and starts at the visible update the player just saw. An intervening remark wakes it immediately. An optional `after_cursor` names an earlier visible-state update. History pagination uses entry IDs instead. |

Accepted decisions identify the action and the revision at which it committed. The nested `current` field describes the seat's resulting opportunity. Reads and hand preparations return their own results. Rejections return an explanation and the current opportunity, subject to the original referee deadline.

When extending an action, check that a value returned by one tool can be used in the next, that the description matches the actual parameter schema in every supported mode, and that the receipt distinguishes a private preparation from a committed event. Exercise a rejected argument and a stale revision as well as the successful sequence. [Local transport and runner](table.md#persistent-ollama-seat)
