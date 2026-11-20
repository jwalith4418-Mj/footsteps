# Can one model play the floor?

A single good seat plays a complete solitaire game. It chooses each tile, square, rotation, discard and movement. The referee draws, rotates and enforces the same directed edges used at a social table. The sole seat automatically approves its proposal, as in the existing solitaire policies. There is no discussion. This removes self-vetoes, elimination and opponent play as explanations for a loss. [Protocol and amendments](https://github.com/othercriteria/footsteps/issues/38)

## What the seat sees

The direct prompt includes the public board, marker, EXIT, turn, stage, store count, the seat's current hand and the legal fields. Each tile shows its true face and its incoming and outgoing compass directions. A placement response gives a literal face, clockwise rotation and coordinate. A movement response names the destination or stay. The prompt uses a fresh context on every decision. The deal seed, store contents, future draws and hard-coded policies are unavailable to the seat.

The aided prompt adds the mechanical consequences of local choices. For **every** enterable adjacent build it lists the face, rotation and usable outgoing edges, including opportunities into unbuilt squares. For movements it lists distance, outgoing edges and whether a closed directed component makes EXIT permanently unreachable. Menu values are identical across arms. The aid can do much of the geometric work. Aided results measure the model's use of that information.

Each deal uses goal (4,2), a two-tile starting hand, ten tiles in the post-deal store and independent entrance/exit bits at density 0.55. Four scripted controls use the same initial deal and draw RNG. Different discards can change later draws. Development deals are 100–103. Evaluation deals are 4001–4008. The target declared before opening them was six wins, at most one certified trapped finish and seven correct detour choices. The criterion applies to local board play under this kit and clock.

In the detour fixture, one step gets closer to EXIT but the tile has no exits. The perpendicular step increases Manhattan distance and has an exit facing the goal side of the board. We reflected both axes and exchanged the order of the two moves on each resulting board. Stay is available first in all eight menus. We score the explicit progressing detour. Waiting can leave the position recoverable. The eight answers represent four reflected presentations of a single tactic.

## Workstation and evidence

The RTX 4090 has 24 GiB of VRAM. Each run uses one model for every move. Tags were local, and each folder contains a residency sample, referee records, model decision latencies and errors, and per-seed model and baseline scores. The decision clock is 30 seconds. A missed or malformed response takes the referee's seeded timeout action. The first cold 32B load exceeded the clock before making a decision. All scored runs preload the model separately.

| Ollama tag | Weight identity |
|---|---|
| qwen2.5:32b | 9f13ba1299af |
| qwen3.5:9b-q8_0 | a8ee95bc3592 |
| footsteps-qwen3.8:27b-rana-layout | Qwen3.8-27B-RANA-layout-Q4_K_M.gguf, SHA-256 91c34c55de4defcc5891f08997b7d4543a171d7e2aa6ab752bff4eec27279ba6 |

The 27B file contains base weights with the RANA tensor precision layout. We used its embedded chat template in Ollama 0.40.15. The 32B and 27B runs used the local harness's restoring voice wrapper. After the first 32B development panel, its resident weights left too little VRAM for Whisper to restart. Unloading the runner and reissuing the group start restored all three speech ports. Subsequent reserved panels unload the model before the wrapper restores speech.

## Reproduce

Use the locked shell at the repository root and an empty output directory. Each command runs without third-party Python dependencies. Ollama serves only on localhost. To import the 27B under the same name, write a Modelfile containing `FROM /path/to/Qwen3.8-27B-RANA-layout-Q4_K_M.gguf`, then run `ollama create footsteps-qwen3.8:27b-rana-layout -f Modelfile`.

```sh
python -m experiments.model_solitaire --model footsteps-qwen3.8:27b-rana-layout --detours --seeds 100 101 102 103 --out /tmp/footsteps-27b-dev
python -m experiments.model_solitaire --model footsteps-qwen3.8:27b-rana-layout --aided --detours --seeds 100 101 102 103 --out /tmp/footsteps-27b-edges
python -m experiments.model_solitaire --model qwen2.5:32b --aided --seeds 4001 4002 4003 4004 4005 4006 4007 4008 --out /tmp/footsteps-32b-held-out
python -m experiments.model_solitaire_audit experiments/model-solitaire/*/
python -m footsteps view experiments/model-solitaire/dev/game-100.json --seat 0 -o /tmp/footsteps-solo.html
```

The offline audit regenerates all four scripted policies, verifies each logged model decision or explicit fallback against the event sequence, reconstructs every chance draw and replays every game after rotating its goal, coordinates and tile orientations by 90 degrees. It compares board, marker, decision stage and winner after every event. Backend scheduling and hardware can change live inference and latency.
