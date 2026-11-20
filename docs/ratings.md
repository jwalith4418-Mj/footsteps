# Measuring a seat's contribution to team wins

What changes when one seat at a five-player table runs a different policy? The blinded guest saw a two-turn trap that the local players missed. A single Red win also fits a world where every available replacement would have won that deal. Keep the tactic as a skill probe and measure the effect on team outcomes separately. [Guest game and worked turn](../experiments/blind-guest/README.md)

## First comparison

Use three Blue and two Red. Freeze the rules, tile kit, offset, turn budget and public discussion protocol. Give each policy an identifier covering model weights and quantization, prompt revision, tools and automatic decisions, inference settings, and deadline. For a human or guest record the participant or policy identity, permitted aids, and prior exposure to the panel. A change to any playing aid creates a new candidate.

For each starting deal and role layout play three games. In the first, the anchor policy plays all seats. In the second replace one Red with the candidate. In the third replace one Blue. The four other seats in each comparison run the same policies on the same starting hands. Later play can diverge. Use the same chance stream convention and record realized draws, decisions, timeouts and the terminal reason. Shuffle execution order within a block using a recorded seed. Isolate sessions and fix concurrency when wall-clock limits matter. Keep incomplete runs in a ledger with a reason and rerun an interrupted block before including it.

The schedule rotates both Red seats around the table. Each candidate plays once per physical seat on each side per deal. Consecutive deal blocks alternate adjacent and separated Red pairs. The CSV uses B for Blue and R for Red. The current social runner uses G for Blue and B for Red. Translate the team column explicitly when constructing a setup. A row identifies a planned table, not a played game.

```sh
python -m experiments.rating_schedule --seeds 9001 9002 --anchor qwen-baseline-v1 --candidate qwen-candidate-v1 > /tmp/footsteps-panel.csv
```

Two deals give 30 games and ten matched comparisons per side. Each baseline result is shared by the two comparisons. Preserve the full initial setup or its digest so differences in deal generation across runners are detectable. Reserve fresh deals for confirmation. Freeze the candidate before opening them.

Report baseline wins, candidate wins, loss-to-win and win-to-loss flips, separately from the perspective of Blue and Red. Role uplift is (favorable flips minus unfavorable flips) divided by that role's matched pairs. Count one outcome per game. An eliminated player shares the team's result, including a posthumous win. Publish distinct deal and lineup counts alongside totals. For enough deals, resample whole deal blocks for uncertainty, retaining the shared anchor games. With only a couple of deals, publish the individual contrasts and leave uncertainty unresolved. If only one team ever wins, calibrate the scenario on a separate development panel before spending on a rating ladder.

## Once enough distinct policies play

Team-rating methods such as TrueSkill infer individual strength from joint outcomes and carry uncertainty about that strength. Teammates who always appear together cannot be distinguished by the outcomes alone. Footsteps also assigns different information and objectives by role. [Original TrueSkill paper](https://proceedings.neurips.cc/paper/2006/file/f44ee263952e65b3610b8ba51229d1f9-Paper.pdf) · [Microsoft Research FAQ](https://www.microsoft.com/en-us/research/project/trueskill-ranking-system/)

A candidate model for Footsteps is a regularized logistic fit to one row per game:

```text
log odds of Blue winning = setup advantage
                         + sum of Blue-role strengths in the Blue seats
                         - sum of Red-role strengths in the Red seats
                         + deal and seat-layout effects
```

Anchor both strengths of one fixed reference policy at zero. The intercept then expresses the all-anchor table's side advantage. A policy seated twice contributes twice to that game's predictor. Keep role estimates separate, shrink sparse estimates towards the reference and report interval estimates and opponent coverage. Cross partners and opponents after the substitution pilot, including candidate-versus-candidate games. Assess the additive assumption on mixed lineups where coordination or a particularly persuasive player could change another seat's contribution.

Compare held-out probability predictions against a setup-and-layout-only baseline with log loss, Brier score and observed win frequencies. Hold out whole deals and confirm transfer to previously unseen lineups. Record performance by offset and policy pool before comparing across them. If a displayed Elo-like scale becomes worthwhile, multiply a fitted role coefficient by 400 / ln(10) for a rating difference against the anchor. Its meaning is conditional on the other seats and the setup. A single blended rating also needs an explicit role distribution.

## What to measure alongside wins

Keep frozen, seat-visible tests for recognizing a trap before a ballot, carrying out a legal placement on the next turn, and verifying a public accusation. Vary turn order, rotate faces, include cases where the trap is impossible, and track voluntary tool use independently of forced exposure. Report attempts, successful actions and deadlines. Those measurements can reveal a gap even when two policies win all the same games. The pilot's first deliverable is paired win data on fresh deals. No current game assigns the guest or Qwen a numerical rating.
