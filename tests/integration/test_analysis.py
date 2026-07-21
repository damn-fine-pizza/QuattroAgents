from pathlib import Path

from quattroagents.analysis import detect_changes, scan_repository
from quattroagents.domain import ToolDefinition


def test_scan_detects_python_with_setuptools_build_system(tmp_path: Path) -> None:
    """Test case 1: pyproject.toml with setuptools + .py file."""
    (tmp_path / "pyproject.toml").write_text('[build-system]\nrequires = ["setuptools>=45"]\n')
    (tmp_path / "main.py").write_text("# Python code\n")

    profile = scan_repository(tmp_path)

    assert "python" in profile.languages
    assert "setuptools" in profile.build_systems


def test_scan_detects_cpp_with_cmake(tmp_path: Path) -> None:
    """Test case 2: CMakeLists.txt -> cpp, cmake."""
    (tmp_path / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)\n")

    profile = scan_repository(tmp_path)

    assert "cpp" in profile.languages
    assert "cmake" in profile.build_systems


def test_scan_detects_javascript_and_typescript(tmp_path: Path) -> None:
    """Test case 3: package.json + tsconfig.json -> javascript, typescript."""
    (tmp_path / "package.json").write_text('{"name": "test", "version": "1.0.0"}\n')
    (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {}}\n')

    profile = scan_repository(tmp_path)

    assert "javascript" in profile.languages
    assert "typescript" in profile.languages


def test_scan_detects_pytest_from_test_files(tmp_path: Path) -> None:
    """Test case 4: tests/ directory with test_foo.py (no pyproject.toml)."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_foo.py").write_text("def test_example(): pass\n")

    profile = scan_repository(tmp_path)

    assert "pytest" in profile.test_frameworks


def test_scan_detects_github_actions_ci(tmp_path: Path) -> None:
    """Test case 5: .github/workflows/ci.yml -> github-actions."""
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("name: CI\non: push\n")

    profile = scan_repository(tmp_path)

    assert "github-actions" in profile.ci_systems


def test_scan_detects_architecture_docs(tmp_path: Path) -> None:
    """Test case 6: docs/architecture.md -> relative path in architecture_docs."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "architecture.md").write_text("# Architecture\n")

    profile = scan_repository(tmp_path)

    assert "docs/architecture.md" in profile.architecture_docs


def test_fingerprint_is_deterministic(tmp_path: Path) -> None:
    """Test case 7: fingerprint is deterministic; changes with new top-level directory."""
    (tmp_path / "file.txt").write_text("content")

    profile1 = scan_repository(tmp_path)
    profile2 = scan_repository(tmp_path)

    assert profile1.fingerprint == profile2.fingerprint

    (tmp_path / "new_dir").mkdir()
    profile3 = scan_repository(tmp_path)

    assert profile3.fingerprint != profile1.fingerprint


def test_scan_detects_duplicate_implementation_names(tmp_path: Path) -> None:
    """Test case 8: Two files with same basename in different src/ subdirectories."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "old").mkdir()
    (src_dir / "old" / "engine.py").write_text("# Old engine\n")
    (src_dir / "new").mkdir()
    (src_dir / "new" / "engine.py").write_text("# New engine\n")

    profile = scan_repository(tmp_path)

    # Should have a risk mentioning engine.py
    assert any("engine.py" in risk for risk in profile.risks)


def test_scan_detects_legacy_files(tmp_path: Path) -> None:
    """Test case 9: File named legacy_helper.py anywhere in the tree."""
    (tmp_path / "legacy_helper.py").write_text("# Legacy code\n")

    profile = scan_repository(tmp_path)

    assert any("legacy_helper.py" in legacy for legacy in profile.legacy_areas)


def test_scan_detects_claude_config_agents_and_settings(tmp_path: Path) -> None:
    """Test case 10: .claude/agents/foo.md + .claude/settings.json."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "foo.md").write_text("# Agent Foo\n")
    (claude_dir / "settings.json").write_text('{"version": 1}\n')

    profile = scan_repository(tmp_path)

    assert "foo" in profile.existing_claude_config["agents"]
    assert profile.existing_claude_config["settings_present"] is True


