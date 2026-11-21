import json
import unittest
from pathlib import Path
from random import Random

from footsteps.record import read
from footsteps.session import Session
from footsteps.table import Table

CROSSING = read(Path(__file__).resolve().parents[1] / "examples/crossing.json")


class ProjectedSeat:
    """JSON transport with an explicit test clock and no access to other seat links."""

    def __init__(self, table, seat):
        self.table, self.seat, self.now = table, seat, 0

    def call(self, path, data=None):
        if path == "/choice":
            self.table.submit(self.seat, data["revision"], data["choice"], self.now)
        return json.loads(json.dumps(self.table.view(self.seat, self.now, structured_history=True)))


class PersistentSeat(unittest.TestCase):
    def test_sealed_wait_and_recovery_across_turns(self):
        t = Table(CROSSING["setup"], Random(1), seconds=30, discussion=5)
        for i in range(4):
            t.join(i, 0)
        peer = ProjectedSeat(t, 2)
        session = Session(peer)

        def call(name, **args):
            return session.execute(name, args, session.tools(), session.snap["revision"])

        for e in CROSSING["events"][1:4]:
            t.submit(0, t.revision, {k: v for k, v in e.items() if k != "kind"}, 0)
        session.refresh()
        cursor = session.cursor
        t.say(1, t.revision, "I will vote No.", 0)
        result = call("wait", after_cursor=cursor)
        self.assertGreater(result["cursor"], cursor)
        self.assertEqual(result["latest"][0]["speaker"], 1)
        cursor = session.cursor
        session.sleep = lambda _: setattr(peer, "now", 5)
        self.assertTrue(call("wait", after_cursor=cursor)["owe_action"])
        cursor = session.cursor
        t.submit(1, t.revision, {"vote": True}, 5)
        session.refresh()
        self.assertEqual(session.cursor, cursor)
        self.assertEqual(call("history", kind="move_vote")["entries"], [])
        for i in (0, 3):
            t.submit(i, t.revision, {"vote": True}, 5)
        self.assertTrue(call("vote_move", approve=True)["accepted"])
        t.submit(1, t.revision, {"target": 3}, 5)
        t.say(1, t.revision, "P3 voted No. Remove P3.", 5)
        session.refresh()
        statement = call("history", kind="remark", speaker=1, limit=1)["entries"][0]
        vote = call("history", kind="move_vote", voter=3)["entries"][0]
        self.assertTrue(vote["requested_ballot"])
        self.assertLess(vote["id"], statement["id"])
        self.assertNotIn("18", call("history", kind="draw")["entries"][0]["text"])
        self.assertNotIn("red_teammates", call("get_role"))
        self.assertTrue(
            call("compact", summary="P1 accused P3; the public ballot contradicts P1.")["compacted"]
        )
        self.assertEqual(len(session.messages), 2)
        self.assertIn("public ballot contradicts", session.messages[-1]["content"])
        self.assertNotIn("tool_calls", str(session.messages))
        peer.now = 10
        session.refresh()
        call("vote_removal", approve=False)
        for i in (0, 1, 3):
            t.submit(i, t.revision, {"vote": False}, 10)
        while t.game.stage == "nominate":
            t.submit(t.game.queue[0], t.revision, {"target": None}, 10)
        session.refresh()
        self.assertEqual(session.snap["state"]["turn"], 2)
        self.assertEqual(call("history", after=vote["id"], kind="remark")["entries"], [statement])
        self.assertEqual(
            call("history", before=statement["id"], kind="move_vote", voter=3)["entries"], [vote]
        )

    def test_hidden_ballot_during_wait_only_wakes_at_public_reveal(self):
        t = Table(CROSSING["setup"], Random(1), seconds=30, discussion=0)
        for i in range(4):
            t.join(i, 0)
        for e in CROSSING["events"][1:4]:
            t.submit(0, t.revision, {k: v for k, v in e.items() if k != "kind"}, 0)
        peer = ProjectedSeat(t, 2)
        polls = []

        def advance(_):
            polls.append(peer.now)
            if len(polls) == 1:
                t.submit(0, t.revision, {"vote": True}, 0)
            else:
                peer.now = 30

        session = Session(peer, sleep=advance)
        cursor = session.cursor
        session.wait(cursor)
        self.assertEqual(len(polls), 2)
        self.assertEqual(session.cursor, cursor + 1)
        row = session.execute(
            "history", {"kind": "move_vote", "voter": 3}, session.tools(), t.revision
        )
        self.assertIsNone(row["entries"][0]["requested_ballot"])
        self.assertTrue(row["entries"][0]["ballots"]["0"])

    def test_late_reply_cannot_commit_at_new_revision(self):
        t = Table(CROSSING["setup"], Random(1), seconds=10, discussion=0)
        for i in range(4):
            t.join(i, 0)
        peer = ProjectedSeat(t, 0)
        session = Session(peer)

        def answer(*_):
            peer.now = 10
            return {
                "message": {
                    "tool_calls": [
                        {
                            "function": {
                                "name": "place_tile",
                                "arguments": {"piece": "H1", "x": 1, "y": 0},
                            }
                        }
                    ]
                }
            }

        row = session.step("script", infer=answer)
        self.assertIn("changed", row["result"]["error"])
        self.assertTrue(t.record["events"][-1]["timeout"])
        self.assertEqual(t.game.stage, "discard")

    def test_model_compaction_discards_old_exchange_and_preserves_authority(self):
        t = Table(CROSSING["setup"], Random(1))
        peer = ProjectedSeat(t, 3)
        session = Session(peer)
        names = iter(["get_role", "compact", "get_state"])

        def answer(_port, _path, body, _budget):
            name = next(names)
            offered = [s["function"]["name"] for s in body["tools"]]
            if name == "compact":
                self.assertEqual(offered, ["compact"])
            if name == "get_state":
                self.assertEqual(len(body["messages"]), 3)
                current = json.loads(body["messages"][1]["content"])
                self.assertEqual(current["your_identity"]["team"], "red")
                self.assertEqual(current["your_private_player_authored_summary"], "I suspect P0.")
            args = {"summary": "I suspect P0."} if name == "compact" else {}
            return {
                "prompt_eval_count": 6300 if name == "get_role" else 100,
                "message": {"tool_calls": [{"function": {"name": name, "arguments": args}}]},
            }

        initial = list(session.messages)

        def unavailable(*args):
            raise TimeoutError("backend busy")

        with self.assertRaises(TimeoutError):
            session.step("script", infer=unavailable)
        self.assertEqual(session.messages, initial)
        for name in ("get_role", "compact", "get_state"):
            self.assertEqual(session.step("script", infer=answer)["tool"], name)

    def test_rotation_inspection_is_optional_and_leaves_held_piece_unchanged(self):
        table = Table(
            {"roles": ["blue"], "goal": [2, 0], "hands": [[65]], "store": [65, 65]}, Random(1)
        )
        table.join(0, 0)
        peer = ProjectedSeat(table, 0)
        default = Session(peer)
        self.assertNotIn("inspect_rotations_at", [t["function"]["name"] for t in default.tools()])
        session = Session(peer, inspect_rotations=True)
        before = peer.call("/session")
        answer = session.execute(
            "inspect_rotations_at", {"piece": "H1", "x": 1, "y": 0}, session.tools(), table.revision
        )
        self.assertEqual([r["rotation"] for r in answer["orientations"] if r["can_step_here"]], [3])
        self.assertEqual(peer.call("/session"), before)

    def test_movement_update_displays_the_actual_marker_and_older_legal_landing(self):
        table = Table(CROSSING["setup"], Random(1), discussion=0)
        for seat in range(4):
            table.join(seat, 0)
        for event in CROSSING["events"][1:3]:
            table.submit(0, table.revision, {k: v for k, v in event.items() if k != "kind"}, 0)
        session = Session(ProjectedSeat(table, 0), movement_context=True)
        notice = session.opportunity()
        self.assertEqual(notice["marker_here"], [0, 0])
        self.assertEqual(notice["legal_one_step_destinations"], [[1, 0]])
        self.assertEqual(notice["EXIT"], [2, 0])
        table.submit(0, table.revision, {"to": [1, 0]}, 0)
        session.refresh()
        self.assertEqual(session.opportunity()["proposed_landing_if_approved"], [1, 0])
        self.assertEqual(session.opportunity()["marker_here"], [0, 0])
        self.assertNotIn("legal_one_step_destinations", session.opportunity())

    def test_no_argument_wait_keeps_cursor_from_before_inference(self):
        table = Table(CROSSING["setup"], Random(1), seconds=30, discussion=5)
        for i in range(4):
            table.join(i, 0)
        for e in CROSSING["events"][1:4]:
            table.submit(0, table.revision, {k: v for k, v in e.items() if k != "kind"}, 0)
        peer = ProjectedSeat(table, 2)
        session = Session(peer, sleep=lambda _: self.fail("lost the intervening public remark"))

        def speak_then_wait(_port, _path, body, _budget):
            spec = next(t["function"] for t in body["tools"] if t["function"]["name"] == "wait")
            self.assertEqual(spec["parameters"]["required"], [])
            table.say(1, table.revision, "Check the first move.", 0)
            return {"message": {"tool_calls": [{"function": {"name": "wait", "arguments": {}}}]}}

        first = session.cursor
        response = session.step("script", infer=speak_then_wait)
        self.assertGreater(response["result"]["cursor"], first)
        self.assertEqual(response["result"]["latest"][0]["speaker"], 1)
