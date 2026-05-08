# Bitbucket PR Tools

Available tools for managing Bitbucket pull requests:

## `mcp__groot-tools__create_bitbucket_pr`
Create a new pull request in a Bitbucket repository.

**Parameters:**
- `repo_slug` (required) — Repository slug, e.g. `tourno`
- `source_branch` (required) — Source branch name, e.g. `bugfix/TF-463-email-sending-fail`
- `destination_branch` (required) — Destination branch name, e.g. `master`
- `title` (required) — PR title
- `description` (optional) — PR description

**Example:**
```
create_bitbucket_pr(
  repo_slug="tourno",
  source_branch="bugfix/TF-463-email-sending-fail",
  destination_branch="master",
  title="Fix: TF-463 — Email sending issue",
  description="Fixed the email sending bug"
)
```

## `mcp__groot-tools__merge_bitbucket_pr`
Merge a pull request in a Bitbucket repository.

**Parameters:**
- `repo_slug` (required) — Repository slug, e.g. `tourno`
- `pr_id` (required) — Pull request ID number
- `merge_strategy` (optional) — Merge strategy: `merge_commit`, `squash`, `fast_forward`. Defaults to `merge_commit`

**Example:**
```
merge_bitbucket_pr(
  repo_slug="tourno",
  pr_id=214,
  merge_strategy="merge_commit"
)
```

## Related Tools
- `list_bitbucket_prs` — List open/merged PRs
- `get_bitbucket_pr` — Get PR details
- `list_bitbucket_branches` — List branches
