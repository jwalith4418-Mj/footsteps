# Footsteps · base rules 1

A group explores a tiled floor with one shared marker. **Blue wins** when the marker enters EXIT, whoever built the tile, proposed the step or voted for it. **Red wins** if the last movement opportunity ends short of EXIT or all Blue players are eliminated. The win conditions and starting team sizes are public from setup. A player can make a move that helps the other team.

## Setup

Pick an exit square, a tile mix, total supply N, private hand size M, and the number of Blue and Red players. Seat everyone in a circle with at least one Blue player. Assign the chosen roles at random, deal M floor tiles to each player and put the remaining tiles in a bag. At least one tile must remain after the deal. Choose a first player before revealing roles. For a reproducible setup, record the realized seating, deal and bag. The bag has no draw order.

**Who knows the roles?** The starting team sizes and this information rule are common knowledge. Everyone knows the rule and knows that everyone else knows it.

- A Blue player is told their own alignment. They may work out other roles from the public counts or from play.
- Every Red player knows the identities of **all** Red players from setup and therefore knows the alignment of every seat. A Red player with no Red teammates knows everyone else is Blue.
- Everyone sees which seat is eliminated. Its role stays hidden from the public until game end. Red players retain their original knowledge of both teams.

Hands are private to their owners.

The floor is a square grid with no boundary. Place START and EXIT at the chosen displacement and put the marker on START. By default EXIT is (0, 0). For an exit four squares east and two north, START is (−4, −2). A marker at (x, y) needs at least |x| + |y| steps to reach EXIT in this frame. Some historical tables instead put START at (0, 0). Everyone uses the same coordinates throughout a game. Arrows and missing tiles can force a longer route or close it entirely. Both special tiles permit entry and exit on all four sides and are outside the supply N. North increases y and east increases x.

## Build

1. Draw two tiles privately and uniformly from the bag without replacement. If it contains one tile, draw it.
2. Place one tile from your hand, either newly drawn or previously held. Choose any quarter-turn rotation. The square must be empty and share an edge with the start or an ordinary placed tile. The exit alone gives no placement rights. The arrows along adjacent edges can disagree. Once placed, a tile keeps its position and rotation.
3. If you drew two, privately choose one remaining tile from your hand and return it to the bag. Returning it makes it eligible on the very next draw. If you drew one, skip this step.

A placement changes the floor. The marker remains on its current square throughout the build. Tile arrows restrict the marker's later step. They impose no matching requirement on placement.

### Optional placement check

The builder privately names an existing START or ordinary tile O sharing an edge with the new square N. With the chosen tile rotated as submitted, answer “could a marker on O step directly onto N?” Check the outgoing side at O and the facing entrance at N. Some tables also ask “is the actual marker on O now?” Both a blocked edge and a remote origin can be correct answers. If a check fails, the builder gets a private explanation and can retry within the original decision window. An accepted build places only the tile. Movement still requires its later proposal and ballot.

For example, suppose the marker is at (−2, −2) and O is the tile just north, at (−2, −1), with its east side open outward. Place face 58 in printed orientation at (−1, −1). Its west entrance is open, so the edge answer is yes and the marker answer is no. Rotate face 58 clockwise once and the west entrance closes. The same placement square is legal with the edge answer no. No step happens in either case.

## Move

The builder proposes either staying put or moving one square. For a move east, the current tile needs an outgoing east arrow and the destination an incoming west arrow. Apply the same rule in the other three directions. Movement requires a tile at both ends.

The proposed destination may be an older tile or the one just placed. On a movement ballot, vote to **move the marker** to the named square or **keep the marker here**. A rejected step leaves the newly placed tile on the floor. Staying skips the movement vote. Otherwise all living players, including the builder, cast ballots simultaneously and then reveal them by name. Move on a majority yes. On a tie, use the builder's ballot, which may be no. Reaching the exit ends the game with a Blue-team win. Otherwise an empty bag at this point ends the game with a Red-team win, even if every Red player has been eliminated.

At a movement ballot the build is complete. Count the tiles left in the bag to find how many movement opportunities come **after** this one if play continues to depletion. Staying or rejecting the step uses the current opportunity. The bag count stays the same through nominations and removals.

## Discussion

Everyone knows the discussion rules. When there is time to speak before a ballot, every seat hears each remark and knows who said it. Players on either team may tell the truth, lie, bluff, or stay silent. Players may claim either role. A promised vote leaves the speaker free to vote either way.

A player can check a claim against the public floor and revealed ballots, and against private facts their own seat is entitled to know. Speaking gives nobody an extra way to inspect a hand, reveal a role, or verify an intention. For example, if P1 says “I’m Blue and I voted no last turn,” everyone can check P1’s revealed vote. A Blue listener can weigh the role claim alongside other evidence. A Red listener already knows P1’s team from setup. Both hear exactly the same words.

## Nominate

Starting with the next living player after the builder, go once around the table, builder last. Each surviving player may pass or name one other living player for removal. Everyone sees who passed or who nominated whom as soon as the choice is made. Everyone knows this before choosing. Resolve each nomination immediately with a simultaneous public vote of all living players, including the nominee. On this ballot, vote to **remove the nominee** or **keep the nominee in play**. Neither choice moves the marker. Only the voter can see their own submission while voting is open. The table shows everyone each seat’s Yes, No or timeout together when voting closes. A strict majority yes eliminates the nominee. A tie fails. Skip eliminated seats for all subsequent decisions. Set their hands aside privately. Roles stay hidden during play.

If the last Blue player is eliminated, the Red team wins immediately. Otherwise continue, including when Red has a majority of the living seats or no Red players remain. When the round ends, the next living seat after the builder becomes the builder. A sole survivor skips nominations. Every member of the winning team shares the result, including eliminated players. Reveal roles at game end.

## Deadlines and solitaire

For timed play announce deadlines before decisions. As an optional table convention, open voting early once nobody has a speaking opportunity left. For example, with five seconds for discussion and twenty for voting, a final remark at second two opens the ballot immediately and sets its deadline at second twenty-two. If a living player stays silent, voting opens at second five as scheduled. Everyone receives the final remark before voting opens.

Mark a missing ballot publicly as timed out and count it as no, including the builder's tie-break. A missed proposal means stay and a missed nomination means pass. A missed required placement or discard triggers a public report of a random choice, with the discarded face still private. The referee samples uniformly among distinct legal commands. A command identifies a face value, and a placement also identifies a square and one of four rotations.

In solitaire, use one Blue player, accept their legal movement proposals, and skip nomination. A store of S tiles **after dealing** permits exactly S movement opportunities unless the exit is reached earlier. Each build uses one net tile. The start-to-exit Manhattan distance is a lower bound on winning time.

## Reading a floor tile

Face numbers are useful for recording a game. Each face has independent incoming and outgoing permissions in the four compass directions. In either group N, E, S, W have values 1, 2, 4, 8. The face number equals the incoming sum plus 16 times the outgoing sum. Face 40 accepts from the west (8) and exits east (2 × 16). Rotating it clockwise once makes entry north and exit south. The worked game places it between the start and exit. [Worked game](../examples/crossing.md)
