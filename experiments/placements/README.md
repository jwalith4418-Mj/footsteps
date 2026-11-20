# Can a model distinguish an onward exit from a trap?

The Blue builder used face 12 with no exits on turn two of [deals 22 and 23](../ballots/README.md). Both hands contained face 41, which could be entered and left. We offered the two complete legal placements at the same square, framed the local objective assuming the marker enters, and tested the builder as both Blue and Red. Swapping the builder's role with another seat preserves the initial role count. Replaying the same prefix preserves the hand, draws and observable board. Only the builder's own view enters the prompt.

On fresh reference deals 31, 32 and 33, we selected the first placement with a closer square admitting both a certified trap and a playable face with a goalward exit. All three qualified. We used the first qualifying square in compass order and the first face and rotation in legal menu order for each category. Each pair was presented in both orders. Both menu encodings display the same oriented tile and complete action. The answer selects either its zero-based index or its literal face/rotation identifier. Blue is scored for retaining the onward exit and Red for sealing the route, conditional on the stated entry.

| Model | Encoding | Original deals, Blue | Original deals, Red | Fresh deals, Blue | Fresh deals, Red |
|---|---|---:|---:|---:|---:|
| Llama 3.1 8B | index | 2/4 | 2/4 | 3/6 | 3/6 |
| Llama 3.1 8B | literal | 4/4 | 0/4 | 3/6 | 3/6 |
| Qwen3.5 4B | index | 3/4 | 1/4 | 4/6 | 3/6 |
| Qwen3.5 4B | literal | 3/4 | 2/4 | 5/6 | 1/6 |

Literal actions gave Qwen five correct replies in six fresh Blue-seat trials and one in six fresh Red-seat trials. Llama lost the apparent Blue-seat gain on the three fresh positions. Neither model cleared the condition for a full-game trial of these restricted menus. The eighty answers represent only five underlying positions. The next single-seat test can ask about board reading without the role reversal. [Raw decisions](probe.csv) · [Protocol](https://github.com/othercriteria/footsteps/issues/36) · [Solitaire benchmark](https://github.com/othercriteria/footsteps/issues/38)

Run from the root with the Ollama versions and settings in the ballot report. No full game is played by the probe.

```sh
python -m experiments.placement_probe experiments/ballots > /tmp/placement-probe.csv
```
