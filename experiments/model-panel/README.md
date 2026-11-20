# Can a small local model play a whole table?

Sixteen completed games on one RTX 4090 produced 835 decisions and 761 referee events. Two Blue teams reached EXIT. Every decision arrived before its 15-second deadline, including concurrent ballots. The most repeatable improvement came from letting a model answer a movement proposal with a compass direction. [Game configurations in run order](runs.csv) · [Per-game results](results.csv)

## Can the builder use the tile it just placed?

Eight development games crossed two paper-kit deals (seeds 11 and 12), two models and two prompts. Each seat used the same model within a game. The plain prompt used the original legal option indices. The guided prompt added team advice and one worked placement per enterable new square closer to EXIT. The helper ranks rotations by usable onward exits using only the seat’s board and choices. The model can select any legal placement. All games used the full sixteen-tile kit, two tiles per hand, no discussion, and EXIT at (4, 2).

| Four-seat lineup | Blue forward builds / eligible builds | Blue forward proposals / opportunities | Blue wins |
|---|---:|---:|---:|
| Qwen2.5 3B plain | 1/14 | 1/1 | 0/2 |
| Qwen2.5 3B guided | 2/2 | 0/11 | 0/2 |
| Llama 3.1 8B plain | 1/9 | 5/5 | 0/2 |
| Llama 3.1 8B guided | 5/6 | 13/13 | 0/2 |

A forward build lets the marker enter the newly placed tile and reduce Manhattan distance on the next move. A forward proposal can use any legal tile closer to EXIT. These measures credit local progress. They miss useful detours, long-term construction, and reasons to avoid a trap. The denominator changes as the boards and surviving seats diverge. Seeds 11 and 12 both happened to assign P1 the Red role.

On both guided Qwen deals, P0 built an enterable floor north on turn one, then stayed at START. We froze its seat view before the proposal. North was the only move. With the indexed answers, Qwen2.5 3B took the first listed action on both deals in both orders. With the literal names `stay` and `north`, it chose north in all four cases. Llama chose north in 3/4 indexed and 4/4 named cases. Qwen3.5 4B with thinking disabled gave the same answers as the 3B. These two positions were selected after observing the original games. [All 24 probe replies](probe.csv)

On fresh seeds 13 and 14 we changed only the proposal encoding for guided Qwen2.5 3B. With indices, Blue builders proposed a closer move on **1/12** opportunities. The marker finished five and six squares away. With names, they did so on **8/8**, reached EXIT on turn six of seed 13 and finished two squares away on seed 14. Later options and ballots depend on earlier choices. The two matched deals establish a reason to keep testing named moves. [Six-turn win](qwen-names-13/game.json) · [Same starting deal with indices](qwen-index-13/game.json)

## Which lineups fit the workstation?

The original 481 calls had median / 95th-percentile latencies of 112 / 195 ms for Qwen2.5 3B and 169 / 329 ms for Llama 3.1 8B. The longest Llama call took 12.394 s. Calls include loading and queueing when they occur. The Qwen3.5 4B four-seat trial completed 41/41 decisions with a median of 493 ms and a 95th percentile of 661 ms. Its Blue team finished three squares away on seed 13. It used named moves, placement guidance and disabled thinking. [Qwen3.5 4B game](qwen4-names-13/game.json)

| Seats in order on seed 13 | Red seat | Winner | Largest number of overlapping ballot calls | Latest voter reply after ballot opened |
|---|---|---|---:|---:|
| 4B, 9B, 4B, 9B | P0 (4B) | Red on turn 8 | 4 | 4.754 s |
| 3B, 4B, 9B | P2 (9B) | Blue on turn 10 | 3 | 0.718 s |
| 9B, 4B, 3B | P2 (3B) | Red on turn 10 | 3 | 0.747 s |

The mixed seats all used guidance, named proposals and disabled thinking. `/api/ps` reported the three models resident at the same time with their full reported allocations on GPU, approximately 2.01, 2.92 and 8.38 GiB respectively. The overlapping intervals measure simultaneous client requests. Ollama schedules the underlying decoding. The last column estimates when inference returned from the table’s remaining clock at request time and the client’s elapsed inference time. The committed ballot includes the short additional seat submission trip. The mixed games ran consecutively, so later games could reuse loaded weights. [Three-model residency samples](mixed-three-large-red/residency.json) · [Per-seat calls](mixed-three-large-red/calls.csv)

Both three-seat games used identical initial roles, hands and bag. A full three-seat kit leaves ten movement opportunities compared with eight at four seats. In both three-seat games the Red P2 was eliminated on turn one and Blue P0 eventually played alone. The 3B survivor reached (3, 2) on turn nine and EXIT on the final draw. After swapping P0 and P2, the 9B survivor finished at (1, 2) and the eliminated 3B shared the win. One role swap cannot rank the models. P2 never had a building turn in either game. This posthumous win required no tile sabotage by the Red player. [Final-draw win](mixed-three-large-red/game.json) · [Posthumous win on the same deal](mixed-three-small-red/game.json)

Every game saw an elimination in the first round. On guided Llama seed 11, a sole Blue survivor proposed moves and voted against its own proposals on turns four through eight. That sequence is legal, all votes were explicit, and the prompt requested no rationale. The ballot representation is worth testing before using these games to change elimination or tie rules. [Replay](llama-guided-11/game.json) · [Ballot experiment](https://github.com/othercriteria/footsteps/issues/24)

## Reproduce and audit

Models were local Ollama 0.40.15 tags on a 24 GiB RTX 4090. The IDs were `357c53fb659c` (qwen2.5:3b), `46e0c10c039e` (llama3.1:8b), `d8b0f5e9760c` (qwen3.5:4b) and `a8ee95bc3592` (qwen3.5:9b-q8_0). Each request used temperature 0, sampling seed 1, a 4096-token context and up to 64 output tokens. Returns to the bag change future draws, even with a fixed draw RNG. Concurrent inference, local service load and backend versions may affect reproduction.

Voice services ran during the single-model games. For the three mixed games the workstation’s local-harness `scripts/with_speech_released.py` wrapper checked for active speech connections, paused the initially active `gpu-voice` group and restored it afterward. It verified the original states and speech port readiness. Ollama served throughout. This machine-specific step is optional when reproducing the games.

Run from the repository root. `runs.csv` gives the exact seat tags, seed and switches for each game. The examples reproduce the three-model lineup and the frozen probes. Use a fresh game output directory. The summary and transcript commands work offline.

```sh
python -m experiments.model_panel --model qwen2.5:3b qwen3.5:4b qwen3.5:9b-q8_0 --seats 3 --seed 13 --guided --named-moves --no-think --out /tmp/footsteps-mixed-repeat
python -m experiments.proposal_probe experiments/model-panel
python -m experiments.proposal_probe experiments/model-panel --models qwen3.5:4b --no-think
python -m experiments.model_panel_summary experiments/model-panel > /tmp/footsteps-panel-results.csv
cmp /tmp/footsteps-panel-results.csv experiments/model-panel/results.csv
python -m footsteps view experiments/model-panel/mixed-three-large-red/game.json --omniscient -o /tmp/final-draw.html
```

The audit replays each game, checks the tile multiset after every event including eliminated hands, and matches each private inference to the actor’s committed choice or the correct living seat’s revealed ballot. It checks for duplicate calls, extra calls, and missing or mismatched responses to committed choices. Each game directory contains its full synthetic referee record and decision log. Early runs recorded event, seat, stage, inference duration, choice and error. Later logs add model and start time. The mixed runs also include remaining decision time and residency samples. Empty timing cells in the summary indicate measurements unavailable for those runs.
