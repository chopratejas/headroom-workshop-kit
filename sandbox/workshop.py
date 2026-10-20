"""Prebaked Headroom Enterprise sandboxes on Daytona for the hands-on session.

    sandbox/spawn 3                                     # easiest: 3 sandboxes, links printed
    python sandbox/workshop.py snapshot                 # build the image once (~10 min)
    python sandbox/workshop.py create --count 40        # one sandbox per attendee, 10 at a time
    python sandbox/workshop.py links                    # print each attendee's terminal link again
    python sandbox/workshop.py delete                   # tear every workshop sandbox down
    python sandbox/workshop.py delete dev-01 r6test-01  # delete only these

Credentials never go into the image. They are read from an env file (default
~/env.txt) and passed to each sandbox as environment variables when it is
created, so a snapshot can be shared and every secret stays revocable:

    DAYTONA_API_KEY                     Daytona account
    HEADROOM_ACCESS_TOKEN_SANDBOX,      org access token (hrta_...) and org slug for `headroom login`;
    HEADROOM_ORG_SANDBOX                the workshop org (falls back to HEADROOM_TOKEN, HEADROOM_ORG)
    HEADROOM_KOMPRESS_ENDPOINT[_TOKEN]  hosted Kompress model
    ROUTEMEGOOD_CLEF_URL, _TOKEN        optional; Clef /v1/systemone endpoint for complexity routing
    WORKSHOP_GITHUB_PAT                 optional; fine-grained, read-only, public repos only

Everything an attendee can read inside their sandbox, including these values,
must be a workshop-scoped credential you can revoke afterwards.
"""

import argparse
import os
import sys
from pathlib import Path

SNAPSHOT = "headroom-workshop-0.4.3-r18"
LABEL = {"app": "headroom-workshop"}
KIT = Path(__file__).resolve().parent.parent
WHEELHOUSE = KIT / "sandbox" / "headroom-enterprise-wheelhouse-0.4.3.tgz"
# Builds newer than the wheelhouse (unreleased fixes), installed over it: plugin wheels, and
# optionally a headroom-ai core wheel plus a headroom-enterprise wheel that pins it. Private: gitignored.
OVERRIDES = KIT / "sandbox" / "overrides"
NODE = "22.20.0"  # 22.12+ needed: mcp-server-fetch's readabilipy require()s an ES module
GITHUB_MCP = "v0.20.2"
GH_CLI = "2.62.0"

FORWARDED = [
    "HEADROOM_KOMPRESS_ENDPOINT", "HEADROOM_KOMPRESS_ENDPOINT_TOKEN",
    "ROUTEMEGOOD_CLEF_URL", "ROUTEMEGOOD_CLEF_TOKEN",
]


def read_env(path: Path) -> dict:
    env = {}
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def client(env: dict):
    from daytona import Daytona, DaytonaConfig

    if not env.get("DAYTONA_API_KEY"):
        sys.exit("DAYTONA_API_KEY is missing from the env file; add it and retry.")
    return Daytona(DaytonaConfig(api_key=env["DAYTONA_API_KEY"]))


