from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .domain import ProjectProfile, ToolDefinition


def scan_repository(root: Path) -> ProjectProfile:
    fingerprint = _compute_fingerprint(root)
    languages = _detect_languages(root)
    build_systems = _detect_build_systems(root)
    test_frameworks = _detect_test_frameworks(root)
    ci_systems = _detect_ci_systems(root)
    subsystems = _detect_subsystems(root)
    coding_conventions = _detect_coding_conventions(root)
    architecture_docs = _detect_architecture_docs(root)
    tools = _detect_tools()
    existing_claude_config = _detect_claude_config(root)
    existing_codex_config = _detect_codex_config(root)
    existing_mcp_servers = _detect_mcp_servers(root)
    risks, legacy_areas = _detect_risks_and_legacy(root)
    analyzed_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    return ProjectProfile(
        fingerprint=fingerprint,
        languages=languages,
        build_systems=build_systems,
        test_frameworks=test_frameworks,
        ci_systems=ci_systems,
        subsystems=subsystems,
        coding_conventions=coding_conventions,
        architecture_docs=architecture_docs,
        tools=tools,
        existing_claude_config=existing_claude_config,
        existing_codex_config=existing_codex_config,
        existing_mcp_servers=existing_mcp_servers,
        risks=risks,
        legacy_areas=legacy_areas,
        analyzed_at=analyzed_at,
    )


def detect_changes(previous: ProjectProfile | None, current: ProjectProfile) -> dict[str, Any]:
    prev_langs = set(previous.languages) if previous else set()
    curr_langs = set(current.languages)

    prev_builds = set(previous.build_systems) if previous else set()
    curr_builds = set(current.build_systems)

    prev_tools = {t.id: t.availability for t in (previous.tools if previous else [])}
    curr_tools = {t.id: t.availability for t in current.tools}

    tools_changed = []
    for tool_id in set(prev_tools.keys()) | set(curr_tools.keys()):
        if prev_tools.get(tool_id) != curr_tools.get(tool_id):
            tools_changed.append(tool_id)

    significant = (
        previous is None
        or bool(curr_langs - prev_langs)
        or bool(prev_langs - curr_langs)
        or bool(curr_builds - prev_builds)
        or bool(prev_builds - curr_builds)
        or bool(tools_changed)
    )

    return {
        "languages_added": sorted(curr_langs - prev_langs),
        "languages_removed": sorted(prev_langs - curr_langs),
        "build_systems_added": sorted(curr_builds - prev_builds),
        "build_systems_removed": sorted(prev_builds - curr_builds),
        "tools_changed": sorted(tools_changed),
        "significant": significant,
    }


