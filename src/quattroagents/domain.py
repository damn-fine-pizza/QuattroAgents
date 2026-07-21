"""Provider-independent domain model for the Project Agent Factory.

Every dataclass here is a plain data contract: no I/O, no provider knowledge
(Claude/Codex), no persistence format opinions. Adapters, persistence, and
generation modules all import from here so the shape of an agent, skill,
decision, etc. is defined exactly once.

All dataclasses are constructed with keyword arguments and expose
`to_dict()`/`from_dict()` for JSON persistence (see persistence.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# --------------------------------------------------------------------------
# Shared enums
# --------------------------------------------------------------------------


class Model(StrEnum):
    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"
    INHERIT = "inherit"


class AgentMode(StrEnum):
    READ_ONLY = "read_only"
    WRITE = "write"


class AgentLifetime(StrEnum):
    PERMANENT = "permanent"
    TASK_TEMPORARY = "task_temporary"


class DefinitionSource(StrEnum):
    DEFAULT = "default"
    ADHOC = "adhoc"
    TASK_TEMPORARY = "task_temporary"


class GapType(StrEnum):
    MISSING_FACT = "missing_fact"
    MISSING_PREFERENCE = "missing_preference"
    MISSING_CONSTRAINT = "missing_constraint"
    MISSING_PRIORITY = "missing_priority"
    MISSING_WORKFLOW = "missing_workflow"
    MISSING_OWNERSHIP = "missing_ownership"
    MISSING_VALIDATION_RULE = "missing_validation_rule"
    MISSING_TOOL_POLICY = "missing_tool_policy"
    AMBIGUOUS_ARCHITECTURE = "ambiguous_architecture"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    STALE_DECISION = "stale_decision"


class GapStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class Priority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class QuestionType(StrEnum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    BOOLEAN = "boolean"
    FREE_TEXT = "free_text"
    ORDERED_CHOICE = "ordered_choice"
    NUMERIC = "numeric"
    PATH_SELECTION = "path_selection"
    AGENT_SELECTION = "agent_selection"
    TOOL_SELECTION = "tool_selection"


class AnswerClassification(StrEnum):
    FACT = "fact"
    PREFERENCE = "preference"
    CONSTRAINT = "constraint"
    PRIORITY = "priority"
    POLICY = "policy"
    WORKFLOW = "workflow"
    OWNERSHIP = "ownership"
    RISK_ACCEPTANCE = "risk_acceptance"
    VALIDATION_RULE = "validation_rule"
    TOOL_POLICY = "tool_policy"
    MODEL_POLICY = "model_policy"
    TEMPORARY_INSTRUCTION = "temporary_instruction"


class DecisionScope(StrEnum):
    PROJECT_WIDE = "project_wide"
    TASK_LOCAL = "task_local"
    TEMPORARY = "temporary"
    EXPERIMENTAL = "experimental"


class DecisionStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    UNCERTAIN = "uncertain"


class DecisionSourceType(StrEnum):
    USER = "user"
    REPOSITORY = "repository"
    INFERRED = "inferred"
    IMPORTED = "imported"


class SessionType(StrEnum):
    INITIAL_SETUP = "initial_setup"
    REPOSITORY_CHANGE = "repository_change"
    TASK_PREPARATION = "task_preparation"
    DECISION_REVIEW = "decision_review"
    TOOLING_CHANGE = "tooling_change"
    AGENT_REGENERATION = "agent_regeneration"
    MANUAL_REVIEW = "manual_review"


class SessionStatus(StrEnum):
    AWAITING_ANSWERS = "awaiting_answers"
    READY_FOR_CONFIRMATION = "ready_for_confirmation"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"


class ConflictType(StrEnum):
    USER_VS_REPOSITORY = "user_vs_repository"
    USER_VS_PREVIOUS = "user_vs_previous"
    DOC_VS_CODE = "doc_vs_code"
    USER_VS_USER = "user_vs_user"
    AGENT_VS_DECISION = "agent_vs_decision"
    TOOL_POLICY_VS_AVAILABILITY = "tool_policy_vs_availability"


class ConflictSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConflictStatus(StrEnum):
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"


# --------------------------------------------------------------------------
# Small helpers shared by every dataclass's (de)serialization
# --------------------------------------------------------------------------


def _enum_value(value: Any) -> Any:
    return value.value if isinstance(value, StrEnum) else value


# --------------------------------------------------------------------------
# Tool inventory
# --------------------------------------------------------------------------


@dataclass
class ToolDefinition:
    id: str
    availability: str  # "available" | "unavailable"
    source: str  # "builtin-claude" | "builtin-codex" | "mcp" | "cli" | "detected"
    capabilities: list[str] = field(default_factory=list)
    recommended_for: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "availability": self.availability,
            "source": self.source,
            "capabilities": list(self.capabilities),
            "recommended_for": list(self.recommended_for),
            "limitations": list(self.limitations),
            "version": self.version,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ToolDefinition:
        return ToolDefinition(
            id=data["id"],
            availability=data["availability"],
            source=data["source"],
            capabilities=list(data.get("capabilities", [])),
            recommended_for=list(data.get("recommended_for", [])),
            limitations=list(data.get("limitations", [])),
            version=data.get("version"),
        )


# --------------------------------------------------------------------------
# Agents
# --------------------------------------------------------------------------


@dataclass
class AgentPermissions:
    can_read_files: bool = True
    can_write_files: bool = False
    can_execute_commands: bool = False
    can_use_network: bool = False
    can_modify_git: bool = False
    can_create_commits: bool = False
    can_push: bool = False
    can_open_pr: bool = False
    can_modify_config: bool = False
    can_delete_files: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "can_read_files": self.can_read_files,
            "can_write_files": self.can_write_files,
            "can_execute_commands": self.can_execute_commands,
            "can_use_network": self.can_use_network,
            "can_modify_git": self.can_modify_git,
            "can_create_commits": self.can_create_commits,
            "can_push": self.can_push,
            "can_open_pr": self.can_open_pr,
            "can_modify_config": self.can_modify_config,
            "can_delete_files": self.can_delete_files,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> AgentPermissions:
        return AgentPermissions(**{k: bool(v) for k, v in data.items()})


@dataclass
class AgentDefinition:
    id: str  # stable kebab-case identifier, e.g. "repository-cartographer"
    description: str  # short one-line responsibility, used in canonical display format
    responsibilities: list[str] = field(default_factory=list)
    scope: str = ""
    when_to_use: str = ""
    when_not_to_use: str = ""
    expected_inputs: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    available_tools: list[str] = field(default_factory=list)
    mandatory_tools: list[str] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)
    relevant_paths: list[str] = field(default_factory=list)
    completion_criteria: list[str] = field(default_factory=list)
    escalation_criteria: list[str] = field(default_factory=list)
    preferred_model: Model = Model.HAIKU
    fallback_model: Model | None = None
    mode: AgentMode = AgentMode.READ_ONLY
    collaboration_notes: str = ""
    permissions: AgentPermissions = field(default_factory=AgentPermissions)
    lifetime: AgentLifetime = AgentLifetime.PERMANENT
    source: DefinitionSource = DefinitionSource.DEFAULT
    constraints: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    archetype_id: str | None = (
        None  # reference archetype this agent was derived from, e.g. "test-agent"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "responsibilities": list(self.responsibilities),
            "scope": self.scope,
            "when_to_use": self.when_to_use,
            "when_not_to_use": self.when_not_to_use,
            "expected_inputs": list(self.expected_inputs),
            "expected_outputs": list(self.expected_outputs),
            "available_tools": list(self.available_tools),
            "mandatory_tools": list(self.mandatory_tools),
            "forbidden_tools": list(self.forbidden_tools),
            "relevant_paths": list(self.relevant_paths),
            "completion_criteria": list(self.completion_criteria),
            "escalation_criteria": list(self.escalation_criteria),
            "preferred_model": _enum_value(self.preferred_model),
            "fallback_model": _enum_value(self.fallback_model),
            "mode": _enum_value(self.mode),
            "collaboration_notes": self.collaboration_notes,
            "permissions": self.permissions.to_dict(),
            "lifetime": _enum_value(self.lifetime),
            "source": _enum_value(self.source),
            "constraints": list(self.constraints),
            "required_skills": list(self.required_skills),
            "archetype_id": self.archetype_id,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> AgentDefinition:
        fallback = data.get("fallback_model")
        return AgentDefinition(
            id=data["id"],
            description=data["description"],
            responsibilities=list(data.get("responsibilities", [])),
            scope=data.get("scope", ""),
            when_to_use=data.get("when_to_use", ""),
            when_not_to_use=data.get("when_not_to_use", ""),
            expected_inputs=list(data.get("expected_inputs", [])),
            expected_outputs=list(data.get("expected_outputs", [])),
            available_tools=list(data.get("available_tools", [])),
            mandatory_tools=list(data.get("mandatory_tools", [])),
            forbidden_tools=list(data.get("forbidden_tools", [])),
            relevant_paths=list(data.get("relevant_paths", [])),
            completion_criteria=list(data.get("completion_criteria", [])),
            escalation_criteria=list(data.get("escalation_criteria", [])),
            preferred_model=Model(data.get("preferred_model", Model.HAIKU)),
            fallback_model=Model(fallback) if fallback else None,
            mode=AgentMode(data.get("mode", AgentMode.READ_ONLY)),
            collaboration_notes=data.get("collaboration_notes", ""),
            permissions=AgentPermissions.from_dict(data.get("permissions", {})),
            lifetime=AgentLifetime(data.get("lifetime", AgentLifetime.PERMANENT)),
            source=DefinitionSource(data.get("source", DefinitionSource.DEFAULT)),
            constraints=list(data.get("constraints", [])),
            required_skills=list(data.get("required_skills", [])),
            archetype_id=data.get("archetype_id"),
        )


# --------------------------------------------------------------------------
# Skills
# --------------------------------------------------------------------------


@dataclass
class SkillDefinition:
    id: str
    trigger: str
    workflow: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    validation_criteria: list[str] = field(default_factory=list)
    usable_by_agents: list[str] = field(default_factory=list)
    source: DefinitionSource = DefinitionSource.DEFAULT
    body: str | None = None  # pre-rendered body overrides workflow-based rendering

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "trigger": self.trigger,
            "workflow": list(self.workflow),
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "required_tools": list(self.required_tools),
            "validation_criteria": list(self.validation_criteria),
            "usable_by_agents": list(self.usable_by_agents),
            "source": _enum_value(self.source),
            "body": self.body,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SkillDefinition:
        return SkillDefinition(
            id=data["id"],
            trigger=data["trigger"],
            workflow=list(data.get("workflow", [])),
            inputs=list(data.get("inputs", [])),
            outputs=list(data.get("outputs", [])),
            required_tools=list(data.get("required_tools", [])),
            validation_criteria=list(data.get("validation_criteria", [])),
            usable_by_agents=list(data.get("usable_by_agents", [])),
            source=DefinitionSource(data.get("source", DefinitionSource.DEFAULT)),
            body=data.get("body"),
        )


# --------------------------------------------------------------------------
# Swarm
# --------------------------------------------------------------------------


@dataclass
class SwarmAgentStep:
    agent_id: str
    phase: str
    parallel_group: str | None = None
    depends_on: list[str] = field(default_factory=list)
    can_run_parallel_with: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "phase": self.phase,
            "parallel_group": self.parallel_group,
            "depends_on": list(self.depends_on),
            "can_run_parallel_with": list(self.can_run_parallel_with),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SwarmAgentStep:
        return SwarmAgentStep(
            agent_id=data["agent_id"],
            phase=data["phase"],
            parallel_group=data.get("parallel_group"),
            depends_on=list(data.get("depends_on", [])),
            can_run_parallel_with=list(data.get("can_run_parallel_with", [])),
        )


@dataclass
class SwarmDefinition:
    task_id: str
    goal: str
    agents: list[SwarmAgentStep] = field(default_factory=list)
    required_review_agents: list[str] = field(default_factory=list)
    completion_criteria: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "agents": [a.to_dict() for a in self.agents],
            "required_review_agents": list(self.required_review_agents),
            "completion_criteria": list(self.completion_criteria),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SwarmDefinition:
        return SwarmDefinition(
            task_id=data["task_id"],
            goal=data["goal"],
            agents=[SwarmAgentStep.from_dict(a) for a in data.get("agents", [])],
            required_review_agents=list(data.get("required_review_agents", [])),
            completion_criteria=list(data.get("completion_criteria", [])),
        )


# --------------------------------------------------------------------------
# Project profile (repository analysis output)
# --------------------------------------------------------------------------


@dataclass
class ProjectProfile:
    fingerprint: str
    languages: list[str] = field(default_factory=list)
    build_systems: list[str] = field(default_factory=list)
    test_frameworks: list[str] = field(default_factory=list)
    ci_systems: list[str] = field(default_factory=list)
    subsystems: list[str] = field(default_factory=list)
    coding_conventions: list[str] = field(default_factory=list)
    architecture_docs: list[str] = field(default_factory=list)
    tools: list[ToolDefinition] = field(default_factory=list)
    existing_claude_config: dict[str, Any] = field(default_factory=dict)
    existing_codex_config: dict[str, Any] = field(default_factory=dict)
    existing_mcp_servers: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    legacy_areas: list[str] = field(default_factory=list)
    analyzed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "languages": list(self.languages),
            "build_systems": list(self.build_systems),
            "test_frameworks": list(self.test_frameworks),
            "ci_systems": list(self.ci_systems),
            "subsystems": list(self.subsystems),
            "coding_conventions": list(self.coding_conventions),
            "architecture_docs": list(self.architecture_docs),
            "tools": [t.to_dict() for t in self.tools],
            "existing_claude_config": dict(self.existing_claude_config),
            "existing_codex_config": dict(self.existing_codex_config),
            "existing_mcp_servers": list(self.existing_mcp_servers),
            "risks": list(self.risks),
            "legacy_areas": list(self.legacy_areas),
            "analyzed_at": self.analyzed_at,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ProjectProfile:
        return ProjectProfile(
            fingerprint=data["fingerprint"],
            languages=list(data.get("languages", [])),
            build_systems=list(data.get("build_systems", [])),
            test_frameworks=list(data.get("test_frameworks", [])),
            ci_systems=list(data.get("ci_systems", [])),
            subsystems=list(data.get("subsystems", [])),
            coding_conventions=list(data.get("coding_conventions", [])),
            architecture_docs=list(data.get("architecture_docs", [])),
            tools=[ToolDefinition.from_dict(t) for t in data.get("tools", [])],
            existing_claude_config=dict(data.get("existing_claude_config", {})),
            existing_codex_config=dict(data.get("existing_codex_config", {})),
            existing_mcp_servers=list(data.get("existing_mcp_servers", [])),
            risks=list(data.get("risks", [])),
            legacy_areas=list(data.get("legacy_areas", [])),
            analyzed_at=data.get("analyzed_at", ""),
        )


# --------------------------------------------------------------------------
# Interview Engine domain: knowledge gaps, questions, answers, decisions
# --------------------------------------------------------------------------


@dataclass
class KnowledgeGap:
    id: str
    topic: str
    description: str
    gap_type: GapType
    evidence: list[str] = field(default_factory=list)
    impact: dict[str, str] = field(
        default_factory=dict
    )  # agents/skills/swarm/permissions -> high|medium|low
    confidence: float = 0.5
    status: GapStatus = GapStatus.OPEN
    priority: Priority = Priority.MEDIUM
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "description": self.description,
            "gap_type": _enum_value(self.gap_type),
            "evidence": list(self.evidence),
            "impact": dict(self.impact),
            "confidence": self.confidence,
            "status": _enum_value(self.status),
            "priority": _enum_value(self.priority),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> KnowledgeGap:
        return KnowledgeGap(
            id=data["id"],
            topic=data["topic"],
            description=data["description"],
            gap_type=GapType(data["gap_type"]),
            evidence=list(data.get("evidence", [])),
            impact=dict(data.get("impact", {})),
            confidence=float(data.get("confidence", 0.5)),
            status=GapStatus(data.get("status", GapStatus.OPEN)),
            priority=Priority(data.get("priority", Priority.MEDIUM)),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class QuestionOption:
    id: str
    label: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "label": self.label}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> QuestionOption:
        return QuestionOption(id=data["id"], label=data["label"])


@dataclass
class Question:
    id: str
    gap_id: str
    question: str
    type: QuestionType
    options: list[QuestionOption] = field(default_factory=list)
    allow_free_text: bool = False
    reason: str = ""
    evidence: list[str] = field(default_factory=list)
    impact: list[str] = field(default_factory=list)
    follow_up_of: str | None = None  # question_id this is an adaptive follow-up to
    depth: int = 0  # follow-up chain depth, 0 for a root question

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "gap_id": self.gap_id,
            "question": self.question,
            "type": _enum_value(self.type),
            "options": [o.to_dict() for o in self.options],
            "allow_free_text": self.allow_free_text,
            "reason": self.reason,
            "evidence": list(self.evidence),
            "impact": list(self.impact),
            "follow_up_of": self.follow_up_of,
            "depth": self.depth,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Question:
        return Question(
            id=data["id"],
            gap_id=data["gap_id"],
            question=data["question"],
            type=QuestionType(data["type"]),
            options=[QuestionOption.from_dict(o) for o in data.get("options", [])],
            allow_free_text=bool(data.get("allow_free_text", False)),
            reason=data.get("reason", ""),
            evidence=list(data.get("evidence", [])),
            impact=list(data.get("impact", [])),
            follow_up_of=data.get("follow_up_of"),
            depth=int(data.get("depth", 0)),
        )


@dataclass
class Answer:
    question_id: str
    value: str
    free_text: str = ""
    classification: list[AnswerClassification] = field(default_factory=list)
    source: str = "user"
    confidence: float = 1.0
    scope: list[str] = field(default_factory=list)
    valid_from: str = ""
    valid_until: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "value": self.value,
            "free_text": self.free_text,
            "classification": [_enum_value(c) for c in self.classification],
            "source": self.source,
            "confidence": self.confidence,
            "scope": list(self.scope),
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Answer:
        return Answer(
            question_id=data["question_id"],
            value=data["value"],
            free_text=data.get("free_text", ""),
            classification=[AnswerClassification(c) for c in data.get("classification", [])],
            source=data.get("source", "user"),
            confidence=float(data.get("confidence", 1.0)),
            scope=list(data.get("scope", [])),
            valid_from=data.get("valid_from", ""),
            valid_until=data.get("valid_until"),
        )


@dataclass
class DecisionSource:
    type: DecisionSourceType
    interview_session: str | None = None
    question_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": _enum_value(self.type),
            "interview_session": self.interview_session,
            "question_id": self.question_id,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DecisionSource:
        return DecisionSource(
            type=DecisionSourceType(data["type"]),
            interview_session=data.get("interview_session"),
            question_id=data.get("question_id"),
        )


@dataclass
class Decision:
    id: str
    title: str
    value: dict[str, Any]
    source: DecisionSource
    reason: str
    scope_paths: list[str] = field(default_factory=list)
    decision_scope: DecisionScope = DecisionScope.PROJECT_WIDE
    confidence: float = 1.0
    status: DecisionStatus = DecisionStatus.ACTIVE
    effects: dict[str, list[str]] = field(
        default_factory=dict
    )  # agents/skills/validations -> [ids]
    supersedes: str | None = None  # id of the decision this replaces
    superseded_by: str | None = None
    sensitivity: str = "normal"  # "normal" | "confidential"
    include_in_generated_files: bool = True
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "value": dict(self.value),
            "source": self.source.to_dict(),
            "reason": self.reason,
            "scope_paths": list(self.scope_paths),
            "decision_scope": _enum_value(self.decision_scope),
            "confidence": self.confidence,
            "status": _enum_value(self.status),
            "effects": {k: list(v) for k, v in self.effects.items()},
            "supersedes": self.supersedes,
            "superseded_by": self.superseded_by,
            "sensitivity": self.sensitivity,
            "include_in_generated_files": self.include_in_generated_files,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Decision:
        return Decision(
            id=data["id"],
            title=data["title"],
            value=dict(data.get("value", {})),
            source=DecisionSource.from_dict(data["source"]),
            reason=data.get("reason", ""),
            scope_paths=list(data.get("scope_paths", [])),
            decision_scope=DecisionScope(data.get("decision_scope", DecisionScope.PROJECT_WIDE)),
            confidence=float(data.get("confidence", 1.0)),
            status=DecisionStatus(data.get("status", DecisionStatus.ACTIVE)),
            effects={k: list(v) for k, v in data.get("effects", {}).items()},
            supersedes=data.get("supersedes"),
            superseded_by=data.get("superseded_by"),
            sensitivity=data.get("sensitivity", "normal"),
            include_in_generated_files=bool(data.get("include_in_generated_files", True)),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class InterviewSession:
    id: str
    type: SessionType
    project_fingerprint: str
    started_at: str
    completed_at: str | None = None
    status: SessionStatus = SessionStatus.AWAITING_ANSWERS
    knowledge_gaps: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    answers: list[Answer] = field(default_factory=list)
    generated_decisions: list[str] = field(default_factory=list)
    superseded_decisions: list[str] = field(default_factory=list)
    max_questions_per_batch: int = 5

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": _enum_value(self.type),
            "project_fingerprint": self.project_fingerprint,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": _enum_value(self.status),
            "knowledge_gaps": list(self.knowledge_gaps),
            "questions": list(self.questions),
            "answers": [a.to_dict() for a in self.answers],
            "generated_decisions": list(self.generated_decisions),
            "superseded_decisions": list(self.superseded_decisions),
            "max_questions_per_batch": self.max_questions_per_batch,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> InterviewSession:
        return InterviewSession(
            id=data["id"],
            type=SessionType(data["type"]),
            project_fingerprint=data["project_fingerprint"],
            started_at=data["started_at"],
            completed_at=data.get("completed_at"),
            status=SessionStatus(data.get("status", SessionStatus.AWAITING_ANSWERS)),
            knowledge_gaps=list(data.get("knowledge_gaps", [])),
            questions=list(data.get("questions", [])),
            answers=[Answer.from_dict(a) for a in data.get("answers", [])],
            generated_decisions=list(data.get("generated_decisions", [])),
            superseded_decisions=list(data.get("superseded_decisions", [])),
            max_questions_per_batch=int(data.get("max_questions_per_batch", 5)),
        )


@dataclass
class ConflictRecord:
    id: str
    type: ConflictType
    decision_id: str
    evidence: list[str] = field(default_factory=list)
    severity: ConflictSeverity = ConflictSeverity.MEDIUM
    status: ConflictStatus = ConflictStatus.UNRESOLVED
    possible_resolutions: list[str] = field(default_factory=list)
    resolution: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": _enum_value(self.type),
            "decision_id": self.decision_id,
            "evidence": list(self.evidence),
            "severity": _enum_value(self.severity),
            "status": _enum_value(self.status),
            "possible_resolutions": list(self.possible_resolutions),
            "resolution": self.resolution,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ConflictRecord:
        return ConflictRecord(
            id=data["id"],
            type=ConflictType(data["type"]),
            decision_id=data["decision_id"],
            evidence=list(data.get("evidence", [])),
            severity=ConflictSeverity(data.get("severity", ConflictSeverity.MEDIUM)),
            status=ConflictStatus(data.get("status", ConflictStatus.UNRESOLVED)),
            possible_resolutions=list(data.get("possible_resolutions", [])),
            resolution=data.get("resolution"),
        )
