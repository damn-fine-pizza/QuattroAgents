"""Tests for the domain.py module: dataclass defaults, serialization, and enums."""

import json

from quattroagents.domain import (
    AgentDefinition,
    AgentLifetime,
    AgentMode,
    AgentPermissions,
    Answer,
    AnswerClassification,
    ConflictRecord,
    ConflictSeverity,
    ConflictStatus,
    ConflictType,
    Decision,
    DecisionScope,
    DecisionSource,
    DecisionSourceType,
    DecisionStatus,
    DefinitionSource,
    GapStatus,
    GapType,
    InterviewSession,
    KnowledgeGap,
    Model,
    Priority,
    ProjectProfile,
    Question,
    QuestionOption,
    QuestionType,
    SessionStatus,
    SessionType,
    SkillDefinition,
    SwarmAgentStep,
    SwarmDefinition,
    ToolDefinition,
)

# --------------------------------------------------------------------------
# Enum value tests
# --------------------------------------------------------------------------


def test_model_enum_values() -> None:
    """Verify Model enum members have correct string values."""
    assert Model.HAIKU.value == "haiku"
    assert Model.SONNET.value == "sonnet"
    assert Model.OPUS.value == "opus"
    assert Model.INHERIT.value == "inherit"


def test_agent_mode_enum_values() -> None:
    """Verify AgentMode enum members have correct string values."""
    assert AgentMode.READ_ONLY.value == "read_only"
    assert AgentMode.WRITE.value == "write"


def test_agent_lifetime_enum_values() -> None:
    """Verify AgentLifetime enum members have correct string values."""
    assert AgentLifetime.PERMANENT.value == "permanent"
    assert AgentLifetime.TASK_TEMPORARY.value == "task_temporary"


def test_definition_source_enum_values() -> None:
    """Verify DefinitionSource enum members have correct string values."""
    assert DefinitionSource.DEFAULT.value == "default"
    assert DefinitionSource.ADHOC.value == "adhoc"
    assert DefinitionSource.TASK_TEMPORARY.value == "task_temporary"


def test_gap_type_enum_values() -> None:
    """Verify GapType enum members have correct string values."""
    assert GapType.MISSING_FACT.value == "missing_fact"
    assert GapType.MISSING_PREFERENCE.value == "missing_preference"
    assert GapType.CONFLICTING_EVIDENCE.value == "conflicting_evidence"


def test_gap_status_enum_values() -> None:
    """Verify GapStatus enum members have correct string values."""
    assert GapStatus.OPEN.value == "open"
    assert GapStatus.RESOLVED.value == "resolved"
    assert GapStatus.DISMISSED.value == "dismissed"


def test_priority_enum_values() -> None:
    """Verify Priority enum members have correct string values."""
    assert Priority.HIGH.value == "high"
    assert Priority.MEDIUM.value == "medium"
    assert Priority.LOW.value == "low"


def test_question_type_enum_values() -> None:
    """Verify QuestionType enum members have correct string values."""
    assert QuestionType.SINGLE_CHOICE.value == "single_choice"
    assert QuestionType.MULTIPLE_CHOICE.value == "multiple_choice"
    assert QuestionType.BOOLEAN.value == "boolean"
    assert QuestionType.FREE_TEXT.value == "free_text"


def test_answer_classification_enum_values() -> None:
    """Verify AnswerClassification enum members have correct string values."""
    assert AnswerClassification.FACT.value == "fact"
    assert AnswerClassification.PREFERENCE.value == "preference"
    assert AnswerClassification.CONSTRAINT.value == "constraint"


def test_decision_scope_enum_values() -> None:
    """Verify DecisionScope enum members have correct string values."""
    assert DecisionScope.PROJECT_WIDE.value == "project_wide"
    assert DecisionScope.TASK_LOCAL.value == "task_local"
    assert DecisionScope.TEMPORARY.value == "temporary"


def test_decision_status_enum_values() -> None:
    """Verify DecisionStatus enum members have correct string values."""
    assert DecisionStatus.ACTIVE.value == "active"
    assert DecisionStatus.SUPERSEDED.value == "superseded"
    assert DecisionStatus.UNCERTAIN.value == "uncertain"


