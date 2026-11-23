"""A terminal for one seat. Run a copy of this file inside the seat's exchange directory."""

import argparse
import json
import sys
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parent


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cmd = cli.add_subparsers(dest="command", required=True)
    read = cmd.add_parser("next")
    read.add_argument("--wait", type=int, default=30)
    post = cmd.add_parser("submit")
    post.add_argument("id", type=int)
    post.add_argument("reply", help='JSON, e.g. {"choice":{"vote":false},"observation":"..."}')
    args = cli.parse_args()
    if args.command == "next":
        deadline = time.monotonic() + args.wait
        while True:
            for packet in sorted(ROOT.glob("*.request.json")):
                if (ROOT / (packet.name.split(".")[0] + ".expired")).exists():
                    continue
                if not packet.with_name(packet.name.replace(".request.", ".reply.")).exists():
                    print(packet.read_text())
                    return
            if (ROOT / "finished").exists():
                print("The playtest is finished.")
                return
            if time.monotonic() >= deadline:
                print("Waiting for the next decision.")
                return
            time.sleep(0.15)
    packet = ROOT / f"{args.id:04}.request.json"
    if (ROOT / f"{args.id:04}.expired").exists():
        sys.exit("This opportunity expired. Read the next packet.")
    request = json.loads(packet.read_text())
    reply = json.loads(args.reply)
    if not isinstance(reply, dict) or not isinstance(reply.get("observation"), str):
        sys.exit("Include an observation string (it may be empty).")
    if request["kind"] == "choice":
        choice = reply.get("choice")
        fields = request["legal"]
        if (
            not isinstance(choice, dict)
            or choice.keys() != fields.keys()
            or any(
                not any(type(value) is type(v) and value == v for v in fields[k])
                for k, value in choice.items()
            )
        ):
            sys.exit("Choose one listed value per legal field.")
    if request["kind"] == "speech" and (
        not isinstance(reply.get("speech"), str) or len(reply["speech"]) > 500
    ):
        sys.exit("Provide speech of up to 500 characters, or an empty string.")
    path = ROOT / f"{args.id:04}.reply.json"
    # Link the complete response once, without overwriting a previously accepted decision.
    with NamedTemporaryFile(mode="w", dir=ROOT) as handle:
        json.dump(reply, handle)
        handle.flush()
        try:
            path.hardlink_to(handle.name)
        except FileExistsError:
            sys.exit("This decision already has a reply.")
    print("Submitted.")


if __name__ == "__main__":
    main()
