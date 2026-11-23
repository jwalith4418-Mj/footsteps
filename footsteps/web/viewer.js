"use strict";

const data = JSON.parse(document.getElementById("transcript").textContent);
const frames = data.frames;
const teamName = (role) => role[0].toUpperCase() + role.slice(1);
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
  {p: data.start, face: 255, label: "Start", at: 0},
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

function drawEdges(element, face) {
  directions.forEach((_, d) => {
    const inward = face & (1 << d);
    const outward = face & (16 << d);
    if (!inward && !outward) return;
    const side = make("span", "side");
    side.style.setProperty("--angle", (90 * d) + "deg");
    side.append(make("span", "", inward && outward ? "↕" : inward ? "↓" : "↑"));
    element.append(side);
  });
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
  button.dataset.coord = coordinate(tile.p);
  drawEdges(button, tile.face);
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
  if (f.winner) return teamName(f.winner) + " team wins";
  if (f.stage === "move_vote") return "Vote on moving to " + coordinate(f.pending);
  if (f.stage === "eliminate_vote") return "Vote on eliminating P" + f.pending;
  if (f.stage === "nominate") return "P" + f.nominator + " may nominate";
  const actions = {draw: "draws tiles", place: "places a tile", discard: "returns a tile", propose: "proposes movement"};
  return "P" + f.actor + " " + actions[f.stage];
}

function handGroup(seat, hand, alive) {
  const group = make("section", "hand-group");
  const label = "P" + seat + (alive ? "" : " · Set aside");
  group.append(make("h3", "", label));
  if (!hand.length) {
    group.append(make("p", "", "Empty hand"));
    return group;
  }
  const list = make("ul", "hand-tiles");
  for (const face of hand) {
    const card = make("li", "hand-card");
    const tile = make("span", "hand-face", String(face));
    tile.setAttribute("aria-hidden", "true");
    drawEdges(tile, face);
    const edges = make("span", "hand-edges");
    edges.append(make("span", "sr", "Face " + face + ". "),
      make("span", "", "In: " + permitted(face & 15)),
      make("span", "", "Out: " + permitted(face >> 4)));
    card.append(tile, edges);
    list.append(card);
  }
  group.append(list);
  return group;
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
    if (f.roles) tags.push(teamName(f.roles[i]));
    else if (i === data.seat) tags.push(teamName(f.role));
    row.append(make("strong", "", "P" + i), make("small", "", tags.join(" · ")));
    el("roster").append(row);
  }
  if (data.omniscient || data.seat !== null) {
    el("private").hidden = false;
    el("hand-heading").textContent = data.omniscient ? "All hands" : "Your hand";
    const hands = data.omniscient
      ? f.hands.map((hand, seat) => handGroup(seat, hand, f.alive.includes(seat)))
      : [handGroup(data.seat, f.hand, f.alive.includes(data.seat))];
    el("hand").replaceChildren(...hands);
  }
  if (f.teammates) {
    el("allies").hidden = false;
    el("allies").textContent = "Red" + " teammates: " + (f.teammates.map((i) => "P" + i).join(", ") || "none");
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
  if (f.remarks) {
    for (const remark of f.remarks) {
      const line = make("p");
      line.append(make("strong", "", "P" + remark.seat + " · Public remark "),
        document.createTextNode(remark.text));
      text.append(line);
    }
  }
  if (f.hand_rotations) {
    const details = make("details", "decision-notes");
    details.open = current;
    details.append(make("summary", "", "Private hand rotations (" + f.hand_rotations.length + ")"));
    for (const r of f.hand_rotations) {
      details.append(make("p", "", "P" + r.seat + " turned " + r.piece + " (face " + r.face +
        ") from " + (90 * r.from) + "° to " + (90 * r.to) + "° clockwise from print."));
    }
    text.append(details);
  }
  for (const [traces, prefix] of [[f.thinking_traces, ""], [f.pending_thinking_traces, "Pending decision · "]]) {
    for (const trace of traces || []) {
      const details = make("details", "decision-notes");
      details.append(make("summary", "", prefix + "P" + trace.seat + " · " + trace.model + " · " + trace.label));
      details.append(make("pre", "thinking-trace", trace.thinking || "No thinking text returned."));
      text.append(details);
    }
  }
  if (f.decision_notes) {
    const details = make("details", "decision-notes");
    details.open = current;
    details.append(make("summary", "", "Private model notes (" + f.decision_notes.length + ")"));
    for (const note of f.decision_notes) {
      const line = make("p");
      line.append(make("strong", "", "P" + note.seat + " · " + note.model + " "));
      line.append(document.createTextNode(note.reason || "No explanation supplied."));
      for (const tool of note.tools || []) {
        const face = Number.isInteger(tool.tile) ? " · face " + tool.tile : "";
        const piece = tool.piece ? " " + tool.piece : "";
        const at = tool.at ? " at (" + tool.at.join(", ") + ")" : "";
        const rotation = Number.isInteger(tool.rotation) ? " · " + (90 * tool.rotation) + "°" : "";
        const step = typeof tool.can_step_here === "boolean" ? (tool.can_step_here ? " · marker can enter" : " · no direct step") : "";
        line.append(make("small", "", tool.name + piece + face + rotation + at + " · " + (tool.status || (tool.ok ? "answered" : "error")) + step));
      }
      details.append(line);
      if (!note.matches) {
        details.append(make("p", "", "Attempt differed from the recorded event: " + JSON.stringify(note.choice)));
      }
    }
    text.append(details);
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

function fallbackFocus() {
  for (const control of [el("prev"), el("next"), el("scrub"), el("turn"), el("tile")]) {
    if (control && !control.disabled) {
      control.focus();
      return;
    }
  }
}

function restoreFocus(active) {
  if (!active) return;
  if (active.classList && active.classList.contains("tile")) {
    // The floor is redrawn on every step; keep the same tile focused while it exists.
    const still = document.querySelector('.tile[data-coord="' + active.dataset.coord + '"]');
    if (still) {
      still.focus();
      return;
    }
    fallbackFocus();
    return;
  }
  if (!active.isConnected) {
    fallbackFocus();
    return;
  }
  if ((active.id === "prev" || active.id === "next") && active.disabled) fallbackFocus();
}

function step(dir) {
  const active = document.activeElement;
  go(index + dir);
  restoreFocus(active);
}

// Arrow keys step the transcript; form controls keep their native arrow-key behavior.
document.addEventListener("keydown", (event) => {
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || event.defaultPrevented) return;
  if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
  const active = document.activeElement;
  if (active && /^(INPUT|SELECT|TEXTAREA)$/.test(active.tagName)) return;
  event.preventDefault();
  step(event.key === "ArrowLeft" ? -1 : 1);
});

document.title = data.title + " · Footsteps";
el("title").textContent = data.title;
el("summary").textContent = data.players + (data.players === 1 ? " player" : " players") + " · " + data.red + " " + teamName("red") + " · Goal " + coordinate(data.goal);
el("perspective").textContent = data.omniscient ? "Omniscient · All hands and roles" : data.seat === null ? "Public view" : "P" + data.seat + " · Private view";
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
const linkedEvent = /^#event=([0-9]+)$/.exec(location.hash);
go(linkedEvent ? Number(linkedEvent[1]) : 0);