def test_decision_source_type_enum_values() -> None:
    """Verify DecisionSourceType enum members have correct string values."""
    assert DecisionSourceType.USER.value == "user"
    assert DecisionSourceType.REPOSITORY.value == "repository"
    assert DecisionSourceType.INFERRED.value == "inferred"
    assert DecisionSourceType.IMPORTED.value == "imported"


def test_session_type_enum_values() -> None:
    """Verify SessionType enum members have correct string values."""
    assert SessionType.INITIAL_SETUP.value == "initial_setup"
    assert SessionType.REPOSITORY_CHANGE.value == "repository_change"
    assert SessionType.TASK_PREPARATION.value == "task_preparation"


def test_session_status_enum_values() -> None:
    """Verify SessionStatus enum members have correct string values."""
    assert SessionStatus.AWAITING_ANSWERS.value == "awaiting_answers"
    assert SessionStatus.READY_FOR_CONFIRMATION.value == "ready_for_confirmation"
    assert SessionStatus.CONFIRMED.value == "confirmed"


def test_conflict_type_enum_values() -> None:
    """Verify ConflictType enum members have correct string values."""
    assert ConflictType.USER_VS_REPOSITORY.value == "user_vs_repository"
    assert ConflictType.DOC_VS_CODE.value == "doc_vs_code"


def test_conflict_severity_enum_values() -> None:
    """Verify ConflictSeverity enum members have correct string values."""
    assert ConflictSeverity.LOW.value == "low"
    assert ConflictSeverity.MEDIUM.value == "medium"
    assert ConflictSeverity.HIGH.value == "high"


def test_conflict_status_enum_values() -> None:
    """Verify ConflictStatus enum members have correct string values."""
    assert ConflictStatus.UNRESOLVED.value == "unresolved"
    assert ConflictStatus.RESOLVED.value == "resolved"


# --------------------------------------------------------------------------
# Dataclass default tests
# --------------------------------------------------------------------------


def test_tool_definition_defaults() -> None:
    """Verify ToolDefinition defaults when constructed with required args only."""
    tool = ToolDefinition(id="test-tool", availability="available", source="builtin-claude")
    assert tool.capabilities == []
    assert tool.recommended_for == []
    assert tool.limitations == []
    assert tool.version is None


def test_agent_permissions_defaults() -> None:
    """Verify AgentPermissions defaults."""
    perms = AgentPermissions()
    assert perms.can_read_files is True
    assert perms.can_write_files is False
    assert perms.can_execute_commands is False
    assert perms.can_use_network is False
    assert perms.can_modify_git is False
    assert perms.can_create_commits is False
    assert perms.can_push is False
    assert perms.can_open_pr is False
    assert perms.can_modify_config is False
    assert perms.can_delete_files is False


def test_agent_definition_defaults() -> None:
    """Verify AgentDefinition defaults."""
    agent = AgentDefinition(id="test-agent", description="Test agent")
    assert agent.responsibilities == []
    assert agent.scope == ""
    assert agent.when_to_use == ""
    assert agent.when_not_to_use == ""
    assert agent.expected_inputs == []
    assert agent.expected_outputs == []
    assert agent.available_tools == []
    assert agent.mandatory_tools == []
    assert agent.forbidden_tools == []
    assert agent.relevant_paths == []
    assert agent.completion_criteria == []
    assert agent.escalation_criteria == []
    assert agent.preferred_model == Model.HAIKU
    assert agent.fallback_model is None
    assert agent.mode == AgentMode.READ_ONLY
    assert agent.collaboration_notes == ""
    assert isinstance(agent.permissions, AgentPermissions)
    assert agent.lifetime == AgentLifetime.PERMANENT
    assert agent.source == DefinitionSource.DEFAULT
    assert agent.constraints == []
    assert agent.required_skills == []


def test_skill_definition_defaults() -> None:
    """Verify SkillDefinition defaults."""
    skill = SkillDefinition(id="test-skill", trigger="on_init")
    assert skill.workflow == []
    assert skill.inputs == []
    assert skill.outputs == []
    assert skill.required_tools == []
    assert skill.validation_criteria == []
    assert skill.usable_by_agents == []
    assert skill.source == DefinitionSource.DEFAULT
    assert skill.body is None