def image():
    from daytona import Image

    if not any(OVERRIDES.glob("*.whl")):
        sys.exit(f"No plugin wheels in {OVERRIDES}. Build them from the fix branches first (uv build --wheel -o {OVERRIDES}).")
    if not WHEELHOUSE.is_file():
        sys.exit(
            f"Wheelhouse not found at {WHEELHOUSE}. Download the stable release from the portal first."
        )
    return (
        Image.base("python:3.12-slim-bookworm")
        .run_commands(
            "apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates jq less vim-tiny procps xz-utils && rm -rf /var/lib/apt/lists/*",
            f"curl -fsSL https://nodejs.org/dist/v{NODE}/node-v{NODE}-linux-x64.tar.xz | tar -xJ -C /usr/local --strip-components=1",
            "npm install -g @anthropic-ai/claude-code @openai/codex @upstash/context7-mcp && npm cache clean --force",
            f"curl -fsSL https://github.com/github/github-mcp-server/releases/download/{GITHUB_MCP}/github-mcp-server_Linux_x86_64.tar.gz | tar -xz -C /usr/local/bin github-mcp-server",
            "pip install --no-cache-dir uv && uv tool install mcp-server-fetch && ln -sf /root/.local/bin/mcp-server-fetch /usr/local/bin/mcp-server-fetch",
            f"curl -fsSL https://github.com/cli/cli/releases/download/v{GH_CLI}/gh_{GH_CLI}_linux_amd64.tar.gz | tar -xz -C /usr/local --strip-components=1",
        )
        .add_local_file(str(WHEELHOUSE), "/opt/headroom/wheelhouse.tgz")
        .run_commands(
            "mkdir -p /opt/headroom/wh && tar -xzf /opt/headroom/wheelhouse.tgz -C /opt/headroom/wh --strip-components=1",
            "pip install --no-cache-dir --only-binary=:all: --find-links=/opt/headroom/wh headroom-enterprise",
        )
        .add_local_dir(str(OVERRIDES), "/opt/headroom/overrides")
        .run_commands(
            "pip install --no-cache-dir --no-deps --force-reinstall /opt/headroom/overrides/*.whl",
            # A newer core can add dependencies; resolve them without touching the overrides.
            "pip install --no-cache-dir --only-binary=:all: --find-links=/opt/headroom/wh /opt/headroom/overrides/*.whl",
            "pip check",
        )
        .add_local_dir(str(KIT / "sandbox" / "home"), "/opt/headroom/home")
        .run_commands(
            "cp -r /opt/headroom/home/. /root/ && cat /root/.bashrc_append >> /root/.bashrc && rm /root/.bashrc_append",
            # One AGENTS.md: Codex reads ~/.codex/AGENTS.md, Claude Code imports it from ~/.claude/CLAUDE.md.
            "ln -s /root/AGENTS.md /root/.codex/AGENTS.md",
            "git clone --depth 1 https://github.com/chopratejas/headroom-workshop-kit /root/workshop",
            "headroom version || true",
        )
        .workdir("/root/workshop")
    )


def cmd_snapshot(env: dict, args) -> None:
    from daytona import CreateSnapshotParams, Resources

    daytona = client(env)
    daytona.snapshot.create(
        CreateSnapshotParams(
            name=args.name, image=image(), resources=Resources(cpu=2, memory=4, disk=7)
        ),
        on_logs=lambda chunk: print(chunk, end=""),
    )
    print(f"\nSnapshot {args.name} is ready.")


def sandbox_env(env: dict, developer_id: str) -> dict:
    token = env.get("HEADROOM_ACCESS_TOKEN_SANDBOX") or env.get("HEADROOM_TOKEN")
    org = env.get("HEADROOM_ORG_SANDBOX") or env.get("HEADROOM_ORG")
    if not (token and org):
        sys.exit("HEADROOM_ACCESS_TOKEN_SANDBOX and HEADROOM_ORG_SANDBOX are missing from the env "
                 "file; `headroom login` needs both.")
    out = {
        "HEADROOM_PORTAL_TOKEN": token,
        "HEADROOM_ORG": org,
        "HEADROOM_DEVELOPER_ID": developer_id,
        "HEADROOM_BEACON": "off",
        **{k: env[k] for k in FORWARDED if env.get(k)},
    }
    if env.get("WORKSHOP_GITHUB_PAT"):
        out["GITHUB_PERSONAL_ACCESS_TOKEN"] = env["WORKSHOP_GITHUB_PAT"]
    return out


def create_one(daytona, env: dict, args, developer_id: str) -> str:
    from daytona import CreateSandboxFromSnapshotParams

    sandbox = daytona.create(
        CreateSandboxFromSnapshotParams(
            snapshot=args.name,
            labels={**LABEL, "developer": developer_id},
            auto_stop_interval=args.auto_stop,
            auto_delete_interval=args.auto_delete,
        ),
        timeout=300,
    )
    env_file = "".join(f"{k}={v}\n" for k, v in sandbox_env(env, developer_id).items())
    sandbox.fs.upload_file(env_file.encode(), "/root/.workshop.env")
    sandbox.process.exec("chmod 600 /root/.workshop.env")
    return f"{developer_id}\t{sandbox.id}\t{ssh_command(sandbox, args.hours)}"


