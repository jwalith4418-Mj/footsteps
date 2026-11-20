# One localhost table

Start a host with `python -m footsteps table --save /tmp/game.json`. The default game shuffles the sixteen printed tiles and three good roles plus one bad role. Use `--seats 3` to deal two tiles to each of two good players and one bad player, leaving ten in the bag. For a rules walkthrough, `--crossing` uses the known seating, deal and first draw from the worked example. Players make all subsequent choices.

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

By default a ballot opens after 15 seconds of discussion and every decision has a 60-second response period. All living seats can speak once during discussion (500 characters maximum). The host checks its own monotonic clock even when clients disconnect. At a deadline it reveals missing ballots as timeouts counted as no, or applies the base rules' individual fallback. The server remains available after game end so seats can inspect the outcome.

## Playtest record

The host saves a complete base-1 prefix after each committed event and public remark. It creates a fresh owner-readable file and replaces checkpoints atomically. Unrevealed individual ballots are kept in host memory. A saved prefix replays in the existing record tools. Optional top-level `remarks` contain public text, seat, and the preceding event count. Remarks are annotations outside rules adjudication; the live history displays them and the host JSON preserves them for analysis. In the offline viewer, every perspective shows each speaker’s public words on the proposal or nomination frame, before the ballots are revealed. A checkpoint taken during discussion includes the remarks already made.

For the first nomination, record the nominator, target, turn, marker distance to EXIT, stated evidence, and how many subsequent builds any eliminated player sat out. Ask players which tile edges they found hard to read. Keep a scripted walkthrough distinct from observations of people making decisions. [First nomination playtest](https://github.com/othercriteria/footsteps/issues/3)

## Join with Ollama

Run `python -m footsteps ollama --model qwen2.5:3b` in a second terminal and paste one private seat link at the hidden prompt. The client marks that seat ready. Use an installed model served by Ollama on 127.0.0.1 port 11434. Each player process needs its own seat link. Processes can share an Ollama model or use different local tags. The other seats can be people or programs.

For each decision the client sends the seat’s current board, own hand and team information, legal choices, and its latest twelve history entries. That history includes public discussion. This first player listens during discussion and makes one inference when a decision opens. Each prompt starts fresh. The response selects a zero-based index for each field of the legal choices. The client verifies the fields and indices before submitting to the referee. [Ollama chat API](https://docs.ollama.com/api/chat) · [Structured outputs](https://docs.ollama.com/capabilities/structured-outputs)

Add `--guided` for role guidance and worked forward-build options, `--named-moves` for compass-direction proposals, `--named-ballots` for literal approve/reject votes, and `--no-think` to ask Ollama for direct answers on a short clock. Each switch is independent. [Matched games and proposal probes](../experiments/model-panel/README.md)

The inference budget defaults to 30 seconds and is capped by the host’s remaining time. Set it with `--budget 10`, for example. Each revision gets one attempt. A missing, invalid or late response leaves the decision open for the host’s usual timeout. A ballot remains visibly missing when the votes are revealed. The client can answer again on the next revision. The client terminal reports its own accepted choices, including private returns. [Two-turn model trial and replay](../experiments/ollama-crossing.md)

Add `--tools` to let the seat query a placement or movement before deciding. Add `--private-notes FILE` to ask for one short explanation in the model's final reply and save it beside the game. Choose a fresh path for each seat. The model's legal action alone goes to the table. The local owner-readable JSONL file records the model, seat, revision, attempted choice, tool names and short stated reason. It excludes the seat link and the model's separate thinking field. [Tool catalog and experimental design](seat-tools.md)

To view the notes at the matching decision, attach them explicitly to an omniscient HTML export. Repeat `--notes` for additional seat files. The first seat requesting notes receives a table ID for matching attachments, and the host adds it to the private record. Ordinary games keep their original record shape. Notes from a different live table are rejected. A note whose attempted choice differs from the committed event is labeled accordingly. Opening a private export shares its contents with the reader. Public and individual-seat exports exclude attached notes from their payloads. Existing records can still be viewed without attachments.

```sh
python -m footsteps ollama --model qwen3.5:9b-q8_0 --no-think --tools --private-notes /tmp/seat0.jsonl
python -m footsteps view /tmp/game.json --omniscient --notes /tmp/seat0.jsonl -o /tmp/omniscient.html
```

For a solitaire plan-selector trial, pass `--private-notes-dir` to `python -m experiments.turn_plans` with `--policy model`. Each note attaches to the placement event when the model picked its plan. The later proposal executes the selected destination. Select the corresponding `seat-SEED.jsonl` when exporting `game-SEED.json`.