def test_swarm_agent_step_defaults() -> None:
    """Verify SwarmAgentStep defaults."""
    step = SwarmAgentStep(agent_id="test-agent", phase="phase1")
    assert step.parallel_group is None
    assert step.depends_on == []
    assert step.can_run_parallel_with == []


def test_swarm_definition_defaults() -> None:
    """Verify SwarmDefinition defaults."""
    swarm = SwarmDefinition(task_id="test-task", goal="Test goal")
    assert swarm.agents == []
    assert swarm.required_review_agents == []
    assert swarm.completion_criteria == []


def test_project_profile_defaults() -> None:
    """Verify ProjectProfile defaults."""
    profile = ProjectProfile(fingerprint="abc123")
    assert profile.languages == []
    assert profile.build_systems == []
    assert profile.test_frameworks == []
    assert profile.ci_systems == []
    assert profile.subsystems == []
    assert profile.coding_conventions == []
    assert profile.architecture_docs == []
    assert profile.tools == []
    assert profile.existing_claude_config == {}
    assert profile.existing_codex_config == {}
    assert profile.existing_mcp_servers == []
    assert profile.risks == []
    assert profile.legacy_areas == []
    assert profile.analyzed_at == ""


def test_knowledge_gap_defaults() -> None:
    """Verify KnowledgeGap defaults."""
    gap = KnowledgeGap(
        id="gap1",
        topic="Architecture",
        description="Missing architecture info",
        gap_type=GapType.AMBIGUOUS_ARCHITECTURE,
    )
    assert gap.evidence == []
    assert gap.impact == {}
    assert gap.confidence == 0.5
    assert gap.status == GapStatus.OPEN
    assert gap.priority == Priority.MEDIUM
    assert gap.created_at == ""
    assert gap.updated_at == ""


def test_question_defaults() -> None:
    """Verify Question defaults."""
    question = Question(
        id="q1",
        gap_id="gap1",
        question="What is the architecture?",
        type=QuestionType.FREE_TEXT,
    )
    assert question.options == []
    assert question.allow_free_text is False
    assert question.reason == ""
    assert question.evidence == []
    assert question.impact == []
    assert question.follow_up_of is None
    assert question.depth == 0


def test_answer_defaults() -> None:
    """Verify Answer defaults."""
    answer = Answer(question_id="q1", value="yes")
    assert answer.free_text == ""
    assert answer.classification == []
    assert answer.source == "user"
    assert answer.confidence == 1.0
    assert answer.scope == []
    assert answer.valid_from == ""
    assert answer.valid_until is None


def test_decision_source_defaults() -> None:
    """Verify DecisionSource defaults."""
    source = DecisionSource(type=DecisionSourceType.USER)
    assert source.interview_session is None
    assert source.question_id is None


def test_decision_defaults() -> None:
    """Verify Decision defaults."""
    source = DecisionSource(type=DecisionSourceType.USER)
    decision = Decision(
        id="dec1",
        title="Test decision",
        value={"key": "value"},
        source=source,
        reason="Test reason",
    )
    assert decision.scope_paths == []
    assert decision.decision_scope == DecisionScope.PROJECT_WIDE
    assert decision.confidence == 1.0
    assert decision.status == DecisionStatus.ACTIVE
    assert decision.effects == {}
    assert decision.supersedes is None
    assert decision.superseded_by is None
    assert decision.sensitivity == "normal"
    assert decision.include_in_generated_files is True
    assert decision.created_at == ""
    assert decision.updated_at == ""


def test_interview_session_defaults() -> None:
    """Verify InterviewSession defaults."""
    session = InterviewSession(
        id="sess1",
        type=SessionType.INITIAL_SETUP,
        project_fingerprint="abc123",
        started_at="2026-01-01T00:00:00Z",
    )
    assert session.completed_at is None
    assert session.status == SessionStatus.AWAITING_ANSWERS
    assert session.knowledge_gaps == []
    assert session.questions == []
    assert session.answers == []
    assert session.generated_decisions == []
    assert session.superseded_decisions == []
    assert session.max_questions_per_batch == 5