def test_scan_detects_mcp_servers(tmp_path: Path) -> None:
    """Test case 11: .mcp.json with mcpServers."""
    (tmp_path / ".mcp.json").write_text('{"mcpServers": {"foo": {}}}\n')

    profile = scan_repository(tmp_path)

    assert profile.existing_mcp_servers == ["foo"]


def test_scan_detects_all_expected_tools(tmp_path: Path) -> None:
    """Test case 12: All 10 expected tool IDs are present with correct structure."""
    profile = scan_repository(tmp_path)

    expected_tool_ids = {
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
    }

    assert isinstance(profile.tools, list)
    actual_tool_ids = {tool.id for tool in profile.tools}
    assert expected_tool_ids == actual_tool_ids

    for tool in profile.tools:
        assert isinstance(tool, ToolDefinition)
        assert tool.availability in {"available", "unavailable"}
        assert isinstance(tool.id, str)
        assert isinstance(tool.source, str)
        assert isinstance(tool.capabilities, list)
        assert isinstance(tool.recommended_for, list)
        assert isinstance(tool.limitations, list)


def test_detect_changes_previous_none_means_significant(tmp_path: Path) -> None:
    """Test case 13: previous=None -> significant=True."""
    profile = scan_repository(tmp_path)

    changes = detect_changes(None, profile)

    assert changes["significant"] is True


def test_detect_changes_identical_profiles_not_significant(tmp_path: Path) -> None:
    """Test case 14: Identical profiles -> significant=False, empty added/removed."""
    (tmp_path / "pyproject.toml").write_text('[build-system]\nrequires = ["setuptools"]\n')
    (tmp_path / "main.py").write_text("# Python\n")

    profile1 = scan_repository(tmp_path)
    profile2 = scan_repository(tmp_path)

    changes = detect_changes(profile1, profile2)

    assert changes["significant"] is False
    assert changes["languages_added"] == []
    assert changes["languages_removed"] == []
    assert changes["build_systems_added"] == []
    assert changes["build_systems_removed"] == []


def test_detect_changes_language_added_is_significant(tmp_path: Path) -> None:
    """Test case 15: current.languages gains entry -> significant=True, in languages_added."""
    (tmp_path / "pyproject.toml").write_text('[build-system]\nrequires = ["setuptools"]\n')
    (tmp_path / "main.py").write_text("# Python\n")

    profile_before = scan_repository(tmp_path)

    (tmp_path / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)\n")

    profile_after = scan_repository(tmp_path)

    changes = detect_changes(profile_before, profile_after)

    assert changes["significant"] is True
    assert "cpp" in changes["languages_added"]
    assert changes["languages_removed"] == []


def test_scan_multiple_ci_systems(tmp_path: Path) -> None:
    """Test detection of multiple CI systems."""
    # GitHub Actions
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("name: CI\n")

    # GitLab CI
    (tmp_path / ".gitlab-ci.yml").write_text("stages:\n  - build\n")

    profile = scan_repository(tmp_path)

    assert "github-actions" in profile.ci_systems
    assert "gitlab-ci" in profile.ci_systems


def test_scan_multiple_test_frameworks(tmp_path: Path) -> None:
    """Test detection of multiple test frameworks."""
    # Pytest
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_example.py").write_text("def test_foo(): pass\n")

    # Jest (via package.json)
    (tmp_path / "package.json").write_text('{"devDependencies": {"jest": "^27.0.0"}}\n')

    profile = scan_repository(tmp_path)

    assert "pytest" in profile.test_frameworks
    assert "jest" in profile.test_frameworks


