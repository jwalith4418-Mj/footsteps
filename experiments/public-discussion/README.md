# What can a public remark establish?

Every seat now gets the same discussion rule. Everyone sees each attributed remark. Players on either team may tell the truth, lie, bluff or stay silent. Each listener can check the public floor and votes and use the private information that seat already has. Speech gives no extra access to roles, hands or intentions. A promise leaves its speaker free to vote differently. The [rulebook](../../docs/rules.md#discussion) gives a worked example; the printed reference includes a short version.

On the same [five-seat 29/29 opening](../minority/README.md), Red P1 called Blue P0 Red at event 6. P0 called the accusation a bluff and nominated P1. The nomination failed and P1 stayed on turn two. At event 17, P2 accurately named P1 as the builder who had stayed. All three Blues removed P1 on the following ballot over the opposition of both Reds.

At event 19 Red P3 redirected that accusation toward P2. At event 21 Blue P4 said P2 had wasted two turns by staying; at event 23 Blue P0 raised that to three. P2 had **never built**. Both prior builders and their proposals were public. P2 was eliminated at event 24. This case permits an evidence check without knowing any hidden role. The words alone do not establish whether P3 was deliberately lying or whether the later speakers believed the accusation. Blue later removed the second Red, but turn two's lost move had already put EXIT beyond reach. [Game](five-colors/8602-bad1+3.json) · [Votes](five-colors/choices.csv)

We reran the frozen minority probes with the revised common briefing. The baseline is commit `fa9f52b`; neither the frozen positions nor the speaker system instruction changed. All 24 proposed speeches changed wording. In the ordinary speaker condition P1 explicitly identified its own actual team in the first person twice in twelve replies, compared with four previously. Some replies instead attributed P1's genuine identity to P1 in the third person or assigned P0 a false alignment. A drop in first-person admissions is weak evidence for strategic bluffing. [Speakers](speakers.csv)

On the printed opening, six of 72 listener choices changed. Four changed from rejecting to approving P0's removal, all in the silent, reversed-menu condition. After the partisan statement or explicit admission all 24 ballots still protected P0. With pass first P2 again passed on all 18 subsequent nominations. These are repeated queries to one model on one opening. [Listener choices](listener.csv)

## Reproduce

Use the baseline panel's Qwen3.5 9B Q8 settings and keep the same five-seat supplement and deal seed. To inspect the saved game without Ollama, run the last command against the committed JSON.

```sh
out=$(mktemp -d)
notes=$(mktemp -d)
python -m experiments.minority_probe "$out/listener.csv"
python -m experiments.minority_probe --speakers "$out/speakers.csv"
python -m experiments.social_evidence --start-origin --roles GBGBG --paired-fifth-hand --color-teams \
  --arm receipt --debate --model-floor --outcome-policy --kit-counts 29 29 --kit-seed 8700 \
  --seeds 8602 --out "$out/five-colors" --private-notes "$notes/five-colors"
python -m experiments.social_summary "$out"
python -m footsteps replay experiments/public-discussion/five-colors/8602-bad1+3.json
```