def _compute_fingerprint(root: Path) -> str:
    names = sorted(p.name for p in root.iterdir() if not p.name.startswith("."))
    data = json.dumps(names, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()


def _detect_languages(root: Path) -> list[str]:
    langs: set[str] = set()

    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        langs.add("python")
    elif not langs and any(root.glob("*.py")):
        langs.add("python")

    if (root / "Cargo.toml").exists():
        langs.add("rust")

    if (root / "CMakeLists.txt").exists():
        langs.add("cpp")

    if (root / "package.json").exists():
        langs.add("javascript")
        if (root / "tsconfig.json").exists():
            langs.add("typescript")

    if (root / "go.mod").exists():
        langs.add("go")

    if (root / "Gemfile").exists():
        langs.add("ruby")

    return sorted(langs)


def _detect_build_systems(root: Path) -> list[str]:
    systems: set[str] = set()

    if (root / "CMakeLists.txt").exists():
        systems.add("cmake")

    if (root / "Makefile").exists():
        systems.add("make")

    if (root / "pyproject.toml").exists():
        systems.add(_detect_python_build_system(root))

    if (root / "package.json").exists():
        systems.add(_detect_js_build_system(root))

    if (root / "Cargo.toml").exists():
        systems.add("cargo")

    if (root / "go.mod").exists():
        systems.add("go")

    return sorted(systems)


def _detect_python_build_system(root: Path) -> str:
    try:
        with open(root / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)

        build_system = data.get("build-system", {})
        requires = build_system.get("requires", [])

        if any("setuptools" in req for req in requires):
            return "setuptools"
        if any("poetry" in req for req in requires):
            return "poetry"
        if any("hatchling" in req for req in requires):
            return "hatchling"
        return "pep517"
    except Exception:
        return "pep517"


def _detect_js_build_system(root: Path) -> str:
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    return "npm"


def _detect_test_frameworks(root: Path) -> list[str]:
    frameworks: set[str] = set()

    if (root / "pyproject.toml").exists():
        try:
            with open(root / "pyproject.toml") as f:
                content = f.read()
            if "pytest" in content:
                frameworks.add("pytest")
        except Exception:
            pass

    if (root / "tests").exists() and any((root / "tests").glob("test_*.py")):
        frameworks.add("pytest")

    if (root / "package.json").exists():
        try:
            with open(root / "package.json") as f:
                content = f.read()
            if "jest" in content:
                frameworks.add("jest")
        except Exception:
            pass

    if (root / "CMakeLists.txt").exists():
        try:
            with open(root / "CMakeLists.txt") as f:
                content = f.read()
            if "Catch2" in content:
                frameworks.add("catch2")
            if "gtest" in content or "GTest" in content:
                frameworks.add("googletest")
        except Exception:
            pass

    if any(root.glob("*_test.go")):
        frameworks.add("go-test")

    return sorted(frameworks)


def _detect_ci_systems(root: Path) -> list[str]:
    systems: set[str] = set()

    workflows = root / ".github" / "workflows"
    if workflows.exists() and (list(workflows.glob("*.yml")) or list(workflows.glob("*.yaml"))):
        systems.add("github-actions")

    if (root / ".gitlab-ci.yml").exists():
        systems.add("gitlab-ci")

    if (root / ".circleci" / "config.yml").exists():
        systems.add("circleci")

    return sorted(systems)


def _detect_subsystems(root: Path) -> list[str]:
    src_dir = root / "src"
    if src_dir.exists() and src_dir.is_dir():
        subsystems = sorted(
            [d.name for d in src_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
        )
    else:
        exclude = {
            "tests",
            "docs",
            "scripts",
            "dist",
            "build",
            "node_modules",
            ".venv",
            "__pycache__",
        }
        subsystems = sorted(
            [
                d.name
                for d in root.iterdir()
                if d.is_dir() and not d.name.startswith(".") and d.name not in exclude
            ]
        )

    return subsystems


def _detect_coding_conventions(root: Path) -> list[str]:
    conventions: set[str] = set()

    if (root / ".editorconfig").exists():
        conventions.add(".editorconfig")

    if (root / ".ruff.toml").exists():
        conventions.add(".ruff.toml")
    elif (root / "pyproject.toml").exists():
        try:
            with open(root / "pyproject.toml") as f:
                if "[tool.ruff]" in f.read():
                    conventions.add("ruff")
        except Exception:
            pass

    if (root / ".eslintrc.json").exists():
        conventions.add(".eslintrc.json")
    elif (root / ".eslintrc.js").exists():
        conventions.add(".eslintrc.js")

    if (root / ".clang-format").exists():
        conventions.add(".clang-format")

    if (root / "rustfmt.toml").exists():
        conventions.add("rustfmt.toml")

    return sorted(conventions)


def _detect_architecture_docs(root: Path) -> list[str]:
    docs: list[str] = []
    exclude_dirs = {".venv", "node_modules", ".git"}

    for md_file in root.rglob("*.md"):
        if any(exc in md_file.parts for exc in exclude_dirs):
            continue

        filename_lower = md_file.name.lower()
        if any(keyword in filename_lower for keyword in ["architecture", "adr", "design"]):
            rel_path = md_file.relative_to(root).as_posix()
            docs.append(rel_path)

    return sorted(docs)


def _detect_tools() -> list[ToolDefinition]:
    tool_ids = [
        "rtk",
        "codebase-memory-mcp",
        "ast-grep",
        "git",
        "gh",
        "node",
        "cargo",
        "go",
        "cmake",
        "make",
    ]
    tools: list[ToolDefinition] = []

    for tool_id in tool_ids:
        availability = "available" if shutil.which(tool_id) else "unavailable"
        version = _get_tool_version(tool_id) if availability == "available" else None

        capabilities: list[str] = []
        recommended_for: list[str] = []
        limitations: list[str] = []

        if tool_id == "rtk":
            recommended_for = ["token-efficient CLI wrapping"]
        elif tool_id == "codebase-memory-mcp":
            capabilities = ["semantic-code-search", "persistent-codebase-context"]
            recommended_for = ["architecture analysis", "locating related implementations"]
            limitations = ["may contain stale indexed data"]

        tools.append(
            ToolDefinition(
                id=tool_id,
                availability=availability,
                source="cli",
                capabilities=capabilities,
                recommended_for=recommended_for,
                limitations=limitations,
                version=version,
            )
        )

    return tools


def _get_tool_version(tool_id: str) -> str | None:
    try:
        result = subprocess.run(
            [tool_id, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.strip().split("\n")[0]
    except Exception:
        pass
    return None


def _detect_claude_config(root: Path) -> dict[str, Any]:
    claude_dir = root / ".claude"
    agents_dir = claude_dir / "agents"
    skills_dir = claude_dir / "skills"

    agents = sorted([f.stem for f in agents_dir.glob("*.md")]) if agents_dir.exists() else []
    skills = (
        sorted([d.name for d in skills_dir.iterdir() if d.is_dir()]) if skills_dir.exists() else []
    )
    settings_present = (claude_dir / "settings.json").exists()

    return {
        "agents": agents,
        "skills": skills,
        "settings_present": settings_present,
    }


def _detect_codex_config(root: Path) -> dict[str, Any]:
    codex_dir = root / ".codex"
    agents_dir = codex_dir / "agents"

    agents = sorted([f.stem for f in agents_dir.glob("*.toml")]) if agents_dir.exists() else []
    config_present = (codex_dir / "config.toml").exists()

    return {
        "agents": agents,
        "config_present": config_present,
    }


def _detect_mcp_servers(root: Path) -> list[str]:
    mcp_file = root / ".mcp.json"
    if not mcp_file.exists():
        return []

    try:
        with open(mcp_file) as f:
            data = json.load(f)
        return sorted(data.get("mcpServers", {}).keys())
    except Exception:
        return []


def _detect_risks_and_legacy(root: Path) -> tuple[list[str], list[str]]:
    risks: list[str] = []
    legacy_areas: list[str] = []

    exclude_dir_names = {
        ".venv",
        "node_modules",
        "__pycache__",
        "dist",
        ".git",
        "worktrees",
        "_deps",
    }
    exclude_dir_prefixes = ("build",)

    stem_to_paths: dict[tuple[str, str], list[str]] = {}
    legacy_count = 0

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        dir_parts = path.relative_to(root).parts[:-1]
        if any(
            part in exclude_dir_names or part.startswith(exclude_dir_prefixes) for part in dir_parts
        ):
            continue

        filename_lower = path.name.lower()
        if any(keyword in filename_lower for keyword in ["legacy", "deprecated", "old"]):
            legacy_areas.append(f"legacy-named file: {path.relative_to(root).as_posix()}")
            legacy_count += 1
            if legacy_count >= 20:
                break

        stem = Path(path.name).stem.lower()
        ext = Path(path.name).suffix
        key = (stem, ext)
        if key not in stem_to_paths:
            stem_to_paths[key] = []
        stem_to_paths[key].append(str(path.relative_to(root).as_posix()))

    duplicate_count = 0
    for (stem, ext), paths in stem_to_paths.items():
        dirs = set(str(Path(p).parent) for p in paths)
        if len(dirs) >= 2:
            risks.append(
                f"duplicate implementation name '{stem}{ext}' found in: {', '.join(sorted(paths))}"
            )
            duplicate_count += 1
            if duplicate_count >= 10:
                break

    return sorted(risks), sorted(legacy_areas)
