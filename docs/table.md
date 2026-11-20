# One localhost table

Start a host with `python -m footsteps table --save /tmp/game.json`. The default game shuffles the sixteen printed tiles and three good roles plus one bad role. Use `--seats 3` to deal two tiles to each of two good players and one bad player, leaving ten in the bag. For a rules walkthrough, `--crossing` uses the known seating, deal and first draw from the worked example. Players make all subsequent choices.

Use `--color-teams` to call the exit team Blue and the obstructing team Red in browser seats, model briefs and replay.

To try a different sixteen-tile supply, add `--kit-counts 29 29 --kit-seed 8700`. The first number sets the total entrances and the second sets total exits, each from 0 to 64. Each set is drawn uniformly over the 64 tile sides. A side can have both permissions or neither. The seed reproduces faces across tables. Each host independently shuffles the deal and roles, and the saved record contains the actual setup.

The server binds to 127.0.0.1 and prints a separate browser link for each seat. Give each participant only their own link. A local group can use separate browser tabs or profiles, arranged so players can read their own screen privately. Remote devices would need an independently configured loopback tunnel. The host terminal and the on-disk record contain referee secrets. Reopening a link reconnects to the same seat while that host process is running.

## Decisions

A program can use the same interface as the browser. Split a seat link at the fragment marker. Send requests to the origin with `Authorization: Bearer <fragment>`. Use JSON objects for POST bodies.

| Request | Result |
|---|---|
| GET /state | Own seat number, referee view, perspective-specific history, phase and remaining time. |
| POST /ready with `{}` | Mark the authenticated seat ready. Timers begin after all seats are ready. |
| POST /choice with `{"revision":4,"choice":{"vote":true}}` | Submit a decision for the specified revision. |
| POST /say with `{"revision":4,"text":"Face 40 leads east."}` | Offer one public remark in this ballot's discussion window. |

All successful endpoints return the caller's current snapshot. `choices` is null while waiting. Otherwise its keys give the exact fields to submit, with legal values per field. For placement, combine one tile, one square and one clockwise rotation. For a pass or stay the relevant value is JSON null. A player submits their own boolean ballot. The host assembles the complete vote array in living-seat order. `state` includes the current actor, nominator, proposal or nominee, board, own hand and role, plus teammates for a bad seat. Model prompts distinguish the common information rule from the individual role briefing. A bad seat receives the complete starting map of both teams, including eliminated seats. A good seat sees its own alignment and the public counts and can make deductions from play. The same distinction applies when a model composes a public remark. Only its submitted words enter the discussion. The history supplies public ballots and the player's own draws and returns.

The revision is the count of committed referee events, including automatic draws. A failed or late submission cannot fill a later decision. HTTP 409 means the opportunity is closed for this seat; refresh the snapshot before deciding again. HTTP 400 reports malformed or illegal input. If a POST response is lost, fetch the latest state. A committed ballot sets `voted` only in the voter's own view until the collective reveal.

By default a ballot opens after 15 seconds of discussion and every decision has a 60-second response period. All living seats can speak once during discussion (500 characters maximum). Every seat receives the attributed remark in its history. Both teams may bluff. The host records what was said and offers no additional verification of its contents. The host checks its own monotonic clock even when clients disconnect. At a deadline it reveals missing ballots as timeouts counted as no, or applies the base rules' individual fallback. The server remains available after game end so seats can inspect the outcome.

## Playtest record

The host saves a complete base-1 prefix after each committed event and public remark. It creates a fresh owner-readable file and replaces checkpoints atomically. Unrevealed individual ballots are kept in host memory. A saved prefix replays in the existing record tools. Optional top-level `remarks` contain public text, seat, and the preceding event count. Remarks are annotations outside rules adjudication; the live history displays them and the host JSON preserves them for analysis. In the offline viewer, every perspective shows each speaker’s public words on the proposal or nomination frame, before the ballots are revealed. A checkpoint taken during discussion includes the remarks already made.