def test_conflict_record_defaults() -> None:
    """Verify ConflictRecord defaults."""
    conflict = ConflictRecord(
        id="conf1",
        type=ConflictType.USER_VS_REPOSITORY,
        decision_id="dec1",
    )
    assert conflict.evidence == []
    assert conflict.severity == ConflictSeverity.MEDIUM
    assert conflict.status == ConflictStatus.UNRESOLVED
    assert conflict.possible_resolutions == []
    assert conflict.resolution is None


# --------------------------------------------------------------------------
# Round-trip serialization tests
# --------------------------------------------------------------------------


def test_tool_definition_roundtrip() -> None:
    """Verify ToolDefinition round-trip through to_dict/from_dict."""
    tool = ToolDefinition(
        id="search-tool",
        availability="available",
        source="mcp",
        capabilities=["search", "index"],
        recommended_for=["query", "analysis"],
        limitations=["no_real_time", "rate_limited"],
        version="2.1.0",
    )
    reconstructed = ToolDefinition.from_dict(tool.to_dict())
    assert reconstructed == tool


def test_agent_permissions_roundtrip() -> None:
    """Verify AgentPermissions round-trip."""
    perms = AgentPermissions(
        can_read_files=True,
        can_write_files=True,
        can_execute_commands=True,
        can_use_network=False,
        can_modify_git=True,
        can_create_commits=True,
        can_push=False,
        can_open_pr=True,
        can_modify_config=False,
        can_delete_files=False,
    )
    reconstructed = AgentPermissions.from_dict(perms.to_dict())
    assert reconstructed == perms


def test_agent_definition_roundtrip() -> None:
    """Verify AgentDefinition round-trip with nested AgentPermissions."""
    agent = AgentDefinition(
        id="code-reviewer",
        description="Reviews code changes",
        responsibilities=["review", "approve"],
        scope="Pull requests",
        when_to_use="After commit",
        when_not_to_use="During planning",
        expected_inputs=["diff", "context"],
        expected_outputs=["feedback", "approval"],
        available_tools=["git", "review-tool"],
        mandatory_tools=["git"],
        forbidden_tools=["rm"],
        relevant_paths=["src/", "tests/"],
        completion_criteria=["approved", "documented"],
        escalation_criteria=["complex_change"],
        preferred_model=Model.SONNET,
        fallback_model=Model.HAIKU,
        mode=AgentMode.WRITE,
        collaboration_notes="Coordinate with maintainers",
        permissions=AgentPermissions(
            can_read_files=True,
            can_write_files=False,
            can_execute_commands=True,
        ),
        lifetime=AgentLifetime.TASK_TEMPORARY,
        source=DefinitionSource.ADHOC,
        constraints=["max_tokens=5000"],
        required_skills=["python", "git"],
    )
    reconstructed = AgentDefinition.from_dict(agent.to_dict())
    assert reconstructed == agent


def test_skill_definition_roundtrip() -> None:
    """Verify SkillDefinition round-trip."""
    skill = SkillDefinition(
        id="code-analysis",
        trigger="on_commit",
        workflow=["analyze", "report"],
        inputs=["code"],
        outputs=["report"],
        required_tools=["analyzer"],
        validation_criteria=["report_generated"],
        usable_by_agents=["reviewer", "auditor"],
        source=DefinitionSource.TASK_TEMPORARY,
        body="custom body",
    )
    reconstructed = SkillDefinition.from_dict(skill.to_dict())
    assert reconstructed == skill


def test_swarm_agent_step_roundtrip() -> None:
    """Verify SwarmAgentStep round-trip."""
    step = SwarmAgentStep(
        agent_id="analyzer",
        phase="analysis",
        parallel_group="group1",
        depends_on=["setup"],
        can_run_parallel_with=["validator"],
    )
    reconstructed = SwarmAgentStep.from_dict(step.to_dict())
    assert reconstructed == step


