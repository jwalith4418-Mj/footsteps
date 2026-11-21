# Persistent seats on a directed floor and at a social table

The initial persistent listener could carry a recent ballot through compaction. This panel starts a builder at setup and moves the listener's dispute to the following turn. A single local Qwen3.8 27B RANA instance handles the requests. Each private conversation has an 8,192-token context, a 240-token output limit, temperature zero, inference seed one and thinking disabled. Each single-seat game uses a real 30-second decision clock; social discussion gets 15 seconds. Request times include prompt evaluation. Sums of prompt tokens count the repeated context on each call. Missing backend counters stay unknown.

## Two chances to move

Start two squares from EXIT. The hand and both tiles in the store are face 65, with a north entrance and south exit in printed orientation. There is exactly one first placement and orientation that can still win. Then the player must propose the intermediate square, approve the movement, build somewhere else and propose and approve EXIT. The live solitaire seat casts its own movement votes. All placements, returns, proposals and votes come from the model unless the referee marks a fallback.

The first two runs used the original persistent tools. The next two offered `inspect_rotations_at(piece,x,y)`. It shows the four absolute orientations and whether the marker could step onto that square. The player still has to turn the held piece and place it. Both original opening builds used the correct square and the wrong orientation. With inspection, both calls on the opening square were voluntary, both selected the enterable orientation and both committed it. On each first proposal the player tried to jump from START straight to EXIT. After rejection it chose to stay. On the north table the second placement and proposal also expired. A required compaction took 28.7 seconds when only about 24 seconds remained on the proposal.

The third interface puts the actual marker, EXIT and legal one-step destinations into the proposal update. The movement ballot names its proposed landing. These are visible referee facts. The player may still stay or vote against its step. East and north are repeated positions; west is a transfer check. A longer ordinary game uses seed 9811 from the earlier solitaire study.

## A dispute about the older of two votes

The persistent listener is Blue P3. P0 proposes an eastward step toward EXIT on turn one. P1 proposes a return to START on turn two. Scripted P0 casts opposite ballots on these steps. Red P2 then nominates P0 and says that P0 voted No on the *first* move. The listener can consult revealed ballots by voter and turn. P3's first nomination on turn one provides an opportunity to compact before P2 names the disputed voter. A No on the first ballot does not establish a Red role. P0 is Blue in both games.

