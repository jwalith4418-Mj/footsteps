"""Exercise the generated page in an actual browser, with a disposable user profile."""

import json
import shutil
import subprocess
import tempfile
import unittest
from html import unescape
from pathlib import Path

from footsteps.record import read
from footsteps.viewer import export_html

CHROME = shutil.which("google-chrome") or shutil.which("chromium")
EXAMPLE = Path(__file__).resolve().parents[1] / "examples/crossing.json"


@unittest.skipUnless(CHROME, "install Chrome or Chromium for the offline viewer interaction test")
class OfflineViewer(unittest.TestCase):
    def test_hand_ballots_and_floor_follow_playback_in_both_directions(self):
        document = export_html(read(EXAMPLE), "Crossing", seat=0)
        # Drive public controls, then return observations from the rendered page.
        observe = """
<script>
const find = selector => document.querySelector(selector);
const next = () => find("#next").click();
const hand = () => document.querySelectorAll(".hand-card").length;
const seen = {setup: hand()};
next();
seen.draw = hand();
next(); next(); next();
seen.proposed = find(".tile.proposed").title;
next();
seen.ballot = find("#current").textContent;
seen.marker = find("#marker").textContent;
find("#turn").value = "2";
find("#turn").dispatchEvent(new Event("change"));
seen.turn = find("#turn-tag").textContent;
const scrub = find("#scrub");
scrub.value = scrub.max;
scrub.dispatchEvent(new Event("input"));
seen.outcome = find("#decision").textContent;
scrub.value = "0";
scrub.dispatchEvent(new Event("input"));
seen.rewind = [hand(), find("#marker").textContent, find("#prev").disabled,
               document.querySelectorAll(".tile").length];
const result = document.createElement("pre");
result.id = "observations";
result.textContent = JSON.stringify(seen);
document.body.replaceChildren(result);
</script>"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "crossing.html"
            page.write_text(document.replace("</body>", observe + "</body>"))
            proc = subprocess.run(
                [
                    CHROME,
                    "--headless",
                    "--disable-background-networking",
                    "--no-first-run",
                    f"--user-data-dir={root / 'profile'}",
                    "--dump-dom",
                    page.as_uri(),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
        _, found, text = proc.stdout.partition('<pre id="observations">')
        self.assertTrue(found, "the browser did not finish the playback sequence")
        obs = json.loads(unescape(text.split("</pre>", 1)[0]))
        self.assertEqual((obs["setup"], obs["draw"]), (1, 3))
        self.assertIn("(1, 0)", obs["proposed"])
        self.assertIn("Timed out (no)", obs["ballot"])
        self.assertEqual((obs["marker"], obs["turn"]), ("(1, 0)", "Turn 2"))
        self.assertEqual(obs["outcome"], "Good team wins")
        self.assertEqual(obs["rewind"], [1, "(0, 0)", True, 2])

    def test_arrow_keys_step_events_and_keep_focus_usable(self):
        document = export_html(read(EXAMPLE), "Crossing", seat=0)
        observe = """
<script>
const find = selector => document.querySelector(selector);
const press = (key, options = {}) => document.activeElement.dispatchEvent(
  new KeyboardEvent("keydown", {key, bubbles: true, cancelable: true, ...options})
);
const focusId = () => {
  const active = document.activeElement;
  return active && active.dataset && active.dataset.coord ? "tile:" + active.dataset.coord
    : active && active.id ? active.id : "none";
};
const seen = {};
// Reach event 4 (the pending proposal) with the existing controls.
for (let i = 0; i < 4; i++) find("#next").click();
seen.at4 = [find("#marker").textContent, !!find(".tile.proposed")];
seen.modified = [press("ArrowLeft", {altKey: true}), find("#scrub").value];
press("ArrowRight");
seen.right = [find("#current").textContent, find("#marker").textContent];
press("ArrowLeft");
seen.left = [find("#marker").textContent, !!find(".tile.proposed")];
// Endpoints: stepping past the first or last event is a no-op.
find("#scrub").value = "0";
find("#scrub").dispatchEvent(new Event("input"));
press("ArrowLeft");
seen.first = [find("#event-count").textContent, find("#prev").disabled];
find("#scrub").value = find("#scrub").max;
find("#scrub").dispatchEvent(new Event("input"));
press("ArrowRight");
seen.last = [find("#event-count").textContent, find("#next").disabled];
// A focused floor tile keeps its focus while the tile still exists.
find("#scrub").value = "4";
find("#scrub").dispatchEvent(new Event("input"));
find('.tile[data-coord="(1, 0)"]').focus();
press("ArrowRight");
seen.tileForward = focusId();
press("ArrowLeft");
seen.tileBack = focusId();
// Step back three events: the placed tile vanishes at event 1, so focus
// must land on a usable playback or inspection control.
press("ArrowLeft");
seen.tileGone1 = focusId();
press("ArrowLeft");
seen.tileGone2 = focusId();
press("ArrowLeft");
seen.tileGone3 = focusId();
// A focused playback button that becomes disabled yields to a usable control.
find("#prev").focus();
press("ArrowLeft");
seen.disabledPrev = [find("#event-count").textContent, focusId()];
// Synthetic keys have no native default action. Each control must leave the key
// unconsumed and the event index untouched so the browser can handle it.
seen.native = ["scrub", "turn", "tile"].map(id => {
  find("#" + id).focus();
  return [press("ArrowRight"), find("#scrub").value, document.activeElement.id];
});
const result = document.createElement("pre");
result.id = "observations";
result.textContent = JSON.stringify(seen);
document.body.replaceChildren(result);
</script>"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "crossing.html"
            page.write_text(document.replace("</body>", observe + "</body>"))
            proc = subprocess.run(
                [
                    CHROME,
                    "--headless",
                    "--disable-background-networking",
                    "--no-first-run",
                    f"--user-data-dir={root / 'profile'}",
                    "--dump-dom",
                    page.as_uri(),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
        _, found, text = proc.stdout.partition('<pre id="observations">')
        self.assertTrue(found, "the browser did not finish the arrow-key sequence")
        obs = json.loads(unescape(text.split("</pre>", 1)[0]))
        self.assertEqual(obs["at4"], ["(0, 0)", True])
        self.assertIn("Timed out (no)", obs["right"][0])
        self.assertEqual(obs["right"][1], "(1, 0)")
        self.assertEqual(obs["left"], ["(0, 0)", True])
        self.assertEqual(obs["first"], ["Event 0 / 13", True])
        self.assertEqual(obs["last"], ["Event 13 / 13", True])
        self.assertEqual(obs["tileForward"], "tile:(1, 0)")
        self.assertEqual(obs["tileBack"], "tile:(1, 0)")
        self.assertEqual(obs["tileGone1"], "tile:(1, 0)")
        self.assertEqual(obs["tileGone2"], "tile:(1, 0)")
        self.assertNotIn(obs["tileGone3"], ("tile:(1, 0)", "none"))
        self.assertEqual(obs["disabledPrev"], ["Event 0 / 13", "next"])
        self.assertEqual(obs["modified"], [True, "4"])
        self.assertEqual(obs["native"], [[True, "0", key] for key in ("scrub", "turn", "tile")])