def test_swarm_definition_roundtrip() -> None:
    """Verify SwarmDefinition round-trip with nested SwarmAgentStep."""
    swarm = SwarmDefinition(
        task_id="code-review-task",
        goal="Review all pull requests",
        agents=[
            SwarmAgentStep(
                agent_id="analyzer",
                phase="phase1",
                depends_on=[],
                can_run_parallel_with=["formatter"],
            ),
            SwarmAgentStep(
                agent_id="formatter",
                phase="phase1",
                parallel_group="first",
                depends_on=[],
            ),
        ],
        required_review_agents=["senior-reviewer"],
        completion_criteria=["all_approved"],
    )
    reconstructed = SwarmDefinition.from_dict(swarm.to_dict())
    assert reconstructed == swarm


def test_project_profile_roundtrip() -> None:
    """Verify ProjectProfile round-trip with nested ToolDefinition."""
    profile = ProjectProfile(
        fingerprint="project-2026",
        languages=["python", "typescript"],
        build_systems=["poetry", "npm"],
        test_frameworks=["pytest", "jest"],
        ci_systems=["github-actions"],
        subsystems=["api", "ui"],
        coding_conventions=["pep8", "eslint"],
        architecture_docs=["ADR1", "ADR2"],
        tools=[
            ToolDefinition(
                id="linter",
                availability="available",
                source="builtin-claude",
                capabilities=["lint"],
            ),
        ],
        existing_claude_config={"version": "1.0"},
        existing_codex_config={"model": "latest"},
        existing_mcp_servers=["git-server", "fs-server"],
        risks=["legacy_code"],
        legacy_areas=["old_module"],
        analyzed_at="2026-01-01T00:00:00Z",
    )
    reconstructed = ProjectProfile.from_dict(profile.to_dict())
    assert reconstructed == profile


def test_knowledge_gap_roundtrip() -> None:
    """Verify KnowledgeGap round-trip."""
    gap = KnowledgeGap(
        id="gap-arch",
        topic="Architecture",
        description="Missing architecture documentation",
        gap_type=GapType.AMBIGUOUS_ARCHITECTURE,
        evidence=["missing_adr", "unclear_diagrams"],
        impact={"agents": "high", "skills": "medium"},
        confidence=0.7,
        status=GapStatus.OPEN,
        priority=Priority.HIGH,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
    )
    reconstructed = KnowledgeGap.from_dict(gap.to_dict())
    assert reconstructed == gap


def test_question_roundtrip() -> None:
    """Verify Question round-trip with nested QuestionOption."""
    question = Question(
        id="q-arch-pattern",
        gap_id="gap-arch",
        question="What's the main architectural pattern?",
        type=QuestionType.SINGLE_CHOICE,
        options=[
            QuestionOption(id="opt1", label="MVC"),
            QuestionOption(id="opt2", label="Microservices"),
        ],
        allow_free_text=True,
        reason="Need to understand the current architecture",
        evidence=["codebase_structure"],
        impact=["agent_capabilities", "skill_design"],
        follow_up_of="q-scope",
        depth=1,
    )
    reconstructed = Question.from_dict(question.to_dict())
    assert reconstructed == question


def test_answer_roundtrip() -> None:
    """Verify Answer round-trip."""
    answer = Answer(
        question_id="q-arch",
        value="microservices",
        free_text="Multiple services deployed independently",
        classification=[AnswerClassification.FACT, AnswerClassification.CONSTRAINT],
        source="repository",
        confidence=0.9,
        scope=["backend"],
        valid_from="2026-01-01T00:00:00Z",
        valid_until="2026-12-31T23:59:59Z",
    )
    reconstructed = Answer.from_dict(answer.to_dict())
    assert reconstructed == answer


def test_decision_source_roundtrip() -> None:
    """Verify DecisionSource round-trip."""
    source = DecisionSource(
        type=DecisionSourceType.REPOSITORY,
        interview_session="sess-001",
        question_id="q-arch",
    )
    reconstructed = DecisionSource.from_dict(source.to_dict())
    assert reconstructed == source