For the first nomination, record the nominator, target, turn, marker distance to EXIT, stated evidence, and how many subsequent builds any eliminated player sat out. Ask players which tile edges they found hard to read. Keep a scripted walkthrough distinct from observations of people making decisions. [First nomination playtest](https://github.com/othercriteria/footsteps/issues/3)

## Join with Ollama

Run `python -m footsteps ollama --model qwen2.5:3b` in a second terminal and paste one private seat link at the hidden prompt. The client marks that seat ready. Use an installed model served by Ollama on 127.0.0.1 port 11434. Each player process needs its own seat link. Processes can share an Ollama model or use different local tags. The other seats can be people or programs.

For each decision the client sends the seat’s current board, own hand and team information, legal choices, and its latest twelve history entries. That history includes public discussion. The ordinary client listens during discussion and requests a choice when a decision opens. Each decision starts with a fresh context. The basic menu uses zero-based indices. Named options and the optional placement check use the fields described below. The client verifies the fields and indices before submitting to the referee. [Ollama chat API](https://docs.ollama.com/api/chat) · [Structured outputs](https://docs.ollama.com/capabilities/structured-outputs)

Add `--guided` for role guidance and worked forward-build options, `--named-moves` for compass-direction proposals, `--named-ballots` for literal approve/reject votes, and `--no-think` to ask Ollama for direct answers on a short clock. Use `--action-brief` for a short description of the current decision and ballot choices naming the marker destination or nominee. This switch includes named ballots. [Matched games and proposal probes](../experiments/model-panel/README.md)

The inference budget defaults to 30 seconds and is capped by the host’s remaining time. Set it with `--budget 10`, for example. The client submits at most one choice per revision. A checked placement may use several model calls within that budget. A missing, invalid or late response leaves the decision open for the host’s usual timeout. A ballot remains visibly missing when the votes are revealed. The client can answer again on the next revision. The client terminal reports its own accepted choices, including private returns. [Two-turn model trial and replay](../experiments/ollama-crossing.md)

Add `--tools` to let the seat query a placement, compare marker landings, or check one builder’s public floor history before a nomination or removal vote. Add `--private-notes FILE` to ask for one short explanation in the model's final reply and save it beside the game. Choose a fresh path for each seat. The model's legal action alone goes to the table. The local owner-readable JSONL file records the model, seat, revision, attempted choice, tool names and short stated reason. It excludes the seat link and the model's separate thinking field. [Tool catalog and experimental design](seat-tools.md)

To view the notes at the matching decision, attach them explicitly to an omniscient HTML export. Repeat `--notes` for additional seat files. The first seat requesting notes receives a table ID for matching attachments, and the host adds it to the private record. Ordinary games keep their original record shape. Notes from a different live table are rejected. A note whose attempted choice differs from the committed event is labeled accordingly. Opening a private export shares its contents with the reader. Public and individual-seat exports exclude attached notes from their payloads. Existing records can still be viewed without attachments.

```sh
python -m footsteps ollama --model qwen3.5:9b-q8_0 --no-think --tools --private-notes /tmp/seat0.jsonl
python -m footsteps view /tmp/game.json --omniscient --notes /tmp/seat0.jsonl -o /tmp/omniscient.html
```

For a solitaire plan-selector trial, pass `--private-notes-dir` to `python -m experiments.turn_plans` with `--policy model`. Each note attaches to the placement event when the model picked its plan. The later proposal executes the selected destination. Select the corresponding `seat-SEED.jsonl` when exporting `game-SEED.json`.

Use `--social-policy assisted` with `python -m footsteps ollama` to try the cross-play player. It ranks provable team outcomes on proposals and ballots, and the model handles open choices with its own role, public evidence and possible consequences in view. A unique preferred outcome is attributed to “Footsteps outcome policy” in private replay notes. The `prompt` setting supplies the seat-relative prompt alone. Placement and discard continue through the ordinary seat adapter. [Matched trials and limits](../experiments/social-behavior/README.md)

## Checked placements

Start the host with `--placement-check edge` or `--placement-check edge-and-marker`. The browser and Ollama seat read the additional fields from the active builder’s legal menu. Submit `origin` as an existing non-EXIT coordinate adjacent to `at`, and `can_step` as a literal JSON boolean for that directed edge after rotation. The second mode also requires the boolean `marker_on_origin`. An incorrect submission returns HTTP 400 with a private explanation. The same revision and deadline remain available until a valid submission or timeout. The timeout samples an ordinary legal placement with the original distribution.

The Ollama seat provisionally chooses the face, rotation and square. A second prompt names the eligible origins, their outgoing sides, the tile’s rotated entrances and the marker square. The model has one correction attempt within its shared inference budget. The browser permits revisions to every field. The builder receives a private confirmation giving the marker’s actual one-step access to the new tile. The record identifies the interface mode and stores the committed placement. The public history excludes private checks and rejected attempts.

## Native action calls and private hand pieces

An authenticated snapshot includes `pieces`, a map from a seat-local handle such as `H2` to its printed face and current clockwise quarter turns. New copies arrive at zero turns and get fresh handles. A held copy keeps its orientation across turns and reconnects to the running host. A returned copy loses its handle. Duplicate faces can be manipulated independently. Historical records and clients may continue to use face values. If a face-only action or timeout consumes one of several copies, the host removes the oldest matching handle.

`POST /orient` takes `revision`, `piece` and absolute `rotation` (0–3). A ready, living seat can turn its own pieces privately until game end. The operation consumes no turn or revision and does not extend the clock. On `/choice`, a placement can send `piece`, `at` and an explicit `rotation`, or use the piece's present orientation. Including `expected_orientation` commits only if it still matches. A private return can also identify the piece. Existing checked-placement fields still apply. Only the ordinary placement or return enters the referee record.

For example, `python -m footsteps ollama --model qwen3.5:9b-q8_0 --action-tools hand --private-notes /tmp/seat.jsonl` gives a builder three native functions. It can orient a copy, preview a placement with that copy, or place it. A valid place call commits the choice through its existing authenticated seat link. Use `--action-tools direct` to specify a rotation inside the preview or placement instead. With `--all-decisions`, native calls also select a return, step, stay, nomination, pass, movement vote or removal vote. Other mandatory decisions use the ordinary client by default. A native decision has at most six model replies within the original deadline. Missing commitments receive the usual public fallback. Private notes can retain preparations, rejected calls and the eventual choice for omniscient replay.

To include actual hand turns in a transcript, start the host with `--private-rotations turns.jsonl`, then export with `python -m footsteps view game.json --omniscient --notes turns.jsonl -o replay.html`. Each entry shows the seat, copy, printed face and change in absolute orientation. It appears at the floor revision where it happened, before the next referee action, even when another player was acting or the piece was never placed. Multiple changes appear in order. A repeated request for the current orientation leaves no extra entry. The owner-only attachment stays separate from the game record. You can attach it alongside model notes. Older model notes can already show the model’s own orientation calls.