def test_scan_coding_conventions(tmp_path: Path) -> None:
    """Test detection of coding convention files."""
    (tmp_path / ".editorconfig").write_text("root = true\n")
    (tmp_path / ".ruff.toml").write_text("line-length = 100\n")

    profile = scan_repository(tmp_path)

    assert ".editorconfig" in profile.coding_conventions
    assert ".ruff.toml" in profile.coding_conventions


def test_scan_detects_subsystems_from_src_directory(tmp_path: Path) -> None:
    """Test detection of subsystems from src/ directory."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "core").mkdir()
    (src_dir / "utils").mkdir()

    profile = scan_repository(tmp_path)

    assert "core" in profile.subsystems
    assert "utils" in profile.subsystems


def test_scan_detects_subsystems_from_root_when_no_src(tmp_path: Path) -> None:
    """Test detection of subsystems from root when src/ doesn't exist."""
    (tmp_path / "api").mkdir()
    (tmp_path / "database").mkdir()
    (tmp_path / "tests").mkdir()  # Should be excluded

    profile = scan_repository(tmp_path)

    assert "api" in profile.subsystems
    assert "database" in profile.subsystems
    assert "tests" not in profile.subsystems


def test_scan_poetry_build_system(tmp_path: Path) -> None:
    """Test detection of poetry build system."""
    (tmp_path / "pyproject.toml").write_text('[build-system]\nrequires = ["poetry-core"]\n')

    profile = scan_repository(tmp_path)

    assert "poetry" in profile.build_systems


def test_scan_hatchling_build_system(tmp_path: Path) -> None:
    """Test detection of hatchling build system."""
    (tmp_path / "pyproject.toml").write_text('[build-system]\nrequires = ["hatchling"]\n')

    profile = scan_repository(tmp_path)

    assert "hatchling" in profile.build_systems


def test_scan_pep517_fallback_build_system(tmp_path: Path) -> None:
    """Test fallback to pep517 for unknown pyproject.toml."""
    (tmp_path / "pyproject.toml").write_text("[build-system]\nrequires = []\n")

    profile = scan_repository(tmp_path)

    assert "pep517" in profile.build_systems


