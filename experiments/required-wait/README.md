# Waiting while the table needs your decision

[The clock trial](../early-ballot/README.md) exposed a repeated failure. P1 waited after an already-submitted movement vote, correctly woke up to a nomination, then requested a second wait with 43 seconds left to nominate. That second wait woke only after the host timed it out. The same seat waited through its turn-two build and tile return under both discussion clocks.

The persistent client now returns an `action_required` receipt on a plain wait against an unchanged owed decision. It includes the currently available commit tools. Off-turn and optional-discussion waits still sleep until a visible change. A deliberately submitted `wait(force=true)` can wait through the current deadline. A stale cursor returns the new opportunity immediately, including if voting opened during inference. The table continues to use its original clock; the override grants no reserve credit.

## Reproduce

Run one complete early-clock game with three 9B Q8_0 persistent seats on the same seed 11301 as the clock trial. Use fresh output paths and keep the local GPU exclusive to the game. Run the frozen probes afterward. The offline audit requires only the study directory.

```sh
python -m experiments.early_ballot /tmp/124-game /tmp/124-owner --early-ballot
python -m experiments.required_wait /tmp/124-choices.jsonl
python -m experiments.early_ballot experiments/required-wait/early
```

The two frozen probes reconstruct the original turn-two build and return from the referee events at revisions 9 and 10. Each starts with a fresh P1 conversation, including its own hand and team, and scripts exactly one plain wait. Earlier discussion and the original model's private conversation are omitted. The model then has five native calls to make the owed choice at a fixed clock. A forced wait can advance that clock to expiry. These probes measure whether the model can act on the receipt. They cannot predict how often a model will choose to wait during a fresh game.
