from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .adapters import render
from .control_plane.mcp_server import RESOURCES, TOOLS, serve
from .control_plane.tasks import ControlPlane
from .core.configuration import STATE_FILES, initialise, read_json, state_dir, write_json
from .core.gates import PROTECTED
from .core.project_detection import detect
from .core.routing import fleet, routing


def _root(value: str) -> Path:
    return Path(value).resolve()


def _emit(value: Any, as_json: bool) -> None:
    print(json.dumps(value, indent=2, sort_keys=True) if as_json else value)


def metrics_snapshot() -> dict[str, Any]:
    """Return the stable metrics payload available during 0.2 dogfooding."""
    return {"samples": 0, "primary_metric": "accepted_tasks_per_quota_unit"}


def render_metrics_markdown(metrics: dict[str, Any]) -> str:
    """Render a deterministic report without inferring metrics from absent samples."""
    samples = metrics["samples"]
    rows = (
        ("Samples", samples),
        ("Accepted tasks", 0),
        ("Retries", 0),
        ("Escalations", 0),
        ("Duration", "0 s"),
        ("Parallelism", 0),
        ("Repeated reads", 0),
        (metrics["primary_metric"], 0),
    )
    table = "\n".join(f"| {label} | {value} |" for label, value in rows)
    return (
        "# QuattroAgents metrics\n\n"
        "## Summary\n\n"
        f"No execution samples recorded yet ({samples}). All numeric values are zero; "
        "no savings or outcomes are inferred.\n\n"
        "| Metric | Value |\n"
        "| --- | ---: |\n"
        f"{table}\n"
    )


def initialise_project(root: Path, providers: list[str], profile: str) -> dict[str, Any]:
    initialise(root, profile, providers)
    state = state_dir(root)
    write_json(
        state / "capability-map.json",
        {
            "schema_version": 1,
            "capabilities": {
                "repository_discovery": {"required": True, "risk": "low"},
                "bounded_implementation": {"required": True, "risk": "medium"},
                "realtime_review": {"required": False, "risk": "high"},
            },
        },
    )
    write_json(state / "fleet.json", {"schema_version": 1, "agents": fleet(profile)})
    write_json(state / "model-routing.json", routing(profile))
    write_json(
        state / "quality-gates.json",
        {
            "schema_version": 1,
            "protected_paths": PROTECTED,
            "retry_limit": 1,
            "require_human_approval": True,
        },
    )
    write_json(
        state / "context-manifest.json",
        {"schema_version": 1, "entries": [{"path": "README.md", "purpose": "project overview"}]},
    )
    return {"state": str(state), "providers": providers, "profile": profile}


def validate(root: Path) -> dict[str, Any]:
    missing = [name for name in STATE_FILES if not (state_dir(root) / name).exists()]
    generated = (
        [str(p.relative_to(root)) for p in (root / ".quattroagents").rglob("*.json")]
        if state_dir(root).exists()
        else []
    )
    return {"valid": not missing, "missing": missing, "files": generated}


def doctor(root: Path) -> dict[str, Any]:
    return {
        "version": __version__,
        "python": sys.version.split()[0],
        "root": str(root),
        "venv": str(root / ".venv"),
        "venv_python": (root / ".venv/bin/python").exists()
        or (root / ".venv/Scripts/python.exe").exists(),
        "codex": shutil.which("codex") is not None,
        "claude": shutil.which("claude") is not None,
        "rtk": shutil.which("rtk") is not None,
        "codebase_memory_mcp": shutil.which("codebase-memory-mcp") is not None,
        "state": state_dir(root).exists(),
    }


def write_hooks(root: Path) -> None:
    hooks = root / ".githooks"
    hooks.mkdir(exist_ok=True)
    for name, body in {
        "pre-commit": (
            "#!/bin/sh\nset -eu\n"
            ".venv/bin/python -m quattroagents validate --project . --json\n"
            ".venv/bin/python -m ruff check .\n"
        ),
        "commit-msg": (
            "#!/bin/sh\nset -eu\n"
            'if [ "${QAGENTS_DISABLE_COMMIT_MSG:-0}" = "1" ]; then exit 0; fi\n'
            "if ! grep -Eq '^\\[TASK-[0-9]+\\] ' \"$1\"; then\n"
            '  echo "Commit message must start with [TASK-042] (or set '
            'QAGENTS_DISABLE_COMMIT_MSG=1)." >&2\n'
            "  exit 1\nfi\n"
        ),
        "pre-push": (
            "#!/bin/sh\nset -eu\n"
            ".venv/bin/python -m quattroagents validate --project . --json\n"
            ".venv/bin/python -m pytest\n"
            ".venv/bin/python -m ruff check .\n"
            ".venv/bin/python -m mypy src\n"
        ),
    }.items():
        path = hooks / name
        path.write_text(body)
        path.chmod(0o755)


