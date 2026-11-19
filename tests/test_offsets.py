import unittest
from collections import Counter
from math import comb

from experiments.offsets import KIT, deal, opening_bridges, trial
from footsteps.game import Game
from footsteps.record import replay


class ExitOffsetStudy(unittest.TestCase):
    def test_paired_physical_deals(self):
        first = deal(1040, (1, 1))
        second = deal(1040, (2, 0))
        self.assertEqual(first["hands"], second["hands"])
        self.assertEqual(first["store"], second["store"])
        self.assertEqual(
            Counter(t for h in first["hands"] for t in h) + Counter(first["store"]), Counter(KIT)
        )
        self.assertEqual(list(map(len, first["hands"])), [2] * 4)
        self.assertEqual(len(first["store"]), 8)
        with self.assertRaisesRegex(ValueError, "start and goal must differ"):
            Game(deal(1040, (0, 0)))

    def test_bridge_counts_and_replay_witness(self):
        self.assertEqual(opening_bridges((2, 0)), (comb(16, 4) - comb(5, 4), comb(16, 4)))
        self.assertEqual(opening_bridges((1, 1)), (comb(16, 4), comb(16, 4)))
        for goal, turn in [((1, 0), 1), ((1, 1), 2), ((2, 0), 4)]:
            row, record = trial(goal, 1040, "route")
            game = replay(record)
            self.assertEqual((row["turns"], game.turn, game.winner), (turn, turn, "good"))
            self.assertEqual(game.actor, turn - 1)
            self.assertEqual(game.marker, goal)