def test_decision_roundtrip() -> None:
    """Verify Decision round-trip with nested DecisionSource."""
    source = DecisionSource(
        type=DecisionSourceType.USER,
        interview_session="sess-001",
        question_id="q-arch",
    )
    decision = Decision(
        id="dec-arch",
        title="Adopt microservices architecture",
        value={"pattern": "microservices", "deployment": "kubernetes"},
        source=source,
        reason="Scalability and team independence",
        scope_paths=["backend/", "deployment/"],
        decision_scope=DecisionScope.PROJECT_WIDE,
        confidence=0.95,
        status=DecisionStatus.ACTIVE,
        effects={"agents": ["arch-reviewer"], "skills": ["deployment-skill"]},
        supersedes="dec-monolith",
        superseded_by=None,
        sensitivity="normal",
        include_in_generated_files=True,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
    )
    reconstructed = Decision.from_dict(decision.to_dict())
    assert reconstructed == decision


def test_interview_session_roundtrip() -> None:
    """Verify InterviewSession round-trip with nested Answer."""
    session = InterviewSession(
        id="sess-001",
        type=SessionType.INITIAL_SETUP,
        project_fingerprint="proj-2026",
        started_at="2026-01-01T00:00:00Z",
        completed_at="2026-01-01T02:00:00Z",
        status=SessionStatus.COMPLETED,
        knowledge_gaps=["gap-1", "gap-2"],
        questions=["q-1", "q-2"],
        answers=[
            Answer(
                question_id="q-1",
                value="yes",
                classification=[AnswerClassification.PREFERENCE],
            ),
        ],
        generated_decisions=["dec-1", "dec-2"],
        superseded_decisions=["old-dec-1"],
        max_questions_per_batch=10,
    )
    reconstructed = InterviewSession.from_dict(session.to_dict())
    assert reconstructed == session


def test_conflict_record_roundtrip() -> None:
    """Verify ConflictRecord round-trip."""
    conflict = ConflictRecord(
        id="conf-001",
        type=ConflictType.USER_VS_PREVIOUS,
        decision_id="dec-arch",
        evidence=["user_preference", "old_decision"],
        severity=ConflictSeverity.HIGH,
        status=ConflictStatus.RESOLVED,
        possible_resolutions=["accept_new", "revert"],
        resolution="accept_new",
    )
    reconstructed = ConflictRecord.from_dict(conflict.to_dict())
    assert reconstructed == conflict


# --------------------------------------------------------------------------
# Decision supersedes/superseded_by tests
# --------------------------------------------------------------------------


def test_decision_supersedes_roundtrip() -> None:
    """Verify Decision supersedes/superseded_by round-trip correctly."""
    source1 = DecisionSource(type=DecisionSourceType.REPOSITORY)
    source2 = DecisionSource(type=DecisionSourceType.USER)

    old_decision = Decision(
        id="dec-v1",
        title="Version 1 decision",
        value={"version": "1"},
        source=source1,
        reason="Initial",
        status=DecisionStatus.SUPERSEDED,
        superseded_by="dec-v2",
    )

    new_decision = Decision(
        id="dec-v2",
        title="Version 2 decision",
        value={"version": "2"},
        source=source2,
        reason="Improvement",
        status=DecisionStatus.ACTIVE,
        supersedes="dec-v1",
    )

    old_reconstructed = Decision.from_dict(old_decision.to_dict())
    new_reconstructed = Decision.from_dict(new_decision.to_dict())

    assert old_reconstructed.superseded_by == "dec-v2"
    assert old_reconstructed.status == DecisionStatus.SUPERSEDED
    assert new_reconstructed.supersedes == "dec-v1"
    assert new_reconstructed.status == DecisionStatus.ACTIVE


# --------------------------------------------------------------------------
# JSON serialization tests
# --------------------------------------------------------------------------


def test_agent_definition_json_serializable() -> None:
    """Verify AgentDefinition.to_dict() output is JSON-serializable."""
    agent = AgentDefinition(
        id="test-agent",
        description="Test",
        preferred_model=Model.SONNET,
        mode=AgentMode.WRITE,
        permissions=AgentPermissions(can_write_files=True),
    )
    json_str = json.dumps(agent.to_dict())
    assert isinstance(json_str, str)
    reconstructed_data = json.loads(json_str)
    assert reconstructed_data["id"] == "test-agent"


def test_skill_definition_json_serializable() -> None:
    """Verify SkillDefinition.to_dict() output is JSON-serializable."""
    skill = SkillDefinition(
        id="test-skill",
        trigger="on_start",
        source=DefinitionSource.ADHOC,
    )
    json_str = json.dumps(skill.to_dict())
    assert isinstance(json_str, str)
    reconstructed_data = json.loads(json_str)
    assert reconstructed_data["id"] == "test-skill"