def test_scan_rust_language(tmp_path: Path) -> None:
    """Test detection of rust language."""
    (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"\n')

    profile = scan_repository(tmp_path)

    assert "rust" in profile.languages
    assert "cargo" in profile.build_systems


def test_scan_go_language(tmp_path: Path) -> None:
    """Test detection of go language."""
    (tmp_path / "go.mod").write_text("module example.com/test\n")

    profile = scan_repository(tmp_path)

    assert "go" in profile.languages
    assert "go" in profile.build_systems


def test_scan_ruby_language(tmp_path: Path) -> None:
    """Test detection of ruby language."""
    (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'\n")

    profile = scan_repository(tmp_path)

    assert "ruby" in profile.languages


def test_scan_npm_build_system(tmp_path: Path) -> None:
    """Test detection of npm (default for package.json)."""
    (tmp_path / "package.json").write_text('{"name": "test"}\n')

    profile = scan_repository(tmp_path)

    assert "npm" in profile.build_systems


def test_scan_yarn_build_system(tmp_path: Path) -> None:
    """Test detection of yarn build system."""
    (tmp_path / "package.json").write_text('{"name": "test"}\n')
    (tmp_path / "yarn.lock").write_text("# yarn lockfile\n")

    profile = scan_repository(tmp_path)

    assert "yarn" in profile.build_systems


def test_scan_pnpm_build_system(tmp_path: Path) -> None:
    """Test detection of pnpm build system."""
    (tmp_path / "package.json").write_text('{"name": "test"}\n')
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: 5.4\n")

    profile = scan_repository(tmp_path)

    assert "pnpm" in profile.build_systems


def test_scan_make_build_system(tmp_path: Path) -> None:
    """Test detection of make build system."""
    (tmp_path / "Makefile").write_text("all:\n\techo 'Building'\n")

    profile = scan_repository(tmp_path)

    assert "make" in profile.build_systems


def test_scan_pytest_from_pyproject(tmp_path: Path) -> None:
    """Test pytest detection from pyproject.toml."""
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\naddopts = '-v'\n")

    profile = scan_repository(tmp_path)

    assert "pytest" in profile.test_frameworks


def test_scan_go_test_framework(tmp_path: Path) -> None:
    """Test detection of go-test framework."""
    (tmp_path / "example_test.go").write_text("package main\n")

    profile = scan_repository(tmp_path)

    assert "go-test" in profile.test_frameworks


def test_scan_multiple_architecture_docs(tmp_path: Path) -> None:
    """Test detection of multiple architecture documentation files."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "architecture.md").write_text("# Architecture\n")
    (docs_dir / "design.md").write_text("# Design\n")
    adr_dir = docs_dir / "adr"
    adr_dir.mkdir()
    (adr_dir / "adr-001.md").write_text("# ADR 001\n")

    profile = scan_repository(tmp_path)

    assert "docs/architecture.md" in profile.architecture_docs
    assert "docs/design.md" in profile.architecture_docs
    assert "docs/adr/adr-001.md" in profile.architecture_docs


def test_scan_excludes_excluded_dirs_from_docs(tmp_path: Path) -> None:
    """Test that excluded directories are not scanned for architecture docs."""
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    (venv_dir / "architecture.md").write_text("# Should not be found\n")

    profile = scan_repository(tmp_path)

    assert not any("architecture.md" in doc for doc in profile.architecture_docs)


def test_scan_legacy_with_deprecated_keyword(tmp_path: Path) -> None:
    """Test detection of files with 'deprecated' keyword."""
    (tmp_path / "deprecated_module.py").write_text("# Old module\n")

    profile = scan_repository(tmp_path)

    assert any("deprecated_module.py" in legacy for legacy in profile.legacy_areas)


def test_scan_legacy_with_old_keyword(tmp_path: Path) -> None:
    """Test detection of files with 'old' keyword."""
    (tmp_path / "old_utils.py").write_text("# Utilities\n")

    profile = scan_repository(tmp_path)

    assert any("old_utils.py" in legacy for legacy in profile.legacy_areas)


def test_scan_multiple_mcp_servers(tmp_path: Path) -> None:
    """Test detection of multiple MCP servers."""
    (tmp_path / ".mcp.json").write_text('{"mcpServers": {"foo": {}, "bar": {}, "baz": {}}}\n')

    profile = scan_repository(tmp_path)

    assert set(profile.existing_mcp_servers) == {"bar", "baz", "foo"}


def test_scan_claude_config_multiple_agents(tmp_path: Path) -> None:
    """Test detection of multiple claude agents."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "agent1.md").write_text("# Agent 1\n")
    (agents_dir / "agent2.md").write_text("# Agent 2\n")
    (agents_dir / "agent3.md").write_text("# Agent 3\n")

    profile = scan_repository(tmp_path)

    assert set(profile.existing_claude_config["agents"]) == {"agent1", "agent2", "agent3"}


def test_scan_claude_config_skills(tmp_path: Path) -> None:
    """Test detection of claude skills."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()
    (skills_dir / "skill1").mkdir()
    (skills_dir / "skill2").mkdir()

    profile = scan_repository(tmp_path)

    assert set(profile.existing_claude_config["skills"]) == {"skill1", "skill2"}


def test_scan_codex_config(tmp_path: Path) -> None:
    """Test detection of codex configuration."""
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()
    agents_dir = codex_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "agent1.toml").write_text("[agent]\nname = 'Agent 1'\n")
    (codex_dir / "config.toml").write_text("[version]\nschema = 1\n")

    profile = scan_repository(tmp_path)

    assert "agent1" in profile.existing_codex_config["agents"]
    assert profile.existing_codex_config["config_present"] is True


def test_scan_eslintrc_json(tmp_path: Path) -> None:
    """Test detection of eslintrc.json."""
    (tmp_path / ".eslintrc.json").write_text('{"extends": "eslint:recommended"}\n')

    profile = scan_repository(tmp_path)

    assert ".eslintrc.json" in profile.coding_conventions


def test_scan_eslintrc_js(tmp_path: Path) -> None:
    """Test detection of eslintrc.js."""
    (tmp_path / ".eslintrc.js").write_text("module.exports = {};\n")

    profile = scan_repository(tmp_path)

    assert ".eslintrc.js" in profile.coding_conventions


def test_scan_clang_format(tmp_path: Path) -> None:
    """Test detection of .clang-format."""
    (tmp_path / ".clang-format").write_text("BasedOnStyle: LLVM\n")

    profile = scan_repository(tmp_path)

    assert ".clang-format" in profile.coding_conventions


def test_scan_rustfmt_toml(tmp_path: Path) -> None:
    """Test detection of rustfmt.toml."""
    (tmp_path / "rustfmt.toml").write_text("max_width = 100\n")

    profile = scan_repository(tmp_path)

    assert "rustfmt.toml" in profile.coding_conventions


def test_scan_ruff_in_pyproject(tmp_path: Path) -> None:
    """Test detection of ruff config in pyproject.toml."""
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n")

    profile = scan_repository(tmp_path)

    assert "ruff" in profile.coding_conventions


def test_detect_changes_build_systems_added(tmp_path: Path) -> None:
    """Test detection of added build systems."""
    (tmp_path / "pyproject.toml").write_text('[build-system]\nrequires = ["setuptools"]\n')
    profile_before = scan_repository(tmp_path)

    (tmp_path / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)\n")
    profile_after = scan_repository(tmp_path)

    changes = detect_changes(profile_before, profile_after)

    assert "cmake" in changes["build_systems_added"]
    assert changes["significant"] is True


def test_detect_changes_language_removed(tmp_path: Path) -> None:
    """Test detection of removed languages."""
    (tmp_path / "pyproject.toml").write_text('[build-system]\nrequires = ["setuptools"]\n')
    (tmp_path / "main.py").write_text("# Python\n")
    profile_before = scan_repository(tmp_path)

    (tmp_path / "pyproject.toml").unlink()
    (tmp_path / "main.py").unlink()
    profile_after = scan_repository(tmp_path)

    changes = detect_changes(profile_before, profile_after)

    assert "python" in changes["languages_removed"]
    assert changes["significant"] is True


def test_scan_catch2_test_framework(tmp_path: Path) -> None:
    """Test detection of Catch2 test framework."""
    (tmp_path / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.10)\nfind_package(Catch2 REQUIRED)\n"
    )

    profile = scan_repository(tmp_path)

    assert "catch2" in profile.test_frameworks


def test_scan_googletest_framework(tmp_path: Path) -> None:
    """Test detection of googletest framework."""
    (tmp_path / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.10)\nfind_package(GTest REQUIRED)\n"
    )

    profile = scan_repository(tmp_path)

    assert "googletest" in profile.test_frameworks


def test_scan_circleci_ci_system(tmp_path: Path) -> None:
    """Test detection of CircleCI."""
    circleci_dir = tmp_path / ".circleci"
    circleci_dir.mkdir()
    (circleci_dir / "config.yml").write_text("version: 2\n")

    profile = scan_repository(tmp_path)

    assert "circleci" in profile.ci_systems


def test_detect_changes_preserves_order_in_lists(tmp_path: Path) -> None:
    """Test that detect_changes returns sorted lists."""
    (tmp_path / "pyproject.toml").write_text('[build-system]\nrequires = ["setuptools"]\n')
    (tmp_path / "main.py").write_text("# Python\n")
    profile1 = scan_repository(tmp_path)

    (tmp_path / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)\n")
    (tmp_path / "go.mod").write_text("module example.com/test\n")
    profile2 = scan_repository(tmp_path)

    changes = detect_changes(profile1, profile2)

    assert changes["languages_added"] == sorted(changes["languages_added"])
    assert changes["build_systems_added"] == sorted(changes["build_systems_added"])


def test_scan_python_from_py_files_without_pyproject(tmp_path: Path) -> None:
    """Test python detection from .py files when no pyproject.toml exists."""
    (tmp_path / "script.py").write_text("print('hello')\n")

    profile = scan_repository(tmp_path)

    assert "python" in profile.languages


def test_analyze_timestamp_is_set(tmp_path: Path) -> None:
    """Test that analyzed_at timestamp is set."""
    profile = scan_repository(tmp_path)

    assert profile.analyzed_at != ""
    assert "T" in profile.analyzed_at  # ISO format check
    assert "Z" in profile.analyzed_at  # UTC check


def test_duplicate_risks_exclude_duplicates_in_same_directory(tmp_path: Path) -> None:
    """Test that duplicates in same directory are not flagged as risks."""
    (tmp_path / "engine.py").write_text("# engine\n")
    (tmp_path / "utils.py").write_text("# utils\n")

    profile = scan_repository(tmp_path)

    assert not any("engine.py" in risk for risk in profile.risks)


def test_scan_combined_complex_project(tmp_path: Path) -> None:
    """Test a complex project with multiple languages, tools, and configurations."""
    # Python
    (tmp_path / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["setuptools"]\n[tool.ruff]\nline-length = 100\n'
    )
    (tmp_path / "main.py").write_text("# Python\n")

    # JavaScript
    (tmp_path / "package.json").write_text('{"name": "test"}\n')

    # C++
    (tmp_path / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)\n")

    # Tests
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text("def test_foo(): pass\n")

    # CI
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("name: CI\n")

    # Docs
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "architecture.md").write_text("# Architecture\n")

    # Claude config
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "reviewer.md").write_text("# Reviewer\n")
    (claude_dir / "settings.json").write_text('{"version": 1}\n')

    # MCP
    (tmp_path / ".mcp.json").write_text('{"mcpServers": {"memory": {}}}\n')

    profile = scan_repository(tmp_path)

    assert "python" in profile.languages
    assert "javascript" in profile.languages
    assert "cpp" in profile.languages
    assert "setuptools" in profile.build_systems
    assert "npm" in profile.build_systems
    assert "cmake" in profile.build_systems
    assert "pytest" in profile.test_frameworks
    assert "github-actions" in profile.ci_systems
    assert "docs/architecture.md" in profile.architecture_docs
    assert "reviewer" in profile.existing_claude_config["agents"]
    assert profile.existing_claude_config["settings_present"] is True
    assert "memory" in profile.existing_mcp_servers
    assert "ruff" in profile.coding_conventions
    assert len(profile.tools) == 10


def test_duplicate_readme_in_legitimate_project_directories(tmp_path: Path) -> None:
    """Test that duplicate README.md in src/ and docs/ directories is detected as risk."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "README.md").write_text("# Source README\n")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "README.md").write_text("# Documentation README\n")

    profile = scan_repository(tmp_path)

    assert any("readme.md" in risk.lower() for risk in profile.risks)


def test_duplicate_readme_excluded_in_build_and_worktree_directories(tmp_path: Path) -> None:
    """Test that README.md in excluded directories (build-*, worktrees, _deps) is not flagged."""
    # Root README (legitimate)
    (tmp_path / "README.md").write_text("# Root README\n")

    # In .claude/worktrees/agent-xyz/ (should be excluded)
    worktrees_dir = tmp_path / ".claude" / "worktrees" / "agent-abc123"
    worktrees_dir.mkdir(parents=True)
    (worktrees_dir / "README.md").write_text("# Worktree README\n")

    # In build-clang-tidy/_deps/googletest-src/ (should be excluded)
    deps_dir = tmp_path / "build-clang-tidy" / "_deps" / "googletest-src"
    deps_dir.mkdir(parents=True)
    (deps_dir / "README.md").write_text("# GoogleTest README\n")

    profile = scan_repository(tmp_path)

    assert not any("readme.md" in risk.lower() for risk in profile.risks)
