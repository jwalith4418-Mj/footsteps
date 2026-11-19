# Contributing to Footsteps

## Pick up an issue

Check the issue and its linked pull requests before starting. Leave a short comment saying what you’re taking on. When another change touches the same rule, record format or experiment, link the two issues and say which change should land first. This gives parallel workers a place to coordinate.

Start a topic branch from current `origin/main`. Include the issue number and a short description in its name. If workers share a checkout, use a separate worktree for each branch. For example, from the repository root:

```sh
git fetch origin
git worktree add -b 4-tile-mix ../footsteps-4-tile-mix origin/main
```

Push the branch and open a draft PR when others would benefit from seeing the approach early. Use `Closes #N` for completed issues and `Part of #N` when a trial, decision or deliverable is still outstanding.

## Make the PR reviewable

State what changed, why, and how someone can reproduce the result. Include the evidence appropriate to the change. A rule change merits a worked turn and a note on replay compatibility. An experiment merits the seed panel, command, result and limits. A change to private information merits evidence from the affected seats. The [worker guide](AGENTS.md) lists local checks and project conventions.

Before marking the PR ready, read the diff against its base and flag outstanding questions. Seek a second reader when an interpretation, such as who may see a ballot, is genuinely unsettled. The approval count is zero so a solo maintainer or workers sharing one GitHub identity can land routine changes.

## Land against current main

GitHub requires a PR with resolved review threads, a branch up to date with `main`, and a passing `rules` check from GitHub Actions. If another PR lands first, update the working branch, resolve conflicts there, and let CI rerun. Merge through GitHub after the gate clears. Force pushes and deletion of `main` are blocked, including for admins. Topic branches remain available for parallel work.

The [ruleset definition](.github/rulesets/main.json) records the GitHub setting. Maintainers changing the gate should keep the live ruleset and this file in sync. Coordinate any rename of the required CI job with the ruleset update.
