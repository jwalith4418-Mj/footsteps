| Goal | Store after deal | Hand | Games per policy | random | greedy | exits | switch | route |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| (4, 2) | 6 | 2 | 200 | 0 | 25 | 189 | 49 | 59 |
| (4, 2) | 6 | 4 | 200 | 0 | 30 | 198 | 52 | 78 |
| (4, 2) | 10 | 2 | 200 | 0 | 17 | 198 | 40 | 199 |
| (4, 2) | 10 | 4 | 200 | 0 | 29 | 200 | 50 | 198 |
| (6, 0) | 6 | 2 | 200 | 0 | 9 | 176 | 19 | 176 |
| (6, 0) | 6 | 4 | 200 | 0 | 11 | 195 | 16 | 195 |
| (6, 0) | 10 | 2 | 200 | 0 | 9 | 192 | 15 | 195 |
| (6, 0) | 10 | 4 | 200 | 0 | 7 | 199 | 12 | 200 |

Ten-turn games, pooled across goal shape and hand size. Counts by finish turn.

| Policy | 6 | 7 | 8 | 9 | 10 | Loss | Of losses, certified trapped |
|---|---:|---:|---:|---:|---:|---:|---:|
| random | 0 | 0 | 0 | 0 | 0 | 800 | 130 |
| greedy | 62 | 0 | 0 | 0 | 0 | 738 | 160 |
| exits | 789 | 0 | 0 | 0 | 0 | 11 | 2 |
| switch | 117 | 0 | 0 | 0 | 0 | 683 | 142 |
| route | 534 | 167 | 70 | 17 | 4 | 8 | 4 |

Of 1600 paired starts, 441 reached the switch point. Both won 137, only switch won 116, only greedy won 0, and both lost 188.
