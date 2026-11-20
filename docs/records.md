# Recording a game

The full JSON has a numeric `format` (currently 3), a `rules` identifier (`base-1`), a realized `setup`, and an ordered `events` array. Seat indices start at zero. Setup contains the goal coordinate, roles and starting hands in seat order, and the bag as an array of face numbers with multiplicity. Seat 0 builds first. Face IDs preserve true orientation. The referee rotates a face only when applying the placement.

Format 3 stores team IDs as `"blue"` and `"red"` and requires an explicit START. For example, `"start":[-4,-2],"goal":[0,0]` gives the paper layout. The importer upgrades format 1 with START at (0, 0) and format 2 with its recorded START. It maps historical role IDs once on import. Exports use format 3. Events, coordinates, table IDs, remarks and private sidecar associations survive the upgrade. The base-1 rules are unchanged.

An optional top-level `placement_check` records the builder interface used at a live table (`edge` or `edge-and-marker`). The replay uses the committed tile, square, and rotation. Builder answers and rejected attempts stay private.

| Phase / kind | Required fields | Interpretation |
|---|---|---|
| draw | tiles | Realized faces in draw order, with multiplicity |
| place | tile, at, rotation | True face, [x,y], 0–3 clockwise quarter turns |
| discard | tile | Returned face |
| propose | to | Coordinate or null to stay |
| move_vote | votes | Boolean or null per living seat, in ascending seat order |
| nominate | target | Seat index or null to pass |
| eliminate_vote | votes | Same ballot representation as movement |

For place, discard, propose and nominate, optional `timeout: true` marks the realized fallback. A null ballot means a public timeout counted as no. Every event is applied to the previous legal state. Turn, actor, nominator, eligibility, movement and outcome are derived. A valid prefix is a resumable position. An event after game end or an unsupported version is an error.

The referee retains the realized setup, every draw and every random fallback. Replaying never calls a PRNG. Seeded policy experiments additionally record their input parameters and seed so a developer can rerun the policy itself. The seed and full record expose secrets. The public account hides hands and drawn or discarded faces. It reveals roles only after game end. A seat account adds its own role, known teammates, starting hand and private events. The referee's `Game.view(seat)` supplies the corresponding current snapshot. To supply an agent, derive its view in the referee process.

The full Markdown export ends in a labeled JSON block. Import replays that block and regenerates the prose. A redacted account can be shared with players. It deliberately lacks the information required for replay. Editing free-form prose does not edit an event. To change a worked example, edit the embedded record or canonical JSON, then render again.

```sh
python -m footsteps replay examples/crossing.json --full > /tmp/crossing.full.md
python -m footsteps replay /tmp/crossing.full.md --seat 1
```

Change the rules ID when a legal history would acquire different semantics. Change the format version when its encoded fields or meanings change. Keep versioned examples and regression tests when adding readers.