def setup(root: Path, providers: list[str], profile: str, yes: bool) -> dict[str, Any]:
    venv = root / ".venv"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    if not yes:
        raise RuntimeError("setup changes files; pass --yes for non-interactive setup")
    version = subprocess.run(
        [str(python), "-c", "import sys; print(sys.version_info >= (3, 11))"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if version != "True":
        raise RuntimeError("project .venv must use Python 3.11+")
    source_root = Path(__file__).resolve().parents[2]
    subprocess.run([str(python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "-e", f"{source_root}[dev]"], check=True)
    initialise_project(root, providers, profile)
    files = render(root, providers)
    write_hooks(root)
    return {"configured": files, "doctor": doctor(root), "validation": validate(root)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="qagents")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in (
        "init",
        "analyze",
        "interview",
        "propose",
        "apply",
        "doctor",
        "validate",
        "diff",
        "rollback",
        "reconfigure",
        "benchmark",
    ):
        p = sub.add_parser(name)
        p.add_argument("--project", default=".")
        p.add_argument("--json", action="store_true")
        if name == "init":
            p.add_argument("--providers", default="codex,claude")
            p.add_argument("--profile", default="economy")
            p.add_argument("--greenfield", action="store_true")
            p.add_argument("--brownfield", action="store_true")
        if name == "apply":
            p.add_argument("--providers", default="codex,claude")
    p = sub.add_parser("setup")
    p.add_argument("--project", default=".")
    p.add_argument("--providers", default="codex,claude")
    p.add_argument("--profile", default="economy")
    p.add_argument("--install-mcp", default="recommended")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--json", action="store_true")
    agents = sub.add_parser("agents")
    agents.add_subparsers(dest="agents_command", required=True).add_parser("list").add_argument(
        "--project", default="."
    )
    tasks = sub.add_parser("tasks")
    ts = tasks.add_subparsers(dest="tasks_command", required=True)
    task_list = ts.add_parser("list")
    task_list.add_argument("--project", default=".")
    task_list.add_argument("--json", action="store_true")
    show = ts.add_parser("show")
    show.add_argument("task_id")
    show.add_argument("--project", default=".")
    show.add_argument("--json", action="store_true")
    mcp = sub.add_parser("mcp")
    ms = mcp.add_subparsers(dest="mcp_command", required=True)
    serve_p = ms.add_parser("serve")
    serve_p.add_argument("--project", default=".")
    md = ms.add_parser("doctor")
    md.add_argument("--project", default=".")
    md.add_argument("--json", action="store_true")
    ml = ms.add_parser("list")
    ml.add_argument("--project", default=".")
    ml.add_argument("--json", action="store_true")
    metrics = sub.add_parser("metrics")
    mr = metrics.add_subparsers(dest="metrics_command", required=True)
    report = mr.add_parser("report")
    report.add_argument("--project", default=".")
    report.add_argument("--format", default="json")
    selfh = sub.add_parser("self-hosting")
    ss = selfh.add_subparsers(dest="self_command", required=True)
    status = ss.add_parser("status")
    status.add_argument("--project", default=".")
    status.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = _root(getattr(args, "project", "."))
    as_json = getattr(args, "json", False)
    try:
        out: Any
        if args.command == "init":
            out = initialise_project(root, args.providers.split(","), args.profile)
        elif args.command == "analyze":
            out = detect(root)
        elif args.command == "doctor":
            out = doctor(root)
        elif args.command == "validate":
            out = validate(root)
        elif args.command == "setup":
            out = setup(root, args.providers.split(","), args.profile, args.yes)
        elif args.command == "apply":
            providers = args.providers.split(",")
            out = {"generated": render(root, providers), "providers": providers}
        elif args.command == "agents":
            out = read_json(state_dir(root) / "fleet.json", {}).get("agents", [])
        elif args.command == "tasks":
            plane = ControlPlane(state_dir(root) / "control-plane.sqlite3")
            out = plane.query() if args.tasks_command == "list" else plane.query(args.task_id)
        elif args.command == "mcp" and args.mcp_command == "serve":
            return serve(root)
        elif args.command == "mcp":
            out = {"tools": TOOLS, "resources": RESOURCES, "valid": validate(root)["valid"]}
        elif args.command == "metrics":
            metrics_payload = metrics_snapshot()
            out = (
                render_metrics_markdown(metrics_payload)
                if args.format == "markdown"
                else metrics_payload
            )
        elif args.command == "self-hosting":
            checks = {
                "setup": state_dir(root).exists(),
                "adapter_codex": (root / ".codex/config.toml").exists(),
                "adapter_claude": (root / ".mcp.json").exists(),
                "protected_kernel": (state_dir(root) / "quality-gates.json").exists(),
                "ci": (root / ".github/workflows/ci.yml").exists(),
            }
            out = {
                "status": "dogfooding" if all(checks.values()) else "disabled",
                "checks": checks,
                "note": "0.2 permits only low-risk dogfooding; official self-hosting starts in 0.3.",
            }
        else:
            out = {
                "command": args.command,
                "status": "available",
                "note": "Use init/analyze/apply/setup for state-changing workflow.",
            }
        _emit(out, as_json or isinstance(out, (dict, list)))
        return 0 if not isinstance(out, dict) or out.get("valid", True) else 1
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        _emit({"error": str(exc)}, True)
        return 2