def test_swarm_definition_json_serializable() -> None:
    """Verify SwarmDefinition.to_dict() output is JSON-serializable."""
    swarm = SwarmDefinition(
        task_id="task1",
        goal="Test swarm",
        agents=[
            SwarmAgentStep(agent_id="a1", phase="p1"),
            SwarmAgentStep(agent_id="a2", phase="p2"),
        ],
    )
    json_str = json.dumps(swarm.to_dict())
    assert isinstance(json_str, str)
    reconstructed_data = json.loads(json_str)
    assert reconstructed_data["task_id"] == "task1"


def test_project_profile_json_serializable() -> None:
    """Verify ProjectProfile.to_dict() output is JSON-serializable."""
    profile = ProjectProfile(
        fingerprint="proj123",
        languages=["python"],
        tools=[ToolDefinition(id="t1", availability="available", source="builtin-claude")],
    )
    json_str = json.dumps(profile.to_dict())
    assert isinstance(json_str, str)
    reconstructed_data = json.loads(json_str)
    assert reconstructed_data["fingerprint"] == "proj123"


def test_knowledge_gap_json_serializable() -> None:
    """Verify KnowledgeGap.to_dict() output is JSON-serializable."""
    gap = KnowledgeGap(
        id="gap1",
        topic="Topic",
        description="Description",
        gap_type=GapType.MISSING_FACT,
        impact={"agents": "high"},
    )
    json_str = json.dumps(gap.to_dict())
    assert isinstance(json_str, str)
    reconstructed_data = json.loads(json_str)
    assert reconstructed_data["id"] == "gap1"


def test_question_json_serializable() -> None:
    """Verify Question.to_dict() output is JSON-serializable."""
    question = Question(
        id="q1",
        gap_id="gap1",
        question="Test question?",
        type=QuestionType.BOOLEAN,
        options=[QuestionOption(id="y", label="Yes")],
    )
    json_str = json.dumps(question.to_dict())
    assert isinstance(json_str, str)
    reconstructed_data = json.loads(json_str)
    assert reconstructed_data["id"] == "q1"


def test_answer_json_serializable() -> None:
    """Verify Answer.to_dict() output is JSON-serializable."""
    answer = Answer(
        question_id="q1",
        value="yes",
        classification=[AnswerClassification.FACT],
    )
    json_str = json.dumps(answer.to_dict())
    assert isinstance(json_str, str)
    reconstructed_data = json.loads(json_str)
    assert reconstructed_data["question_id"] == "q1"


def test_decision_json_serializable() -> None:
    """Verify Decision.to_dict() output is JSON-serializable."""
    decision = Decision(
        id="dec1",
        title="Test decision",
        value={"key": "value"},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Test reason",
        effects={"agents": ["a1", "a2"]},
    )
    json_str = json.dumps(decision.to_dict())
    assert isinstance(json_str, str)
    reconstructed_data = json.loads(json_str)
    assert reconstructed_data["id"] == "dec1"


def test_interview_session_json_serializable() -> None:
    """Verify InterviewSession.to_dict() output is JSON-serializable."""
    session = InterviewSession(
        id="sess1",
        type=SessionType.TASK_PREPARATION,
        project_fingerprint="proj1",
        started_at="2026-01-01T00:00:00Z",
        answers=[Answer(question_id="q1", value="answer")],
    )
    json_str = json.dumps(session.to_dict())
    assert isinstance(json_str, str)
    reconstructed_data = json.loads(json_str)
    assert reconstructed_data["id"] == "sess1"


def test_conflict_record_json_serializable() -> None:
    """Verify ConflictRecord.to_dict() output is JSON-serializable."""
    conflict = ConflictRecord(
        id="conf1",
        type=ConflictType.USER_VS_REPOSITORY,
        decision_id="dec1",
        evidence=["evidence1"],
    )
    json_str = json.dumps(conflict.to_dict())
    assert isinstance(json_str, str)
    reconstructed_data = json.loads(json_str)
    assert reconstructed_data["id"] == "conf1"
