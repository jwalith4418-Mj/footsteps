# Footsteps · base rules 1

A group explores a tiled floor. The good team wants the marker to reach the exit. The bad team wants to exhaust the tile store first. Tables can call the exit team **Blue** and the team obstructing it **Red**. Everyone knows both objectives and the starting team sizes under either naming convention.

## Setup

Pick an exit square, a tile mix, total supply N, private hand size M, and team sizes G and B. Seat G + B players in a circle with at least one good player. Assign the chosen roles at random, deal M floor tiles to each player and put the remaining tiles in a bag. At least one tile must remain after the deal. Choose a first player before revealing roles. For a reproducible setup, record the realized seating, deal and bag. The bag has no draw order.

**Who knows the roles?** The starting team sizes and this information rule are common knowledge. Everyone knows the rule and knows that everyone else knows it.

- A good player is told their own alignment. They may work out other roles from the public counts or from play.
- Every bad player knows the identities of **all** bad players from setup and therefore knows the alignment of every seat. A bad player with no bad teammates knows everyone else is good.
- Everyone sees which seat is eliminated. Its role stays hidden from the public until game end. Bad players retain their original knowledge of both teams.

Hands are private to their owners.

The floor is a square grid with no boundary. Place START and EXIT at the chosen displacement and put the marker on START. Agree on one coordinate system for the whole table. For an exit four squares east and two north, you can call START (0, 0) and EXIT (4, 2), or call EXIT (0, 0) and START (−4, −2). In the latter convention a marker at (x, y) needs at least |x| + |y| steps to reach EXIT. Arrows and missing tiles can force a longer route or close it entirely. Both special tiles permit entry and exit on all four sides and are outside the supply N. North increases y and east increases x.

## Build

1. Draw two tiles privately and uniformly from the bag without replacement. If it contains one tile, draw it.
2. Place one tile from your hand, either newly drawn or previously held. Choose any quarter-turn rotation. The square must be empty and share an edge with the start or an ordinary placed tile. The exit alone gives no placement rights. The arrows along adjacent edges can disagree. Once placed, a tile keeps its position and rotation.
3. If you drew two, privately choose one remaining tile from your hand and return it to the bag. Returning it makes it eligible on the very next draw. If you drew one, skip this step.

A placement changes the floor. The marker remains on its current square throughout the build. Tile arrows restrict the marker's later step. They impose no matching requirement on placement.

## Move

The builder proposes either staying put or moving one square. For a move east, the current tile needs an outgoing east arrow and the destination an incoming west arrow. Apply the same rule in the other three directions. Movement requires a tile at both ends.

The proposed destination may be an older tile or the one just placed. On a movement ballot, vote to **move the marker** to the named square or **keep the marker here**. A rejected step leaves the newly placed tile on the floor. Staying skips the movement vote. Otherwise all living players, including the builder, cast ballots simultaneously and then reveal them by name. Move on a majority yes. On a tie, use the builder's ballot, which may be no. Reaching the exit ends the game with a good-team win. Otherwise an empty bag at this point ends the game with a bad-team win, even if every bad player has been eliminated.

## Discussion

Everyone knows the discussion rules. When there is time to speak before a ballot, every seat hears each remark and knows who said it. Players on either team may tell the truth, lie, bluff, or stay silent. Players may claim either role. A promised vote leaves the speaker free to vote either way.

A player can check a claim against the public floor and revealed ballots, and against private facts their own seat is entitled to know. Speaking gives nobody an extra way to inspect a hand, reveal a role, or verify an intention. For example, if P1 says “I’m Blue and I voted no last turn,” everyone can check P1’s revealed vote. A Blue listener can weigh the role claim alongside other evidence. A Red listener already knows P1’s team from setup. Both hear exactly the same words.

## Nominate

Starting with the next living player after the builder, go once around the table, builder last. Each surviving player may pass or name one other living player. Resolve each nomination immediately with a simultaneous public vote of all living players, including the nominee. On this ballot, vote to **remove the nominee** or **keep the nominee in play**. Neither choice moves the marker. A strict majority yes eliminates the nominee. A tie fails. Skip eliminated seats for all subsequent decisions. Set their hands aside privately. Roles stay hidden during play.

If the last good player is eliminated, the bad team wins immediately. Otherwise continue even if no bad players remain. When the round ends, the next living seat after the builder becomes the builder. A sole survivor skips nominations. Every member of the winning team shares the result, including eliminated players. Reveal roles at game end.

## Deadlines and solitaire

For timed play announce deadlines before decisions. Mark a missing ballot publicly as timed out and count it as no, including the builder's tie-break. A missed proposal means stay and a missed nomination means pass. A missed required placement or discard triggers a public report of a random choice, with the discarded face still private. The referee samples uniformly among distinct legal commands. A command identifies a face value, and a placement also identifies a square and one of four rotations.

In solitaire, use one good player, accept their legal movement proposals, and skip nomination. A store of S tiles **after dealing** permits exactly S movement opportunities unless the exit is reached earlier. Each build uses one net tile. The start-to-exit Manhattan distance is a lower bound on winning time.

## Reading a floor tile

Face numbers are useful for recording a game. Each face has independent incoming and outgoing permissions in the four compass directions. In either group N, E, S, W have values 1, 2, 4, 8. The face number equals the incoming sum plus 16 times the outgoing sum. Face 40 accepts from the west (8) and exits east (2 × 16). Rotating it clockwise once makes entry north and exit south. The worked game places it between the start and exit. [Worked game](../examples/crossing.md)
