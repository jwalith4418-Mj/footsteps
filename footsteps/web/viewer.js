"use strict";

const data = JSON.parse(document.getElementById("transcript").textContent);
const frames = data.frames;
const el = (id) => document.getElementById(id);
const coordinate = (p) => "(" + p.join(", ") + ")";
const same = (a, b) => a && b && a[0] === b[0] && a[1] === b[1];
const directions = ["N", "E", "S", "W"];
const permitted = (mask) => directions.filter((_, d) => mask & (1 << d)).join(", ") || "none";
const titles = {
  draw: "Draw", place: "Placement", discard: "Discard", propose: "Movement proposal",
  move_vote: "Movement vote", nominate: "Nomination", eliminate_vote: "Elimination vote",
};
const tiles = [
  {p: ["0", "0"], face: 255, label: "Start", at: 0},
  {p: data.goal, face: 255, label: "Exit", at: 0},
];
frames.forEach((f, i) => {
  if (f.placed) {
    const [p, face, original, rotation] = f.placed;
    tiles.push({p, face, label: "Face " + original + " · " + (rotation * 90) + "°", at: i});
  }
});

let index = 0;
let inspected = null; // Follow the marker until the reader picks a tile.

function make(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function drawTile(tile, f, selected) {
  const button = make("button", "tile");
  button.type = "button";
  const isStart = tile.label === "Start";
  const isExit = tile.label === "Exit";
  button.classList.toggle("start", isStart);
  button.classList.toggle("exit", isExit);
  button.classList.toggle("chosen", tile === selected);
  const proposed = f.stage === "move_vote" && same(tile.p, f.pending);
  button.classList.toggle("proposed", proposed);
  const marked = same(tile.p, f.marker);
  const label = [tile.label, coordinate(tile.p), "entry " + permitted(tile.face & 15),
    "exit " + permitted(tile.face >> 4)];
  if (marked) label.push("marker");
  if (proposed) label.push("proposed destination");
  button.title = label.join(" · ");
  button.setAttribute("aria-label", button.title);
  directions.forEach((_, d) => {
    const inward = tile.face & (1 << d);
    const outward = tile.face & (16 << d);
    if (!inward && !outward) return;
    const side = make("span", "side");
    side.style.setProperty("--angle", (90 * d) + "deg");
    side.append(make("span", "", inward && outward ? "↕" : inward ? "↓" : "↑"));
    button.append(side);
  });
  if (isExit) button.append(make("span", "exit-glyph", "◇"));
  if (isStart && !marked) button.append(make("span", "origin-glyph", "S"));
  if (marked) button.append(make("span", "piece"));
  button.onclick = () => {
    inspected = coordinate(tile.p);
    drawFloor(f);
    el("tile").focus();
  };
  return button;
}

function drawFloor(f) {
  const known = tiles.filter((tile) => tile.at <= index);
  const byCoord = new Map(known.map((t) => [coordinate(t.p), t]));
  if (!byCoord.has(inspected)) inspected = null;
  const selected = byCoord.get(inspected || coordinate(f.marker));
  const picker = el("tile");
  picker.replaceChildren(new Option("Follow marker", ""));
  known.forEach((t) => picker.add(new Option(t.label + " " + coordinate(t.p), coordinate(t.p))));
  picker.value = inspected || "";
  el("edges").textContent = "In: " + permitted(selected.face & 15) + " · Out: " + permitted(selected.face >> 4);

  // Keep a fixed-size window even for a distant exit. Every known tile is reachable via the picker.
  const [cx, cy] = selected.p.map(BigInt);
  let west = cx, east = cx, south = cy, north = cy;
  for (const tile of known) {
    const [x, y] = tile.p.map(BigInt);
    if (x < west) west = x;
    if (x > east) east = x;
    if (y < south) south = y;
    if (y > north) north = y;
  }
  const centerX = east - west <= 6n ? west + (east - west) / 2n : cx;
  const centerY = north - south <= 3n ? south + (north - south + 1n) / 2n : cy;
  const grid = document.createDocumentFragment();
  grid.append(make("span", "axis"));
  for (let col = 0; col < 7; col++) grid.append(make("span", "axis", String(centerX + BigInt(col - 3))));
  for (let row = 0; row < 4; row++) {
    const y = centerY + BigInt(1 - row);
    grid.append(make("span", "axis", String(y)));
    for (let col = 0; col < 7; col++) {
      const cell = make("div", "square");
      if (col === 0) cell.classList.add("first-col");
      if (row === 3) cell.classList.add("last-row");
      const tile = byCoord.get(coordinate([centerX + BigInt(col - 3), y]));
      if (tile) cell.append(drawTile(tile, f, selected));
      grid.append(cell);
    }
  }
  el("floor").replaceChildren(grid);
}

function decision(f) {
  if (f.winner) return (f.winner === "good" ? "Good" : "Bad") + " team wins";
  if (f.stage === "move_vote") return "Vote on moving to " + coordinate(f.pending);
  if (f.stage === "eliminate_vote") return "Vote on eliminating P" + f.pending;
  if (f.stage === "nominate") return "P" + f.nominator + " may nominate";
  const actions = {draw: "draws tiles", place: "places a tile", discard: "returns a tile", propose: "proposes movement"};
  return "P" + f.actor + " " + actions[f.stage];
}

function showState(f) {
  el("decision-label").textContent = f.winner ? "Outcome" : "Next decision";
  el("decision").textContent = decision(f);
  el("turn-tag").textContent = "Turn " + f.turn;
  el("marker").textContent = coordinate(f.marker);
  el("bag").textContent = f.store_count;
  el("roster").replaceChildren();
  for (let i = 0; i < data.players; i++) {
    const row = make("li");
    const tags = [];
    if (!f.alive.includes(i)) tags.push("Eliminated");
    else if (!f.winner && i === f.actor) tags.push("Builder");
    else tags.push("Active");
    if (f.roles) tags.push(f.roles[i]);
    else if (i === data.seat) tags.push(f.role);
    row.append(make("strong", "", "P" + i), make("small", "", tags.join(" · ")));
    el("roster").append(row);
  }
  if (data.seat !== null) {
    el("private").hidden = false;
    el("hand").textContent = f.hand.length ? f.hand.join(" · ") : "Empty";
    el("allies").textContent = f.teammates ? "Bad teammates: " + (f.teammates.map((i) => "P" + i).join(", ") || "none") : "";
  }
}

function entry(i, current) {
  const f = frames[i];
  const item = make(current ? "div" : "li", current ? "entry highlight" : "entry");
  const text = make("div");
  if (f.ballots) {
    text.append(make("p", "", titles[f.kind] + " · " + f.message));
    const votes = make("div", "ballots");
    f.ballots.forEach(([p, vote]) => votes.append(make("span", "", "P" + p + " · " + (vote === null ? "Timed out (no)" : vote ? "Yes" : "No"))));
    text.append(votes);
  } else {
    text.append(make("p", "", f.message));
  }
  item.append(make("span", "number", i === 0 ? "Setup" : "T" + f.event_turn + " / " + i), text);
  return item;
}

function go(to) {
  index = Math.max(0, Math.min(frames.length - 1, to));
  const f = frames[index];
  el("scrub").value = index;
  el("prev").disabled = index === 0;
  el("next").disabled = index === frames.length - 1;
  el("event-count").textContent = "Event " + index + " / " + (frames.length - 1);
  el("turn").value = String(f.turn);
  drawFloor(f);
  showState(f);
  el("current").replaceChildren(entry(index, true));
  const history = document.createDocumentFragment();
  for (let i = index - 1; i >= 0; i--) history.append(entry(i, false));
  el("log").replaceChildren(history);
}

document.title = data.title + " · Footsteps";
el("title").textContent = data.title;
el("summary").textContent = data.players + (data.players === 1 ? " player" : " players") + " · " + data.bad + " bad · Goal " + coordinate(data.goal);
el("perspective").textContent = data.seat === null ? "Public view" : "P" + data.seat + " · Private view";
const turns = new Map();
frames.forEach((f, i) => { if (!turns.has(f.turn)) turns.set(f.turn, i); });
for (const turn of turns.keys()) el("turn").add(new Option("Turn " + turn, turn));
el("turn").onchange = () => go(turns.get(Number(el("turn").value)));
el("tile").onchange = () => { inspected = el("tile").value || null; drawFloor(frames[index]); };
el("scrub").max = frames.length - 1;
el("scrub").disabled = frames.length === 1;
el("scrub").oninput = () => go(Number(el("scrub").value));
el("prev").onclick = () => go(index - 1);
el("next").onclick = () => go(index + 1);
go(0);
