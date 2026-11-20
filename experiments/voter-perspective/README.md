# Whose removal am I voting on?

At turn 4, event 55 of five-seat deal 9901, P2 nominated Blue P4. Everyone voted No. P4 called P4 a confirmed Blue ally; P1 named an impossible Red roster and said three votes would fall short of a majority of five. All five notes attributed a pattern of removal votes to P4. P4 had voted No on all 16 earlier removal ballots. The ordinary seat's twelve-entry recent history contained three of those ballots, interleaved with public accusations. The published claims were real statements, but their content contradicted the recorded votes. [Game](../goal-pursuit/games/five-9901-last-r320.json)

Each of the five seats reconsiders event 55 and event 12 of a different five-seat game. On the second ballot the nominee is Red P1, who had publicly voted Yes on an earlier removal in the visible window. Both positions have three Blues and two Reds alive. These contrasts cover being the nominee, knowing the nominee is a teammate or opponent, and lacking the nominee's private alignment. [Second game](../minority/five-colors/8602-red1+3.json)

The four presentations cross two changes to the ordinary structured ballot request. The identity treatment binds my seat, private team and disclosed roster together at the start, places the nominee next to them, distinguishes the turn's builder, and uses P-prefixed names for living seats. The source treatment marks player statements with their speaker and labels referee events. All arms keep the same twelve entries, their order, and the two legal ballot choices. Each arm receives only the queried seat's projection.

For each presentation we request the ordinary ballot and short private reason. Independently, in a fresh request with the same evidence, we ask for the nominee's relationship to the voter under the setup disclosure and whether the nominee cast any Yes on the visible removal ballots. The model never sees its answers to these questions when casting its ballot. Those facts have verifiable answers. Neither voting No to defend oneself nor voting to remove an opponent is required.

## Reproduce

Run from the root, with local Ollama serving `qwen3.5:9b-q8_0`. Use fresh output filenames. The two requests use temperature zero, inference seed one, 4,096 tokens of context, a 144-token response budget, and a 30-second timeout. The files separate ballots and factual responses from the private ballot explanations.

```sh
out=$(mktemp -d)
python -m experiments.voter_perspective "$out/replies.jsonl" "$out/private.jsonl"
```

## Findings

In **all four presentations**, every seat on both tables voted No. On the independent fact check each presentation scored 10/10 on whether the nominee had cast a visible Yes and 5/10 on the relationship. The model answered *undisclosed* every time. That answer was correct for the five Blue observers of other seats, incorrect for both nominees and all three Red observers of other seats. P4's ordinary explanation at event 55 reproduced the original misidentification. Even with both changes, its private reason still described P4 as an ally who had voted to eliminate opponents. A correct answer to the separate history question therefore does not establish that the voter used the history when acting. The second game's original ballot had two Yes votes; the probes all use the 9901 decision interface. [Matched responses](replies.jsonl)

A follow-up on the same seats spelled out the relationship each voter already knew and what removal would do to the nominee. It used the existing seat-relative ballot names, including `yes_remove_myself` and `no_keep_myself`. This condition still produced ten No votes, ten *undisclosed* answers and ten correct history answers. On a **standalone boolean question** asking only “Are you the player nominated for removal on this ballot?”, the ordinary view missed both self cases and identified all eight other cases. The explicit relative view identified both self cases and all eight other cases. That is successful readback when the interface supplies the relationship. Neither self-nominee's ballot explanation in this condition clearly identified itself as the player being removed. [Relative ballots and fact checks](relative.jsonl) · [Standalone self check](self.jsonl)

```sh
python -m experiments.voter_perspective "$out/relative.jsonl" "$out/relative-private.jsonl" --relative
python -m experiments.voter_perspective "$out/self.jsonl" --self-check
```

For a player interface, first-person labels can make a removal understandable while leaving both votes available. Public quotations still need their original speaker, especially when they say “our allies.” For evaluating model play, look for the voter to apply these distinctions in its unprompted choices and reasons. These are ten seat perspectives on two selected positions using one model. The standalone self question changes both the task and its response format. Their individual effects remain unmeasured. The comparison leaves open whether any of these changes help during a complete game or on ballots where the seat would independently vote Yes.
