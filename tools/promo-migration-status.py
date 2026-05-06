#!/usr/bin/env python3

"""
Summarize the migration status of a teaching orga from one promo to the next.

Given a target orga like `ue12-p26`, fetches repos, members (with roles), and
pending invitations from both the target (new) orga and the previous-promo
(old) orga, and writes a markdown report.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


REPOS_QUERY = """
query($orga: String!) {
  organization(login: $orga) {
    repositories(first: 100, orderBy: {field: NAME, direction: ASC}) {
      nodes {
        name
        visibility
        isArchived
        description
        defaultBranchRef {
          target {
            ... on Commit {
              author {
                name
                user { login }
              }
            }
          }
        }
      }
    }
  }
}
"""

MEMBERS_QUERY = """
query($orga: String!) {
  organization(login: $orga) {
    membersWithRole(first: 100) {
      edges {
        role
        node { login }
      }
    }
  }
}
"""


def parse_target(target: str) -> tuple[str, str]:
    """Parse `ue12-p26` -> (`ue12-p26`, `ue12-p25`)."""
    m = re.match(r"^(ue\d+)-p(\d+)$", target)
    if not m:
        raise ValueError(
            f"target {target!r} doesn't match <semester>-p<year> (e.g. ue12-p26)"
        )
    semester, year = m.group(1), int(m.group(2))
    if year < 1:
        raise ValueError(f"can't derive previous promo from {target!r}")
    old = f"{semester}-p{year - 1:02d}"
    return target, old


def gh_graphql(query: str, **variables) -> dict:
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        cmd += ["-F", f"{k}={v}"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def gh_rest(path: str) -> list | dict:
    result = subprocess.run(
        ["gh", "api", path], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def fetch_repos(org: str) -> list[dict]:
    data = gh_graphql(REPOS_QUERY, orga=org)
    nodes = data["data"]["organization"]["repositories"]["nodes"]
    out = []
    for n in nodes:
        author = (n.get("defaultBranchRef") or {}).get("target", {}).get("author") or {}
        committer = (author.get("user") or {}).get("login") or author.get("name") or "-"
        out.append({
            "name": n["name"],
            "visibility": n["visibility"],
            "isArchived": n["isArchived"],
            "description": n.get("description") or "",
            "committer": committer,
        })
    out.sort(key=lambda r: r["name"].lower())
    return out


def fetch_members(org: str) -> list[dict]:
    data = gh_graphql(MEMBERS_QUERY, orga=org)
    edges = data["data"]["organization"]["membersWithRole"]["edges"]
    members = [{"login": e["node"]["login"], "role": e["role"]} for e in edges]
    members.sort(key=lambda m: (m["role"] != "ADMIN", m["login"].lower()))
    return members


def fetch_invitations(org: str) -> list[dict]:
    raw = gh_rest(f"orgs/{org}/invitations")
    invites = []
    for inv in raw:
        invites.append({
            "login_or_email": inv.get("login") or inv.get("email") or "-",
            "role": inv.get("role") or "-",
            "inviter": (inv.get("inviter") or {}).get("login") or "-",
        })
    invites.sort(key=lambda i: i["login_or_email"].lower())
    return invites


def render_repos_section(org: str, repos: list[dict]) -> str:
    nb_archived = sum(1 for r in repos if r["isArchived"])
    nb_active = len(repos) - nb_archived
    lines = [
        f"## Repos in {org}",
        "",
        f"Total repos: {len(repos)} ({nb_active} active, {nb_archived} archived)",
        "",
        "| Name | Visibility | Archived | Last Committer | Description |",
        "|------|------------|----------|----------------|-------------|",
    ]
    for r in repos:
        vis = "PRIVATE" if r["visibility"] == "PRIVATE" else "public"
        archived = "yes" if r["isArchived"] else ""
        lines.append(
            f"| [{r['name']}](https://github.com/{org}/{r['name']}) "
            f"| {vis} | {archived} | {r['committer']} | {r['description']} |"
        )
    return "\n".join(lines) + "\n"


def render_members_section(org: str, members: list[dict], invites: list[dict]) -> str:
    out = [f"## Members of {org}", "", f"### Confirmed ({len(members)})", ""]
    if members:
        out += [
            "| Login | Role |",
            "|-------|------|",
        ]
        for m in members:
            out.append(f"| {m['login']} | {m['role']} |")
    else:
        out.append("_none_")
    out += ["", f"### Pending invitations ({len(invites)})", ""]
    if invites:
        out += [
            "| Login / Email | Role | Invited by |",
            "|---------------|------|------------|",
        ]
        for i in invites:
            out.append(f"| {i['login_or_email']} | {i['role']} | {i['inviter']} |")
    else:
        out.append("_none_")
    return "\n".join(out) + "\n"


def render_howto_grant(new_org: str, old_org: str) -> str:
    return f"""## Reminders for granting access

> To promote a member to admin

```bash
gh api -X PUT orgs/{new_org}/memberships/<user> -f role=admin
```

> needs `admin:org` token scope  
  run `gh auth refresh -h github.com -s admin:org` once if needed
"""


def build_report(target: str) -> str:
    new_org, old_org = parse_target(target)
    new_repos = fetch_repos(new_org)
    old_repos = fetch_repos(old_org)
    new_members = fetch_members(new_org)
    old_members = fetch_members(old_org)
    new_invites = fetch_invitations(new_org)
    old_invites = fetch_invitations(old_org)

    sections = [
        f"# {target} repos migration status\n",
        render_repos_section(new_org, new_repos),
        render_repos_section(old_org, old_repos),
        render_howto_grant(new_org, old_org),
        render_members_section(new_org, new_members, new_invites),
        render_members_section(old_org, old_members, old_invites),
    ]
    return "\n".join(sections)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="target orga, e.g. ue12-p26")
    parser.add_argument(
        "-o", "--output",
        help="output path (default: promo-<target>-migration.md). Use '-' for stdout.",
    )
    args = parser.parse_args()

    try:
        report = build_report(args.target)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as e:
        print(f"gh call failed: {e.stderr}", file=sys.stderr)
        return 1

    output = args.output or f"promo-{args.target}-migration.md"
    if output == "-":
        sys.stdout.write(report)
    else:
        Path(output).write_text(report)
        print(f"wrote {output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
