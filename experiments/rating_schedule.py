"""Print matched five-seat games for a single candidate-versus-anchor comparison."""

import argparse
import csv
import sys


def schedule(seeds, anchor, candidate):
    if anchor == candidate:
        raise ValueError("choose distinct policy identifiers")
    if len(set(seeds)) != len(seeds):
        raise ValueError("each deal seed must be unique")
    for block, seed in enumerate(seeds):
        spacing = 1 + block % 2
        for start in range(5):
            reds = {start, (start + spacing) % 5}
            roles = "".join("R" if seat in reds else "B" for seat in range(5))
            pair = f"{seed}-{roles}"
            for arm, replacement in (("anchor", None), ("red", start), ("blue", (start + 3) % 5)):
                seats = [candidate if seat == replacement else anchor for seat in range(5)]
                yield [pair, seed, roles, arm, replacement, *seats]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--anchor", required=True)
    parser.add_argument("--candidate", required=True)
    args = parser.parse_args()
    out = csv.writer(sys.stdout, lineterminator="\n")
    out.writerow(["pair", "deal_seed", "teams_P0_to_P4", "arm", "replacement", *range(5)])
    out.writerows(schedule(args.seeds, args.anchor, args.candidate))


if __name__ == "__main__":
    main()
