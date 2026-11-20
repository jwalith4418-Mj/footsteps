# Can one model play the floor?

A single Blue seat plays a complete solitaire game. It chooses each tile, square, rotation, discard and movement. The referee draws, rotates and enforces the same directed edges used at a social table. The sole seat automatically approves its proposal, as in the existing solitaire policies. There is no discussion. This removes self-vetoes, elimination and opponent play as explanations for a loss. [Protocol and amendments](https://github.com/othercriteria/footsteps/issues/38)

## What the seat sees

The direct prompt includes the public board, marker, EXIT, turn, stage, store count, the seat's current hand and the legal fields. Each tile shows its true face and its incoming and outgoing compass directions. A placement response gives a literal face, clockwise rotation and coordinate. A movement response names the destination or stay. The prompt uses a fresh context on every decision. The deal seed, store contents, future draws and hard-coded policies are unavailable to the seat.

The aided prompt adds the mechanical consequences of local choices. For **every** enterable adjacent build it lists the face, rotation and usable outgoing edges, including opportunities into unbuilt squares. For movements it lists distance, outgoing edges and whether a closed directed component makes EXIT permanently unreachable. Menu values are identical across arms. The aid can do much of the geometric work. Aided results measure the model's use of that information.

Each deal uses goal (4,2), a two-tile starting hand, ten tiles in the post-deal store and independent entrance/exit bits at density 0.55. Four scripted controls use the same initial deal and draw RNG. Different discards can change later draws. Development deals are 100–103. Evaluation deals are 4001–4008. The target declared before opening them was six wins, at most one certified trapped finish and seven correct detour choices. The criterion applies to local board play under this kit and clock.

In the detour fixture, one step gets closer to EXIT but the tile has no exits. The perpendicular step increases Manhattan distance and has an exit facing the goal side of the board. We reflected both axes and exchanged the order of the two moves on each resulting board. Stay is available first in all eight menus. We score the explicit progressing detour. Waiting can leave the position recoverable. The eight answers represent four reflected presentations of a single tactic.

## Matched games

All three direct-answer models lost the same four development deals with the coordinate-list prompt. On deal 100, Qwen2.5 placed face 163 east of START without a west entrance, then spent the remaining turns building beyond the marker. Qwen3.8 finished that deal at START as well. With the edge report, Qwen3.8 won deal 101 in six turns, and Qwen3.5 9B won deals 101 and 103 in seven and eight. The models made every decision within the direct-answer clock. [32B stalled opening](dev/game-100.json) · [27B six-turn win](27b-dev-edges/game-101.json) · [9B eight-turn win](9b-dev-edges/game-103.json)

| Model | Direct wins / 4 | Aided wins / 4 | Detours / 8, direct | Detours / 8, aided |
|---|---:|---:|---:|---:|
| Qwen2.5 32B | 0 | 0 | 1 | 1 |
| Qwen3.5 9B Q8 | 0 | 2 | 5 | 0 |
| Qwen3.8 27B RANA-layout | 0 | 1 | 1 | 0 |

The newer-model selection used development wins first, then detour choices and distance in the event of a tie. This sent aided Qwen3.5 9B to the eight fresh deals. The four scripted controls offer a scale for those exact deals. Random won 0/8, greedy 3/8, exits 7/8 and route 8/8. Route finished in six to eight turns. Qwen2.5 32B won 0/8 in each of its direct and aided arms. The selected Qwen3.5 9B also won 0/8 and finished in three certified traps. All eight deals were solvable by at least one of the scripted policies. [9B holdout scores](9b-test-edges/results.csv) · [Matched 32B scores](test-edges/results.csv)

Qwen3.5 9B with edge information stayed seven times and entered the dead end once on the loose detour. We repeated the eight decisions with a five-tile starting store and showed the four remaining movement opportunities explicitly. It gave the same eight answers. In the tight position every route around the dead end needs at least four moves. A stay leaves three. A regression test plays the four-move winning continuation on each reflection. [Tight diagnostic](9b-test-edges/tight-detours.csv)

The [ASCII trial and tokenizer measurements](ascii.md) test whether a spatial representation changes the same model's decisions.

The 27B thinking arm used 1,024 total generated tokens and 60 seconds per decision. All eight detour calls reached the token ceiling. All 29 decisions in the seed-100 game returned a thinking field and stopped at exactly 1,024 tokens. The benchmark took its recorded fallback in all 29 cases. This measures the runner at that budget. It provides no evidence that the model chose those fallback moves. The original decoder treated any length stop as invalid before checking the answer. The current decoder accepts a complete legal action at the boundary. The original final content was not retained, so the effect of that distinction on these calls is unknown. [Thinking-run telemetry](27b-reason/calls-100.csv)

The [offline decision analysis](traces.md) separates forced and discretionary stays and identifies which placements made the marker's component permanently closed.

## Workstation and evidence

The RTX 4090 has 24 GiB of VRAM. Each run uses one model for every move. Tags were local, and each folder contains a residency sample, referee records, model decision latencies and errors, and per-seed model and baseline scores. Direct answers use temperature zero, seed 1, an 8192-token context, a 96-token generation limit and a 30-second decision clock. A missed or malformed response takes the referee's seeded timeout action. The first cold 32B load exceeded the clock before making a decision. All scored runs preload the model separately.

| Ollama tag | Weight identity |
|---|---|
| qwen2.5:32b | 9f13ba1299af |
| qwen3.5:9b-q8_0 | a8ee95bc3592 |
| footsteps-qwen3.8:27b-rana-layout | Qwen3.8-27B-RANA-layout-Q4_K_M.gguf, SHA-256 91c34c55de4defcc5891f08997b7d4543a171d7e2aa6ab752bff4eec27279ba6 |

The 27B file contains base weights with the RANA tensor precision layout. We used its embedded chat template in Ollama 0.40.15. The 32B and 27B runs used the local harness's restoring voice wrapper. After the first 32B development panel, its resident weights left too little VRAM for Whisper to restart. Unloading the runner and reissuing the group start restored all three speech ports. Subsequent reserved panels unload the model before the wrapper restores speech.

## Reproduce

Use the locked shell at the repository root and an empty output directory. The game runner uses the Python standard library. Ollama serves only on localhost. To import the 27B under the same name, write a Modelfile containing `FROM /path/to/Qwen3.8-27B-RANA-layout-Q4_K_M.gguf`, then run `ollama create footsteps-qwen3.8:27b-rana-layout -f Modelfile`.

```sh
python -m experiments.model_solitaire --model footsteps-qwen3.8:27b-rana-layout --detours --seeds 100 101 102 103 --out /tmp/footsteps-27b-dev
python -m experiments.model_solitaire --model footsteps-qwen3.8:27b-rana-layout --aided --detours --seeds 100 101 102 103 --out /tmp/footsteps-27b-edges
python -m experiments.model_solitaire --model qwen2.5:32b --aided --seeds 4001 4002 4003 4004 4005 4006 4007 4008 --out /tmp/footsteps-32b-held-out
python -m experiments.model_solitaire_audit experiments/model-solitaire/*/
python -m footsteps view experiments/model-solitaire/dev/game-100.json --seat 0 -o /tmp/footsteps-solo.html
```

The offline audit regenerates all four scripted policies, verifies each logged model decision or explicit fallback against the event sequence, reconstructs every chance draw and replays every game after rotating its goal, coordinates and tile orientations by 90 degrees. It compares board, marker, decision stage and winner after every event. Backend scheduling and hardware can change live inference and latency.
