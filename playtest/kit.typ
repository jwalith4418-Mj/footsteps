#set document(title: "Footsteps • Four-seat paper playtest", author: "Footsteps contributors")
#set page(width: 200mm, height: 255mm, margin: (x: 13mm, y: 12mm),
  footer: context align(right, text(size: 8pt)[Footsteps · Paper trial 1 · #counter(page).display() / 3]))
#set text(font: "Libertinus Serif", size: 11pt)
#set par(leading: .48em)
#let faces = (188, 153, 16, 71, 45, 91, 121, 41, 234, 12, 44, 16, 74, 107, 41, 182)
#let edge = .6pt + black
#let size = 32mm
#let heading(body) = text(size: 22pt, weight: "bold", body)
#let subtitle(body) = text(size: 13pt, weight: "bold", body)
#let square(body) = block(width: size, height: size, stroke: edge, inset: 0pt, body)
#let cell(face, name: none) = square({
  let ins = calc.rem(face, 16)
  let outs = calc.div-euclid(face, 16)
  let locations = (center + top, right + horizon, center + bottom, left + horizon)
  let inward = ("↓", "←", "↑", "→")
  let outward = ("↑", "→", "↓", "←")
  let both = ("↕", "↔", "↕", "↔")
  for d in range(4) {
    let bit = calc.pow(2, d)
    let accepts = calc.odd(calc.div-euclid(ins, bit))
    let sends = calc.odd(calc.div-euclid(outs, bit))
    let arrow = if accepts and sends { both.at(d) } else if accepts { inward.at(d) } else if sends { outward.at(d) } else { "" }
    place(locations.at(d), pad(1.2mm, text(font: "DejaVu Sans", size: 17pt, arrow)))
  }
  place(center + horizon, text(weight: "bold", size: 12pt, if name == none { str(face) } else { name }))
})
#let card(w, h, body) = block(width: w, height: h, stroke: edge, inset: 2mm, align(center + horizon, body))
#let four = range(4)

#heading[Floor tiles]
#par[Print all three pages single-sided at *100% / actual size* on Letter or A4. Use opaque stock or glue to identical opaque backing before cutting. Each square below should measure 32 mm on a side.]
#align(center, grid(columns: (size,) * 4, gutter: 0pt, ..faces.map(f => cell(f))))
#v(3mm)
#align(center, grid(columns: (size,) * 4, gutter: 0pt,
  cell(255, name: "START"), cell(255, name: "EXIT"),
  card(size, size, circle(radius: 6mm, stroke: edge, inset: 0pt, align(center + horizon, [●]))), card(size, size, [N ↑ \ Table north])))
#v(2mm)
#par[*Bag only the first sixteen tiles.* Keep the four pieces on the bottom row separate. Cut out the small round marker or use a coin. The north card stays beside the floor.]
#par[An arrow pointing into a tile permits entry from that edge. One pointing out permits departure. A double arrow permits both. A blank edge permits neither. Check both touching edges before proposing a step.]
#pagebreak()

#heading[Seats, roles and ballots]
#par[Cut along the lines. Keep seat signs visible. Shuffle the four role cards face down and deal one privately to each seat. Read yours privately. This kit has one bad player, so no teammate recognition step is needed.]
#align(center, grid(columns: (39mm,) * 4, gutter: 0pt,
  ..four.map(i => card(39mm, 18mm, text(weight: "bold")[SEAT P#i])),
  ..("GOOD", "GOOD", "GOOD", "BAD").map(role => card(39mm, 25mm, [Role \ #text(size: 15pt, weight: "bold", role)]))))
#v(4mm)
#align(center, grid(columns: (39mm,) * 4, gutter: 0pt,
  ..("YES", "NO").map(vote => four.map(i => card(39mm, 23mm, [P#i \ #text(size: 15pt, weight: "bold", vote)]))).flatten()))
#v(3mm)
#subtitle[Set up the floor]
#par[Choose P0 before roles are seen. Seat P1–P3 clockwise from P0. Put the marker on START. Put EXIT four tile widths east and two north of START, measuring center to center. Reserve the empty squares in between. Give each player two random floor tiles behind a screen. Keep the other eight in an opaque bag. Books or folded sheets make good screens.]
#subtitle[Commit and reveal a ballot]
#par[Each living player puts one named ballot face down in front of them. Keep the unused ballot concealed. Reveal together once all have committed. Announce each response by seat. If playing with deadlines, record a missed ballot as timed out and count it as no. Retrieve both ballots privately before the next vote.]
#subtitle[Win conditions]
#par[Good wins immediately on reaching EXIT. Bad wins if the bag is empty after movement and the marker has missed EXIT, or the last good player is eliminated. Eliminated players share their team’s result. Reveal roles at the end.]
#pagebreak()

#heading[Run and observe the trial]
#par[*Build.* The builder draws two tiles behind their screen. Place one tile from the whole hand with any quarter-turn rotation on an empty square touching START or an ordinary tile along an edge. EXIT alone gives no placement rights. Keep existing tiles fixed. Privately return one other tile to the bag and mix it well. On the last draw, take the single tile, place one from hand and skip the return.]
#par[*Move.* The builder proposes one legal step or staying put. Staying skips the vote. Otherwise reveal ballots together. A majority yes moves the marker. On a tie use the builder’s ballot, which can be no. Check the exit and bag win conditions now.]
#par[*Nominate.* Starting after the builder and ending with the builder, each surviving seat may pass or nominate one other living player. All living players, including the nominee, vote. Only a strict majority yes eliminates. Set that hand aside face down, keep the role hidden, and skip the seat thereafter. If at least one good player survives, continue even if every bad player is out. After nominations the next living seat after the builder builds.]
#par[*First trial.* Play untimed. Keep discussion to one trip around the table before a disputed ballot. Everyone hears each remark. Either team may tell the truth, bluff, or stay silent. Check claims using the public record and your own private information.]
#subtitle[Observer notes]
#par[Session / date #box(line(length: 38mm))  End turn #box(line(length: 12mm))  Winning team #box(line(length: 20mm))]
#for prompt in (
  "First disputed edge. Which turn, coordinates and rotation? What did the players read?",
  "First nomination. Which public action did the nominator cite? How far was EXIT?",
  "Any reveal of a private return or early ballot? Where did handling break down?",
  "Which seat sat out, for how many turns? What needed a moderator ruling?",
) [
  #text(size: 10pt, weight: "bold", prompt) \
  #v(3mm)
  #line(length: 100%, stroke: .35pt + gray)
  #v(3mm)
  #line(length: 100%, stroke: .35pt + gray)
]
#par[Record public placements, proposals, revealed ballots and eliminations. A public observer cannot reconstruct private draws and returns. For a full referee record, arrange private notes with all players in advance and collect them after play.]
#text(size: 8pt)[Daniel Klein and Footsteps contributors · Original game materials, CC BY 4.0 · creativecommons.org/licenses/by/4.0/]
