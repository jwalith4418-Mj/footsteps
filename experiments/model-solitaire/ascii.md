# Does a board chart help a model read the floor?

The compact prompt draws one vertex per square. Board tiles use their installed face, including rotation. The hand lists true faces, including duplicates. A single key gives the absolute entrances and exits of every numbered face. In this example, face 8 admits the marker from its west and has no exit. Face 36 admits it from the south and lets it continue east.

```text
S START, X EXIT (both open), @ marker, . unbuilt
y/x  0  1  2
  1 36  .  .
  0 @S  8  X
Hand: 255 255
Face=in>out: 8=W>- 36=S>E 255=NESW>NESW
```

## Token cost

We tokenized all 29 model decisions in the Qwen3.8 direct run on development deal 100 using the vocabulary in the same RANA-layout GGUF. Each comparison holds the seat, turn, board, hand, stage and legal action schema fixed. Counts cover the entire user message. The system text and chat wrapper are constant across the comparison. The spoke drawing puts one directional port around each side of each tile and repeats the layout for the hand.

| User message | Tokens across 29 decisions | Median tokens | Range |
|---|---:|---:|---:|
| Original JSON | 5,543 | 188 | 103–295 |
| JSON plus spoke drawing | 15,456 | 534 | 375–700 |
| Spoke drawing replaces board and hand | 11,587 | 406 | 306–516 |
| Vertex chart replaces board and hand | 6,624 | 225 | 152–324 |

JSON was shortest at all 29 decisions. The vertex chart added 20–58 tokens per decision and 19.5% in aggregate. Replacing the spoke drawing with the vertex chart saved 42.8% across this game. Busy or widely separated boards can change the result. The live trial selected the vertex chart. [Per-decision counts](chart-tokens.csv) · [Protocol and three-position measurement before play](https://github.com/othercriteria/footsteps/issues/43)

## Play on matched positions

Qwen3.8 27B ran with thinking disabled and the full legal menu. Both presentations completed 116 decisions on the same four initial deals without a fallback. The chart changed play but produced no additional wins. It improved two final distances by one step and also produced a certified trap on deal 103.

| Presentation | Wins | Final distances on 100, 101, 102, 103 | Certified trapped finishes | Detours chosen | Median decision latency |
|---|---:|---|---:|---:|---:|
| JSON | 0/4 | 6, 4, 4, 6 | 0/4 | 1/8 | 832 ms |
| Vertex chart | 0/4 | 6, 4, 3, 5 | 1/4 | 2/8 | 921 ms |

The chart did not reach the prespecified threshold of two additional wins or four additional detour choices for a fresh-deal trial. The mirrored menus all describe the same tactic, and a single decode per menu gives little precision. Keep the chart as a reproducible option. These timings came from successive panels and include queue and prompt processing. [Chart decisions](27b-ascii/detours.csv) · [Seed 103 replay](27b-ascii/game-103.json) · [Matched direct replay](27b-dev-direct/game-103.json)

## Reproduce

```sh
python -m experiments.chart_tokens experiments/model-solitaire/27b-dev-direct/game-100.json --gguf /path/to/Qwen3.8-27B-RANA-layout-Q4_K_M.gguf --tokenizer /path/to/llama-tokenize > /tmp/footsteps-chart-tokens.csv
cmp /tmp/footsteps-chart-tokens.csv experiments/model-solitaire/chart-tokens.csv
python -m experiments.model_solitaire --model footsteps-qwen3.8:27b-rana-layout --ascii --detours --seeds 100 101 102 103 --out /tmp/footsteps-chart
```

The tokenizer ran offline with llama.cpp build ddf48f85. Counts concern input representation. Playing skill is scored on the original goal, moves and clock.
