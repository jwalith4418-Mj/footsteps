# One model seat at the crossing

Can the referee advance a vote while a model reply is outstanding, then accept the same seat’s next decision? P2 played its good role with local `qwen2.5:3b` (model ID `357c53fb659c`, Ollama 0.40.15). Three scripted seats supplied the other decisions. The trial used the crossing setup, draw seed 1, a 30-second decision clock and zero discussion time. The experiment held the first movement reply until half a second past its deadline. All subsequent replies went through immediately.

| Event in the replay | What happened |
|---|---|
| 5 | P2’s inference took 5.49 seconds. With its reply held back, the referee recorded P2 as timed out. The 2–2 movement vote passed on P0’s Yes. |
| 7 | P2 voted to eliminate P3. The vote passed 3–1. |
| 8–9 | P2 nominated P0, who had built the crossing, then voted for elimination. P0 and P1 voted No and the nomination failed. |
| 14 | All three living seats voted to enter EXIT, including P2. Good won on the final draw. |

P2’s four subsequent inferences each took 0.09–0.10 seconds on this host. The injected delay checks deadline handling. This single deal with scripted opponents and no discussion gives little evidence about social strategy or ordinary timeout rates. The model supplied no rationale for its nomination. [Recorded game](ollama-crossing.json)

## Reproduce

With the named model installed and Ollama serving on its default loopback port, run from the repository root. Use a fresh output path. Model version and hardware can affect both choices and latency. The saved record replays independently of inference.

```sh
python -u -m experiments.ollama_crossing --model qwen2.5:3b --save /tmp/model-trial.json
python -m footsteps replay experiments/ollama-crossing.json --seat 2
python -m footsteps view experiments/ollama-crossing.json --seat 2 -o /tmp/model-p2.html
```
