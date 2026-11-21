# Larger contexts for three persistent 9B seats

The earlier 4k game spent almost a third of inference service time generating private summaries. Does doubling the window continue to reduce that cost once the model has 8k? Use Qwen3.5 9B Q8_0 (`a8ee95bc3592`) on the same RTX 4090. Seat identities, starting hands, draw seed, single inference queue, 30-second discussion window and 45-second decision period match across runs. All games use the persistent tool interface and its base system prompt. The 16k and 32k runs include the merged change that stops inference after elimination. It would have affected the 4k game. The 8k game had no eliminations.

The runner asks for a summary after a measured prompt exceeds about 74.5% of the window. A player can also compact voluntarily earlier. Ordinary requests allow 240 output tokens, and a dedicated compact request allows one tenth of the window. Service time subtracts time spent waiting for the inference queue. It includes prompt evaluation and output generation. Summaries are private. The public receipts report their cost and size in tokens.

## Live games

| Window | Calls | Dedicated + voluntary summaries | Summary service seconds / all service seconds | Largest measured prompt | Timely decisions | Remarks / available seat-windows | Wall seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| [4k](three-9b-30s/) | 263 | 40 + 20 | 111.6 / 368.7 (30%) | 3,863 | 22/24 | 11/11 | 368.7 |
| [8k](three-9b-8k-30s/) | 178 | 13 + 3 | 43.1 / 267.0 (16%) | 7,107 | 22/23 | 8/9 | 267.8 |
| [16k](three-9b-16384-30s/) | 112 | 3 + 0 | 9.1 / 140.3 (6.5%) | 12,757 | 16/16 | 5/6 | 167.6 |
| [32k](three-9b-32768-30s/) | 161 | 1 + 5 | 14.6 / 237.6 (6.1%) | 24,784 | 23/24 | 15/15 | 312.6 |

Every eligible player had at least one reply ready before discussion closed in each game. At 16k two seats were eliminated on turn one, leaving the last player to finish the game alone. At 32k three removal nominations failed on turn one and all three seats remained active. On turn two Red proposed the winning step and Blue reached EXIT. The runtime and the different outcomes cannot rank context sizes for playing strength. At 32k five of the six summaries were voluntary, all requested at prompts under 3,000 tokens. The one capacity-triggered summary cost 5.2 seconds, 1.7% of the game's wall time. Raising the threshold again could save little direct summary time on that workload. Longer games or more independent seats could change the result.

## Matched prompt cost

On this machine the reserved model was fully GPU-resident at every measured size. Ollama reported 9.25 GB at 8k, 9.54 GB at 16k and 9.97 GB at 32k (decimal). For identical input the cost of reserving a larger window was small. Actually filling a larger window had a measurable cost when the prompt was uncached.

| Fixed prompt tokens | Context(s), in order | Empty-cache prefill, seconds | Exact-repeat prefill, seconds |
|---:|---|---|---|
| [5,606](prefill-short.jsonl) | 8k, 16k, 32k | 0.487, 0.496, 0.486 | 0.066, 0.065, 0.064 |
| [11,282](prefill-medium.jsonl) | 16k, 32k | 0.985, 0.987 | 0.068, 0.069 |
| [19,538](prefill-long.jsonl) | 32k | 1.733 | 0.067 |

These are single paired requests, with matching input digests and reported token counts at each prompt length. Live seats interleave distinct conversations, so an exact repeat is an optimistic cache comparison. Each function name and reply length matched across the windows on the same input. After five scripted state reads the model proposed a step. After 16 and 32 reads it chose to read again. This fixture measures prompt processing and cannot establish whether longer histories improve judgment.

For the next three-seat 9B discussion studies on this GPU, use 32k when the model runs alone. It cost about 0.43 GB more than 16k, the paired requests showed little extra prefill cost, and compulsory summarization consumed only 5.2 seconds. Use 16k as the lower-memory comparison. The observed drop in total summary service share from 6.5% to 6.1% places the practical knee near 16k for these short games. A 64k test would be more informative on a longer table that regularly crosses the 32k threshold.

## Reproduce

Use fresh output directories. The full-table report takes a saved game directory as its only argument. Direct inputs, hand contents and notes stay in the owner trace. Ollama's resident size and GPU-resident size are measured in bytes after play. The warmup runs before the table clock starts.

```sh
out=$(mktemp -d)
for ctx in 16384 32768; do
  python -m experiments.persistent_table "$out/table-$ctx" "$out/private-$ctx" \
    --model qwen3.5:9b-q8_0 --context "$ctx" --discussion-seconds 30
done
python -m experiments.persistent_prefill "$out/short.jsonl" --contexts 8192 16384 32768 --reads 5
python -m experiments.persistent_prefill "$out/medium.jsonl" --contexts 16384 32768 --reads 16
python -m experiments.persistent_prefill "$out/long.jsonl" --contexts 32768 --reads 32
```

The fixed requests come from a real seat projection after a scripted bridge build. The experiment appends the indicated number of valid state-read calls and receipts at the same referee time, then freezes the next request. Each row carries a digest computed before the context-size change. For each length and window, unload the model, warm the weights without a conversation, request once, then repeat the identical request. Ollama reports prompt evaluation and generation separately. The deliberate repeated reads measure inference cost with controlled inputs. They are not a game strategy or evidence of player skill.
