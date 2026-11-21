import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
from unittest.mock import patch

from footsteps.record import read
from footsteps.session import Session, main
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
    def test_cli_refreshes_after_losing_an_accepted_placement_reply(self):
        table = Table(
            {"roles": ["blue"], "goal": [2, 0], "hands": [[255]], "store": [0]}, Random(1)
        )

        class DisconnectAfterBuild(ProjectedSeat):
            def call(self, path, data=None):
                if path == "/ready":
                    self.table.join(self.seat, self.now)
                view = super().call(path, data)
                if path == "/choice" and "at" in data["choice"]:
                    raise ConnectionResetError("lost placement receipt")
                return view

        def infer(_port, _path, body, _budget):
            notice = json.loads(body["messages"][-1]["content"])
            self.assertEqual(body["options"]["num_ctx"], 4096)
            if notice["stage"] == "place":
                name, args = "place_tile", {"piece": "H1", "x": 0, "y": 1}
            else:
                self.assertEqual(notice["stage"], "propose")
                name, args = "stay", {}
            return {"message": {"tool_calls": [{"function": {"name": name, "arguments": args}}]}}

        step = Session.step
        with TemporaryDirectory() as tmp:
            trace = Path(tmp) / "owner.jsonl"
            with (
                patch(
                    "sys.argv",
                    ["session", "--model", "mock", "--context", "4096", "--trace", str(trace)],
                ),
                patch("footsteps.session.getpass", return_value="private link"),
                patch("footsteps.session.Seat", return_value=DisconnectAfterBuild(table, 0)),
                patch("footsteps.session.time.sleep"),
                patch.object(
                    Session, "step", lambda session, model: step(session, model, infer=infer)
                ),
                redirect_stdout(output := io.StringIO()),
            ):
                main()
            self.assertEqual(
                [e["kind"] for e in table.record["events"]], ["draw", "place", "propose"]
            )
            self.assertIn("Winner: red", output.getvalue())
            self.assertEqual(json.loads(trace.read_text())["tool"], "stay")
            self.assertEqual(trace.stat().st_mode & 0o077, 0)

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

    def test_pending_ballot_history_and_unavailable_vote_tools(self):
        table = Table(CROSSING["setup"], Random(1), seconds=30, discussion=5)
        for event in CROSSING["events"][:4]:
            table.commit(event)
        for i in range(4):
            table.join(i, 0)
        peer = ProjectedSeat(table, 2)
        player = Session(peer)

        def ask(name, **args):
            fn = {"name": name, "arguments": args}
            return player.step(
                "mock", infer=lambda *_: {"message": {"tool_calls": [{"function": fn}]}}
            )["result"]

        for kind, tool in (("move_vote", "vote_move"), ("eliminate_vote", "vote_removal")):
            with self.subTest(kind=kind):
                discussion = ask("history", kind=kind)
                self.assertEqual(discussion["entries"], [])
                self.assertIn("Speak now", discussion["pending_ballot"])
                self.assertIn("not opened", ask(tool, approve=True)["pending_ballot"])
                for query in (
                    {"kind": "propose"},
                    {"kind": kind, "turn": 99},
                    {"kind": kind, "before": 3},
                ):
                    self.assertNotIn("pending_ballot", ask("history", **query))
                self.assertIn("error", ask("history", kind=kind, speaker=1))
                table.say(2, table.revision, "I have spoken.", peer.now)
                self.assertNotIn("Speak now", ask("history", voter=0)["pending_ballot"])
                peer.now = table.opens
                due = ask("history", kind=kind, voter=0)
                self.assertIn(tool, due["pending_ballot"])
                table.submit(0, table.revision, {"vote": False}, peer.now)
                self.assertEqual(ask("history", kind=kind, voter=0), due)
                if kind == "eliminate_vote":
                    self.assertIn(tool, ask("vote_eliminate", approve=True)["pending_ballot"])
                self.assertTrue(ask(tool, approve=True)["accepted"])
                submitted = ask("history", kind=kind)
                self.assertEqual(submitted["entries"], [])
                self.assertIn("wait()", submitted["pending_ballot"])
                for i in (1, 3):
                    table.submit(i, table.revision, {"vote": True}, peer.now)
                revealed = ask("history", kind=kind, voter=0)
                self.assertNotIn("pending_ballot", revealed)
                self.assertIs(revealed["entries"][-1]["requested_ballot"], False)
                if kind == "move_vote":
                    table.submit(1, table.revision, {"target": 3}, peer.now)

    def test_unoffered_action_reports_tools_for_the_refreshed_opportunity(self):
        table = Table(CROSSING["setup"], Random(1), seconds=30, discussion=5)
        for event in CROSSING["events"][:4]:
            table.commit(event)
        for i in range(4):
            table.join(i, 0)
        peer = ProjectedSeat(table, 2)
        player = Session(peer)

        def vote_at_opening(*_):
            peer.now = table.opens
            fn = {"name": "vote_move", "arguments": {"approve": True}}
            return {"message": {"tool_calls": [{"function": fn}]}}

        result = player.step("mock", infer=vote_at_opening)["result"]
        self.assertIn("error", result)
        self.assertIn("vote_move", result["available_tools"])
        self.assertNotIn("speak", result["available_tools"])
        self.assertTrue(result["current"]["owe_action"])
        self.assertEqual(table.votes, {})
        self.assertTrue(player.step("mock", infer=vote_at_opening)["result"]["accepted"])

    def test_removed_seat_observes_result_without_using_inference(self):
        t = Table(CROSSING["setup"], Random(1), seconds=30, discussion=0)
        for i in range(4):
            t.join(i, 0)
        for e in CROSSING["events"][1:4]:
            t.submit(0, t.revision, {k: v for k, v in e.items() if k != "kind"}, 0)
        for i in range(4):
            t.submit(i, t.revision, {"vote": True}, 0)
        t.submit(1, t.revision, {"target": 3}, 0)
        for i in range(4):
            t.submit(i, t.revision, {"vote": True}, 0)
        peer = ProjectedSeat(t, 3)
        session = Session(peer, sleep=lambda _: setattr(peer, "now", t.deadline))
        self.assertNotIn(3, t.game.alive)
        self.assertIsNone(t.game.winner)
        while session.snap["phase"] != "over":
            self.assertIsNone(
                session.step("script", infer=lambda *_: self.fail("removed seat inferred"))
            )
        self.assertEqual(session.snap["state"]["winner"], t.game.winner)
        self.assertIsNotNone(t.game.winner)

    def test_wait_returns_the_owed_decision_without_spending_time(self):
        for prefix, names in (
            (1, ["place_tile"]),
            (2, ["return_tile"]),
            (3, ["propose_step", "stay"]),
            (4, ["vote_move"]),
            (5, ["nominate", "pass_nomination"]),
            (6, ["vote_removal"]),
        ):
            with self.subTest(prefix=prefix):
                table = Table(CROSSING["setup"], Random(1), seconds=30, discussion=0)
                for event in CROSSING["events"][:prefix]:
                    table.commit(event)
                for i in range(4):
                    table.join(i, 0)
                seat = table.game.queue[0] if table.game.stage == "nominate" else table.game.actor
                session = Session(
                    ProjectedSeat(table, seat), sleep=lambda _: self.fail("blocked on own choice")
                )
                result = session.execute("wait", {}, session.tools(), table.revision)
                self.assertEqual(result["wait_status"], "action_required")
                self.assertEqual(result["decision_tools"], names)
                self.assertTrue(result["owe_action"])
                self.assertEqual(result["seconds_left_in_phase"], 30)
                self.assertEqual(table.revision, prefix)

    def test_forced_wait_expires_current_choice_but_cannot_carry_into_the_next(self):
        table = Table(CROSSING["setup"], Random(1), seconds=30, discussion=0)
        for i in range(4):
            table.join(i, 0)
        peer = ProjectedSeat(table, 0)
        session = Session(peer, sleep=lambda _: setattr(peer, "now", table.deadline))
        original = session.cursor
        result = session.execute("wait", {"force": True}, session.tools(), table.revision)
        self.assertTrue(table.record["events"][-1]["timeout"])
        self.assertEqual(result["stage"], "discard")
        self.assertTrue(result["owe_action"])
        session.sleep = lambda _: self.fail("stale force consumed the next choice")
        result = session.execute(
            "wait", {"after_cursor": original, "force": True}, session.tools(), table.revision
        )
        self.assertEqual(result["stage"], "discard")
        with self.assertRaises(ValueError):
            session.execute("wait", {"force": 1}, session.tools(), table.revision)
        with self.assertRaises(ValueError):
            session.execute(
                "wait",
                {"after_cursor": session.cursor + 1, "force": True},
                session.tools(),
                table.revision,
            )

    def test_force_in_flight_when_a_choice_opens_returns_the_new_opportunity(self):
        table = Table(CROSSING["setup"], Random(1), seconds=30, discussion=5)
        for event in CROSSING["events"][:4]:
            table.commit(event)
        for i in range(4):
            table.join(i, 0)
        peer = ProjectedSeat(table, 1)
        session = Session(peer, sleep=lambda _: self.fail("slept through newly opened ballot"))

        def cross_cutoff(*_):
            peer.now = table.opens
            return {
                "message": {
                    "tool_calls": [{"function": {"name": "wait", "arguments": {"force": True}}}]
                }
            }

        result = session.step("script", infer=cross_cutoff)["result"]
        self.assertTrue(result["owe_action"])
        self.assertEqual(result["phase"], "decision")
        self.assertEqual(result["seconds_left_in_phase"], 30)

    def test_hidden_ballot_during_wait_only_wakes_at_public_reveal(self):
        t = Table(CROSSING["setup"], Random(1), seconds=30, discussion=0)
        for i in range(4):
            t.join(i, 0)
        for e in CROSSING["events"][1:4]:
            t.submit(0, t.revision, {k: v for k, v in e.items() if k != "kind"}, 0)
        peer = ProjectedSeat(t, 2)
        t.submit(2, t.revision, {"vote": True}, 0)
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
        self.assertEqual(notice["marker"], {"x": 0, "y": 0})
        self.assertEqual(notice["legal_steps"], [{"x": 1, "y": 0}])
        self.assertEqual(notice["goal"], {"x": 2, "y": 0})
        table.submit(0, table.revision, {"to": [1, 0]}, 0)
        session.refresh()
        self.assertEqual(session.opportunity()["proposed_landing"], {"x": 1, "y": 0})
        self.assertEqual(session.opportunity()["marker"], {"x": 0, "y": 0})
        self.assertNotIn("legal_steps", session.opportunity())

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

    def test_failed_compactions_restore_last_private_note_and_release_the_decision(self):
        from footsteps.ollama import ServiceError

        t = Table(CROSSING["setup"], Random(1))
        for i in range(4):
            t.join(i, 0)
        s = Session(ProjectedSeat(t, 0))
        s.execute("compact", {"summary": "Check P2's ballot."}, s.tools(), t.revision)
        s.near_capacity = True

        def fail(*_):
            raise ServiceError(500)

        with self.assertRaises(ServiceError):
            s.step("script", infer=fail)
        recovery = s.step("script", infer=fail)
        self.assertTrue(recovery["result"]["context_recovered"])
        self.assertFalse(s.near_capacity)
        context = json.loads(s.messages[-1]["content"])
        self.assertIn("context_recovery", context)
        self.assertEqual(context["your_private_player_authored_summary"], "Check P2's ballot.")
        self.assertIn("place_tile", [f["function"]["name"] for f in s.tools()])
        self.assertEqual(t.revision, 1)

    def test_state_values_can_be_used_in_native_calls_and_keep_coordinate_meaning(self):
        t = Table(CROSSING["setup"], Random(1), discussion=0)
        for i in range(4):
            t.join(i, 0)
        s = Session(ProjectedSeat(t, 0))

        def call(name, **args):
            return s.execute(name, args, s.tools(), s.snap["revision"])

        state = call("get_state")
        square = next(pos for pos in state["empty_build_squares"] if pos == {"x": 1, "y": 0})
        piece = next(p["piece"] for p in state["held"] if p["face"] == 40)
        args = {"piece": piece, **square}
        preview = call("preview_placement", **args)
        self.assertEqual(preview["at"], square)
        self.assertEqual(preview["marker"], state["marker"])
        with self.assertRaisesRegex(ValueError, "piece: string"):
            call("place_tile", tile=40, **square)
        placed = call("place_tile", **args)
        self.assertEqual((placed["action"], placed["acted_at_revision"]), ("place_tile", 1))
        self.assertEqual(placed["current"]["stage"], "discard")
        call("return_tile", piece=call("get_state")["held"][0]["piece"])
        self.assertEqual(call("get_state")["legal_steps"], [square])
        call("propose_step", **square)
        for i in range(4):
            t.submit(i, t.revision, {"vote": True}, 0)
        self.assertEqual(call("history", turn=2, voter=0)["entries"], [])
        self.assertTrue(call("history", turn=1, voter=0)["entries"][0]["requested_ballot"])

    def test_compaction_trigger_uses_the_snapshot_offered_to_the_model(self):
        table = Table(CROSSING["setup"], Random(1), seconds=10, discussion=0)
        for i in range(4):
            table.join(i, 0)
        peer = ProjectedSeat(table, 0)
        s = Session(peer)
        self.assertEqual(s.snap["state"]["stage"], "place")
        peer.now = 10

        def answer(_port, _path, body, _budget):
            self.assertEqual([tool["function"]["name"] for tool in body["tools"]], ["compact"])
            return {
                "message": {
                    "tool_calls": [
                        {
                            "function": {
                                "name": "compact",
                                "arguments": {"summary": "Placement expired."},
                            }
                        }
                    ]
                }
            }

        row = s.step(
            "fixture", infer=answer, compact_when=lambda snap: snap["state"]["stage"] == "discard"
        )
        self.assertTrue(row["forced_compaction"])
        self.assertEqual(row["revision"], 2)
        self.assertEqual(table.game.stage, "discard")
        with self.assertRaisesRegex(ValueError, "history kind"):
            s.execute("history", {"kind": "vote_move"}, s.tools(), 2)

    def test_truncated_voluntary_compact_reopens_with_proportional_output_allowance(self):
        from footsteps.ollama import INCOMPLETE_COMPACT, ServiceError

        for context in (4096, 8192, 16384, 32768):
            with self.subTest(context=context):
                s = Session(ProjectedSeat(Table(CROSSING["setup"], Random(1)), 0), context=context)

                def truncated(_port, _path, body, _budget, context=context):
                    self.assertEqual(
                        (body["options"]["num_ctx"], body["options"]["num_predict"]), (context, 240)
                    )
                    raise ServiceError(500, INCOMPLETE_COMPACT)

                with self.assertRaises(ServiceError):
                    s.step("fixture", infer=truncated)

                def completed(_port, _path, body, _budget, context=context):
                    self.assertEqual(body["options"]["num_predict"], context // 10)
                    self.assertEqual([t["function"]["name"] for t in body["tools"]], ["compact"])
                    return {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "compact",
                                        "arguments": {"summary": "notes " * 300},
                                    }
                                }
                            ]
                        }
                    }

                row = s.step("fixture", infer=completed)
                self.assertTrue(row["result"]["compacted"])
                self.assertFalse(s.near_capacity)
                self.assertEqual(s.summary, "notes " * 300)