def cmd_create(env: dict, args) -> None:
    """Each sandbox is one attendee: same prebaked snapshot, its own developer id and env file.

    Created `--parallel` at a time; each line is printed as its sandbox becomes ready, so the
    order is not the attendee order. A failed sandbox is reported and the rest carry on.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from daytona import DaytonaError

    sandbox_env(env, "check")  # fail before creating anything if credentials are missing
    if not env.get("ROUTEMEGOOD_CLEF_URL"):
        print("warning: ROUTEMEGOOD_CLEF_URL is not in the env file; these sandboxes will not "
              "route by task complexity.", file=sys.stderr)
    daytona = client(env)
    ids = [f"{args.prefix}-{i:02d}" for i in range(args.start, args.start + args.count)]
    failed = []
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        jobs = {pool.submit(create_one, daytona, env, args, d): d for d in ids}
        for job in as_completed(jobs):
            try:
                print(job.result(), flush=True)
            except DaytonaError as e:
                failed.append(jobs[job])
                print(f"{jobs[job]}: not created ({e})", file=sys.stderr, flush=True)
    if failed:
        sys.exit(
            f"{len(failed)} of {len(ids)} sandboxes failed: {' '.join(sorted(failed))}. "
            "Retry each with --start N --count 1 (check `delete` first if one was half-created)."
        )


def ssh_command(sandbox, hours: int) -> str:
    access = sandbox.create_ssh_access(expires_in_minutes=hours * 60)
    return getattr(access, "ssh_command", None) or f"ssh {access.token}@ssh.app.daytona.io"


def workshop_sandboxes(daytona):
    from daytona import ListSandboxesQuery, SandboxState

    gone = {SandboxState.DESTROYING, SandboxState.DESTROYED}  # delete is async; skip the leftovers
    return [s for s in daytona.list(ListSandboxesQuery(labels=LABEL)) if s.state not in gone]


def cmd_links(env: dict, args) -> None:
    for sandbox in workshop_sandboxes(client(env)):
        print(
            f"{sandbox.labels.get('developer')}\t{sandbox.id}\t{ssh_command(sandbox, args.hours)}"
        )


def cmd_delete(env: dict, args) -> None:
    """Delete the named sandboxes (developer ids), or every workshop sandbox when none are named."""
    daytona = client(env)
    wanted = set(args.developers)
    found = set()
    for sandbox in workshop_sandboxes(daytona):
        developer_id = sandbox.labels.get("developer")
        if wanted and developer_id not in wanted:
            continue
        daytona.delete(sandbox)
        found.add(developer_id)
        print(f"deleted {developer_id} {sandbox.id}")
    if wanted - found:
        print(f"not found: {' '.join(sorted(wanted - found))}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--env-file", type=Path, default=Path.home() / "env.txt")
    parser.add_argument("--name", default=SNAPSHOT, help="snapshot name")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("snapshot")
    create = sub.add_parser("create")
    create.add_argument("--count", type=int, default=1)
    create.add_argument("--start", type=int, default=1, help="first attendee number")
    create.add_argument(
        "--prefix", default="dev", help="developer id prefix shown in the portal fleet"
    )
    create.add_argument("--auto-stop", type=int, default=120, help="minutes idle before stopping")
    create.add_argument(
        "--auto-delete", type=int, default=1440, help="minutes stopped before deleting"
    )
    create.add_argument("--hours", type=int, default=6, help="how long each SSH link stays valid")
    create.add_argument("--parallel", type=int, default=10, help="sandboxes created at once")
    links = sub.add_parser("links")
    links.add_argument("--hours", type=int, default=6)
    delete = sub.add_parser("delete")
    delete.add_argument("developers", nargs="*", help="developer ids to delete; none = all")
    args = parser.parse_args()
    env = read_env(args.env_file)
    {"snapshot": cmd_snapshot, "create": cmd_create, "links": cmd_links, "delete": cmd_delete}[
        args.cmd
    ](env, args)


if __name__ == "__main__":
    main()
