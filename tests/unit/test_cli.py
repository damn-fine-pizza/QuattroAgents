"""Tests for src/quattroagents/cli.py: CLI surface and subcommand dispatch."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from quattroagents import cli


def fake_tool_returns(value: Any) -> Any:
    """Factory for creating fake tool functions that return a fixed value."""

    def fake_tool(args_dict: dict[str, Any]) -> Any:
        fake_tool.last_call = args_dict
        return value

    fake_tool.last_call = None
    return fake_tool


class TestMainBasic:
    """Test basic main() functionality: entry point, exit codes, JSON output."""

    def test_main_analyze_returns_0_on_success(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test analyze subcommand returns exit code 0."""
        fake = fake_tool_returns({"result": "analyzed"})
        monkeypatch.setattr(cli, "DISPATCH", {"analyze_project": fake})

        exit_code = cli.main(["analyze"])

        assert exit_code == 0
        out_text = capsys.readouterr().out
        output = json.loads(out_text)
        assert output["result"] == "analyzed"

    def test_main_returns_1_when_valid_false(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test exit code 1 when tool returns {'valid': False}."""
        fake = fake_tool_returns({"valid": False, "reason": "invalid config"})
        monkeypatch.setattr(cli, "DISPATCH", {"validate_generated_configuration": fake})

        exit_code = cli.main(["validate"])

        assert exit_code == 1
        out_text = capsys.readouterr().out
        output = json.loads(out_text)
        assert output["valid"] is False
        assert output["reason"] == "invalid config"

    def test_main_returns_2_on_exception(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test exit code 2 and error output when tool raises exception."""

        def failing_tool(args_dict: dict[str, Any]) -> Any:
            raise ValueError("boom")

        monkeypatch.setattr(cli, "DISPATCH", {"show_generation_diff": failing_tool})

        exit_code = cli.main(["diff"])

        assert exit_code == 2
        out_text = capsys.readouterr().out
        output = json.loads(out_text)
        assert "error" in output
        assert output["error"] == "boom"

    def test_main_version_flag_exits_0(self) -> None:
        """Test --version flag raises SystemExit(0)."""
        with pytest.raises(SystemExit) as exc_info:
            cli.main(["--version"])
        assert exc_info.value.code == 0


class TestAnalyze:
    """Test analyze subcommand."""

    def test_analyze_calls_analyze_project(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test analyze subcommand calls analyze_project tool."""
        fake = fake_tool_returns({"status": "ok"})
        monkeypatch.setattr(cli, "DISPATCH", {"analyze_project": fake})

        cli.main(["analyze"])

        assert fake.last_call is not None
        assert "project_root" in fake.last_call
        assert Path(fake.last_call["project_root"]).is_absolute()

    def test_analyze_with_project_flag(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test analyze with --project flag resolves to absolute path."""
        fake = fake_tool_returns({"status": "ok"})
        monkeypatch.setattr(cli, "DISPATCH", {"analyze_project": fake})

        cli.main(["analyze", "--project", str(tmp_path)])

        assert fake.last_call is not None
        assert fake.last_call["project_root"] == str(tmp_path.resolve())


class TestValidate:
    """Test validate subcommand."""

    def test_validate_calls_validate_generated_configuration(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test validate subcommand calls validate_generated_configuration tool."""
        fake = fake_tool_returns({"valid": True})
        monkeypatch.setattr(cli, "DISPATCH", {"validate_generated_configuration": fake})

        exit_code = cli.main(["validate"])

        assert exit_code == 0
        assert fake.last_call is not None
        assert "project_root" in fake.last_call


class TestDiff:
    """Test diff subcommand."""

    def test_diff_calls_show_generation_diff(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test diff subcommand calls show_generation_diff tool."""
        fake = fake_tool_returns({"changes": []})
        monkeypatch.setattr(cli, "DISPATCH", {"show_generation_diff": fake})

        cli.main(["diff"])

        assert fake.last_call is not None
        assert "project_root" in fake.last_call


class TestSetup:
    """Test setup subcommand."""

    def test_setup_default_providers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test setup with default providers split into list."""
        fake = fake_tool_returns({"setup": "done"})
        monkeypatch.setattr(cli, "DISPATCH", {"setup": fake})

        cli.main(["setup"])

        assert fake.last_call is not None
        assert "providers" in fake.last_call
        # Default is "claude,codex"
        assert fake.last_call["providers"] == ["claude", "codex"]

    def test_setup_custom_providers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test setup with custom --providers flag split correctly."""
        fake = fake_tool_returns({"setup": "done"})
        monkeypatch.setattr(cli, "DISPATCH", {"setup": fake})

        cli.main(["setup", "--providers", "a,b,c"])

        assert fake.last_call is not None
        assert fake.last_call["providers"] == ["a", "b", "c"]

    def test_setup_single_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test setup with single provider."""
        fake = fake_tool_returns({"setup": "done"})
        monkeypatch.setattr(cli, "DISPATCH", {"setup": fake})

        cli.main(["setup", "--providers", "claude"])

        assert fake.last_call is not None
        assert fake.last_call["providers"] == ["claude"]


class TestAgents:
    """Test agents subcommand."""

    def test_agents_list_calls_list_agents(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test agents list calls list_agents tool."""
        fake = fake_tool_returns({"agents": []})
        monkeypatch.setattr(cli, "DISPATCH", {"list_agents": fake})

        cli.main(["agents", "list"])

        assert fake.last_call is not None
        assert "project_root" in fake.last_call

    def test_agents_generate_calls_generate_agents(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test agents generate calls generate_agents tool."""
        fake = fake_tool_returns({"agents": ["agent1"]})
        monkeypatch.setattr(cli, "DISPATCH", {"generate_agents": fake})

        cli.main(["agents", "generate"])

        assert fake.last_call is not None
        assert "project_root" in fake.last_call


class TestSkills:
    """Test skills subcommand."""

    def test_skills_generate_calls_generate_skills(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test skills generate calls generate_skills tool."""
        fake = fake_tool_returns({"skills": []})
        monkeypatch.setattr(cli, "DISPATCH", {"generate_skills": fake})

        cli.main(["skills", "generate"])

        assert fake.last_call is not None
        assert "project_root" in fake.last_call


class TestDecisions:
    """Test decisions subcommand."""

    def test_decisions_list_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test decisions list without optional flags."""
        fake = fake_tool_returns({"decisions": []})
        monkeypatch.setattr(cli, "DISPATCH", {"list_decisions": fake})

        cli.main(["decisions", "list"])

        assert fake.last_call is not None
        assert "project_root" in fake.last_call
        # status and decision_scope should not be in dict if not provided
        assert "status" not in fake.last_call
        assert "decision_scope" not in fake.last_call

    def test_decisions_list_with_status(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test decisions list with --status flag."""
        fake = fake_tool_returns({"decisions": []})
        monkeypatch.setattr(cli, "DISPATCH", {"list_decisions": fake})

        cli.main(["decisions", "list", "--status", "active"])

        assert fake.last_call is not None
        assert fake.last_call["status"] == "active"

    def test_decisions_list_with_scope(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test decisions list with --scope flag."""
        fake = fake_tool_returns({"decisions": []})
        monkeypatch.setattr(cli, "DISPATCH", {"list_decisions": fake})

        cli.main(["decisions", "list", "--scope", "project_wide"])

        assert fake.last_call is not None
        assert fake.last_call["decision_scope"] == "project_wide"

    def test_decisions_list_with_both_flags(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test decisions list with both --status and --scope."""
        fake = fake_tool_returns({"decisions": []})
        monkeypatch.setattr(cli, "DISPATCH", {"list_decisions": fake})

        cli.main(["decisions", "list", "--status", "active", "--scope", "task_local"])

        assert fake.last_call is not None
        assert fake.last_call["status"] == "active"
        assert fake.last_call["decision_scope"] == "task_local"

    def test_decisions_record_required_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test decisions record with required args only."""
        fake = fake_tool_returns({"recorded": True})
        monkeypatch.setattr(cli, "DISPATCH", {"record_decision": fake})

        cli.main(["decisions", "record", "--id", "dec1", "--title", "Test Decision"])

        assert fake.last_call is not None
        assert fake.last_call["id"] == "dec1"
        assert fake.last_call["title"] == "Test Decision"
        assert fake.last_call["value"] == "{}"  # default
        assert fake.last_call["reason"] == ""  # default
        assert fake.last_call["scope_paths"] == "[]"  # default
        assert fake.last_call["decision_scope"] == "project_wide"  # default
        assert fake.last_call["effects"] == "{}"  # default

    def test_decisions_record_all_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test decisions record with all optional args."""
        fake = fake_tool_returns({"recorded": True})
        monkeypatch.setattr(cli, "DISPATCH", {"record_decision": fake})

        cli.main(
            [
                "decisions",
                "record",
                "--id",
                "dec1",
                "--title",
                "Decision",
                "--value",
                '{"key": "val"}',
                "--reason",
                "Good reason",
                "--scope-paths",
                '["src/"]',
                "--decision-scope",
                "task_local",
                "--effects",
                '{"agents": ["a1"]}',
            ]
        )

        assert fake.last_call is not None
        assert fake.last_call["id"] == "dec1"
        assert fake.last_call["title"] == "Decision"
        assert fake.last_call["value"] == '{"key": "val"}'
        assert fake.last_call["reason"] == "Good reason"
        assert fake.last_call["scope_paths"] == '["src/"]'
        assert fake.last_call["decision_scope"] == "task_local"
        assert fake.last_call["effects"] == '{"agents": ["a1"]}'

    def test_decisions_reopen(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test decisions reopen with required args."""
        fake = fake_tool_returns({"reopened": True})
        monkeypatch.setattr(cli, "DISPATCH", {"reopen_decision": fake})

        cli.main(["decisions", "reopen", "dec1", "--reason", "Reopen it"])

        assert fake.last_call is not None
        assert fake.last_call["decision_id"] == "dec1"
        assert fake.last_call["reason"] == "Reopen it"


class TestTask:
    """Test task subcommand."""

    def test_task_prepare_required_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test task prepare with required args only."""
        fake = fake_tool_returns({"prepared": True})
        monkeypatch.setattr(cli, "DISPATCH", {"prepare_task": fake})

        cli.main(
            [
                "task",
                "prepare",
                "--task-id",
                "task1",
                "--goal",
                "Do something",
                "--session-id",
                "session1",
            ]
        )

        assert fake.last_call is not None
        assert fake.last_call["task_id"] == "task1"
        assert fake.last_call["goal"] == "Do something"
        assert fake.last_call["session_id"] == "session1"
        assert fake.last_call["base_agent_ids"] == "[]"  # default

    def test_task_prepare_with_base_agent_ids(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test task prepare with --base-agent-ids."""
        fake = fake_tool_returns({"prepared": True})
        monkeypatch.setattr(cli, "DISPATCH", {"prepare_task": fake})

        cli.main(
            [
                "task",
                "prepare",
                "--task-id",
                "task1",
                "--goal",
                "Do it",
                "--session-id",
                "session1",
                "--base-agent-ids",
                '["agent1", "agent2"]',
            ]
        )

        assert fake.last_call is not None
        assert fake.last_call["base_agent_ids"] == '["agent1", "agent2"]'


class TestSwarm:
    """Test swarm subcommand."""

    def test_swarm_plan_required_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test swarm plan with required args only."""
        fake = fake_tool_returns({"plan": "created"})
        monkeypatch.setattr(cli, "DISPATCH", {"generate_swarm_plan": fake})

        cli.main(["swarm", "plan", "--task-id", "t1", "--goal", "goal"])

        assert fake.last_call is not None
        assert fake.last_call["task_id"] == "t1"
        assert fake.last_call["goal"] == "goal"
        # agent_ids should not be in dict if not provided
        assert "agent_ids" not in fake.last_call
        assert fake.last_call["phases"] == "{}"  # default
        assert fake.last_call["depends_on"] == "{}"  # default
        assert fake.last_call["file_ownership"] == "{}"  # default

    def test_swarm_plan_with_agent_ids(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test swarm plan with --agent-ids."""
        fake = fake_tool_returns({"plan": "created"})
        monkeypatch.setattr(cli, "DISPATCH", {"generate_swarm_plan": fake})

        cli.main(
            [
                "swarm",
                "plan",
                "--task-id",
                "t1",
                "--goal",
                "goal",
                "--agent-ids",
                "a1,a2",
            ]
        )

        assert fake.last_call is not None
        assert fake.last_call["agent_ids"] == "a1,a2"

    def test_swarm_plan_with_phases(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test swarm plan with --phases."""
        fake = fake_tool_returns({"plan": "created"})
        monkeypatch.setattr(cli, "DISPATCH", {"generate_swarm_plan": fake})

        phases = '{"phase1": ["a1"], "phase2": ["a2"]}'
        cli.main(
            [
                "swarm",
                "plan",
                "--task-id",
                "t1",
                "--goal",
                "goal",
                "--phases",
                phases,
            ]
        )

        assert fake.last_call is not None
        assert fake.last_call["phases"] == phases


class TestInterview:
    """Test interview subcommand."""

    def test_interview_start(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test interview start with required and default args."""
        fake = fake_tool_returns({"session_id": "sess1"})
        monkeypatch.setattr(cli, "DISPATCH", {"start_project_interview": fake})

        cli.main(["interview", "start", "--session-id", "sess1"])

        assert fake.last_call is not None
        assert fake.last_call["session_id"] == "sess1"
        assert fake.last_call["session_type"] == "initial_setup"  # default

    def test_interview_start_with_session_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test interview start with custom session type."""
        fake = fake_tool_returns({"session_id": "sess1"})
        monkeypatch.setattr(cli, "DISPATCH", {"start_project_interview": fake})

        cli.main(
            [
                "interview",
                "start",
                "--session-id",
                "sess1",
                "--session-type",
                "task_preparation",
            ]
        )

        assert fake.last_call is not None
        assert fake.last_call["session_type"] == "task_preparation"

    def test_interview_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test interview state command."""
        fake = fake_tool_returns({"state": "awaiting_answers"})
        monkeypatch.setattr(cli, "DISPATCH", {"get_interview_state": fake})

        cli.main(["interview", "state", "sess1"])

        assert fake.last_call is not None
        assert fake.last_call["session_id"] == "sess1"

    def test_interview_next(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test interview next command."""
        fake = fake_tool_returns({"questions": []})
        monkeypatch.setattr(cli, "DISPATCH", {"get_next_questions": fake})

        cli.main(["interview", "next", "sess1"])

        assert fake.last_call is not None
        assert fake.last_call["session_id"] == "sess1"

    def test_interview_answer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test interview answer command."""
        fake = fake_tool_returns({"submitted": True})
        monkeypatch.setattr(cli, "DISPATCH", {"submit_interview_answers": fake})

        answers = '[{"q_id": "q1", "value": "yes"}]'
        cli.main(["interview", "answer", "sess1", "--answers", answers])

        assert fake.last_call is not None
        assert fake.last_call["session_id"] == "sess1"
        assert fake.last_call["answers"] == answers

    def test_interview_summary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test interview summary command."""
        fake = fake_tool_returns({"summary": "done"})
        monkeypatch.setattr(cli, "DISPATCH", {"review_interview_summary": fake})

        cli.main(["interview", "summary", "sess1"])

        assert fake.last_call is not None
        assert fake.last_call["session_id"] == "sess1"

    def test_interview_confirm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test interview confirm command."""
        fake = fake_tool_returns({"confirmed": True})
        monkeypatch.setattr(cli, "DISPATCH", {"confirm_interview_decisions": fake})

        cli.main(["interview", "confirm", "sess1"])

        assert fake.last_call is not None
        assert fake.last_call["session_id"] == "sess1"

    def test_interview_gaps(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test interview gaps command."""
        fake = fake_tool_returns({"gaps": []})
        monkeypatch.setattr(cli, "DISPATCH", {"list_open_knowledge_gaps": fake})

        cli.main(["interview", "gaps", "sess1"])

        assert fake.last_call is not None
        assert fake.last_call["session_id"] == "sess1"

    def test_interview_conflicts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test interview conflicts command."""
        fake = fake_tool_returns({"conflicts": []})
        monkeypatch.setattr(cli, "DISPATCH", {"list_decision_conflicts": fake})

        cli.main(["interview", "conflicts", "sess1"])

        assert fake.last_call is not None
        assert fake.last_call["session_id"] == "sess1"

    def test_interview_resolve(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test interview resolve command."""
        fake = fake_tool_returns({"resolved": True})
        monkeypatch.setattr(cli, "DISPATCH", {"resolve_decision_conflict": fake})

        cli.main(["interview", "resolve", "--conflict-id", "conf1", "--resolution", "accept"])

        assert fake.last_call is not None
        assert fake.last_call["conflict_id"] == "conf1"
        assert fake.last_call["resolution"] == "accept"


class TestMcp:
    """Test mcp subcommand."""

    def test_mcp_list(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test mcp list emits tools."""
        fake_tools = {"tool1": {}, "tool2": {}}
        monkeypatch.setattr(cli, "TOOLS", fake_tools)

        exit_code = cli.main(["mcp", "list"])

        assert exit_code == 0
        out_text = capsys.readouterr().out
        output = json.loads(out_text)
        assert output["tools"] == fake_tools

    def test_mcp_serve(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test mcp serve returns serve() return value directly without wrapping."""
        fake_serve = MagicMock(return_value=42)
        monkeypatch.setattr(cli, "serve", fake_serve)

        exit_code = cli.main(["mcp", "serve"])

        assert exit_code == 42
        fake_serve.assert_called_once()


class TestDoctor:
    """Test doctor subcommand and function."""

    def test_doctor_returns_dict_with_all_keys(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        """Test doctor command returns dict with all expected keys."""
        # Mock shutil.which to return None for all (no tools found)
        monkeypatch.setattr(cli.shutil, "which", lambda x: None)
        # Mock runtime functions
        monkeypatch.setattr(cli, "runtime_identity", lambda: ("abc123", False))
        monkeypatch.setattr(cli, "runtime_version", lambda: "1.0.0")

        exit_code = cli.main(["doctor", "--project", str(tmp_path)])

        assert exit_code == 0
        out_text = capsys.readouterr().out
        output = json.loads(out_text)

        # Check all expected keys
        assert "version" in output
        assert "package_version" in output
        assert "revision" in output
        assert "dirty" in output
        assert "python" in output
        assert "root" in output
        assert "codex" in output
        assert "claude" in output
        assert "rtk" in output
        assert "codebase_memory_mcp" in output
        assert "state" in output

    def test_doctor_version_and_package_version(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test doctor extracts package_version from version string."""
        monkeypatch.setattr(cli.shutil, "which", lambda x: None)
        monkeypatch.setattr(cli, "runtime_identity", lambda: ("hash", False))
        monkeypatch.setattr(cli, "runtime_version", lambda: "1.2.3+local")

        result = cli.doctor(tmp_path)

        assert result["version"] == "1.2.3+local"
        assert result["package_version"] == "1.2.3"

    def test_doctor_tool_detection_rtk(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test doctor detects rtk presence."""

        def which_impl(name: str) -> str | None:
            return "/usr/bin/rtk" if name == "rtk" else None

        monkeypatch.setattr(cli.shutil, "which", which_impl)
        monkeypatch.setattr(cli, "runtime_identity", lambda: ("hash", False))
        monkeypatch.setattr(cli, "runtime_version", lambda: "1.0.0")

        result = cli.doctor(tmp_path)

        assert result["rtk"] is True
        assert result["claude"] is False
        assert result["codex"] is False

    def test_doctor_tool_detection_multiple(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test doctor detects multiple tool presences."""

        def which_impl(name: str) -> str | None:
            return f"/usr/bin/{name}" if name in ("rtk", "claude") else None

        monkeypatch.setattr(cli.shutil, "which", which_impl)
        monkeypatch.setattr(cli, "runtime_identity", lambda: ("hash", False))
        monkeypatch.setattr(cli, "runtime_version", lambda: "1.0.0")

        result = cli.doctor(tmp_path)

        assert result["rtk"] is True
        assert result["claude"] is True
        assert result["codex"] is False
        assert result["codebase_memory_mcp"] is False

    def test_doctor_state_false_when_no_store_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test doctor.state is False when store_dir does not exist."""
        monkeypatch.setattr(cli.shutil, "which", lambda x: None)
        monkeypatch.setattr(cli, "runtime_identity", lambda: ("hash", False))
        monkeypatch.setattr(cli, "runtime_version", lambda: "1.0.0")

        result = cli.doctor(tmp_path)

        assert result["state"] is False

    def test_doctor_state_true_when_store_dir_exists(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test doctor.state is True when store_dir exists."""
        # Create the store directory
        store_path = tmp_path / ".agent-factory"
        store_path.mkdir()

        monkeypatch.setattr(cli.shutil, "which", lambda x: None)
        monkeypatch.setattr(cli, "runtime_identity", lambda: ("hash", False))
        monkeypatch.setattr(cli, "runtime_version", lambda: "1.0.0")

        result = cli.doctor(tmp_path)

        assert result["state"] is True

    def test_doctor_python_version(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test doctor includes Python version."""
        monkeypatch.setattr(cli.shutil, "which", lambda x: None)
        monkeypatch.setattr(cli, "runtime_identity", lambda: ("hash", False))
        monkeypatch.setattr(cli, "runtime_version", lambda: "1.0.0")
        monkeypatch.setattr(cli.sys, "version", "3.11.5 (main, ...)")

        result = cli.doctor(tmp_path)

        assert result["python"] == "3.11.5"

    def test_doctor_root_path(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test doctor includes the resolved root path."""
        monkeypatch.setattr(cli.shutil, "which", lambda x: None)
        monkeypatch.setattr(cli, "runtime_identity", lambda: ("hash", False))
        monkeypatch.setattr(cli, "runtime_version", lambda: "1.0.0")

        result = cli.doctor(tmp_path)

        assert result["root"] == str(tmp_path.resolve())


class TestProjectResolution:
    """Test --project flag resolution."""

    def test_project_flag_resolves_to_absolute(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test --project resolves relative paths to absolute."""
        fake = fake_tool_returns({"status": "ok"})
        monkeypatch.setattr(cli, "DISPATCH", {"analyze_project": fake})

        # Use an absolute path directly
        cli.main(["analyze", "--project", str(tmp_path)])

        assert fake.last_call is not None
        assert fake.last_call["project_root"] == str(tmp_path.resolve())

    def test_default_project_is_resolved(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test default project '.' is resolved to absolute path."""
        fake = fake_tool_returns({"status": "ok"})
        monkeypatch.setattr(cli, "DISPATCH", {"analyze_project": fake})

        cli.main(["analyze"])

        assert fake.last_call is not None
        project_root = fake.last_call["project_root"]
        assert Path(project_root).is_absolute()


class TestCallFiltering:
    """Test _call() filters None values from kwargs."""

    def test_call_excludes_none_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that _call() excludes kwargs with None values from args dict."""
        fake = fake_tool_returns({"result": "ok"})
        monkeypatch.setattr(cli, "DISPATCH", {"list_decisions": fake})

        # Both status and scope are optional, and parser returns None if not provided
        cli.main(["decisions", "list"])

        assert fake.last_call is not None
        # Only project_root should be in dict
        assert "project_root" in fake.last_call
        assert "status" not in fake.last_call
        assert "decision_scope" not in fake.last_call

    def test_call_includes_non_none_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that _call() includes non-None kwargs in args dict."""
        fake = fake_tool_returns({"result": "ok"})
        monkeypatch.setattr(cli, "DISPATCH", {"list_decisions": fake})

        cli.main(["decisions", "list", "--status", "active"])

        assert fake.last_call is not None
        assert fake.last_call["status"] == "active"


class TestJsonOutput:
    """Test JSON output formatting."""

    def test_output_json_sorted_keys(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that output is JSON with sorted keys."""
        fake = fake_tool_returns({"z_key": 1, "a_key": 2, "m_key": 3})
        monkeypatch.setattr(cli, "DISPATCH", {"analyze_project": fake})

        cli.main(["analyze"])

        out_text = capsys.readouterr().out
        output = json.loads(out_text)
        # Verify JSON is valid and has expected content
        assert output["z_key"] == 1
        assert output["a_key"] == 2
        assert output["m_key"] == 3

    def test_output_json_indented(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that output is indented JSON."""
        fake = fake_tool_returns({"nested": {"key": "value"}})
        monkeypatch.setattr(cli, "DISPATCH", {"analyze_project": fake})

        cli.main(["analyze"])

        out_text = capsys.readouterr().out
        # Indented JSON should have newlines
        assert "\n" in out_text
        assert "  " in out_text  # spaces for indentation


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_tool_returns_non_dict(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test tool returning non-dict value (e.g., list or string)."""
        fake = fake_tool_returns(["item1", "item2"])
        monkeypatch.setattr(cli, "DISPATCH", {"analyze_project": fake})

        exit_code = cli.main(["analyze"])

        # Non-dict values should still return exit code 0 (valid check only applies to dicts)
        assert exit_code == 0
        out_text = capsys.readouterr().out
        output = json.loads(out_text)
        assert output == ["item1", "item2"]

    def test_tool_returns_dict_without_valid_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test tool returning dict without 'valid' key defaults to valid=True."""
        fake = fake_tool_returns({"some_key": "some_value"})
        monkeypatch.setattr(cli, "DISPATCH", {"validate_generated_configuration": fake})

        exit_code = cli.main(["validate"])

        # Should be 0 because valid defaults to True
        assert exit_code == 0

    def test_exception_with_special_characters(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test exception message with special characters is properly JSON-encoded."""

        def failing_tool(args_dict: dict[str, Any]) -> Any:
            raise ValueError('Error with "quotes" and \\ backslash')

        monkeypatch.setattr(cli, "DISPATCH", {"analyze_project": failing_tool})

        exit_code = cli.main(["analyze"])

        assert exit_code == 2
        out_text = capsys.readouterr().out
        output = json.loads(out_text)
        assert "quotes" in output["error"]
