"""Open the four initial GitHub issues. Safe to repeat after a partial upload."""

import json
import subprocess
from pathlib import Path

REPO = "othercriteria/footsteps"
BRIEFS = Path(__file__).resolve().parents[1] / "docs/issues"


def main():
    titles = subprocess.check_output(
        ["gh", "api", "--paginate", "--slurp", f"repos/{REPO}/issues?state=all&per_page=100"],
        text=True,
    )
    existing = {
        issue["title"]
        for page in json.loads(titles)
        for issue in page
        if "pull_request" not in issue
    }
    for brief in sorted(BRIEFS.glob("*.md")):
        heading, _, body = brief.read_text().partition("\n")
        title = heading.removeprefix("# ")
        if title not in existing:
            subprocess.run(
                ["gh", "issue", "create", "--repo", REPO, "--title", title, "--body-file", "-"],
                input=body.lstrip(),
                text=True,
                check=True,
            )


if __name__ == "__main__":
    main()
