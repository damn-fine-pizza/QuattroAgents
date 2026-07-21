"""Canonical text formatting for agent display lines.

Format: <role> (<tier>)

Valid example: cartographer (1)

`role` is a short, generic label for what the agent does (not its
`AgentDefinition.id`); `tier` is a single digit 1-4 encoding the agent's
preferred model: 1=haiku, 2=sonnet, 3=opus, 4=inherit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .domain import Model

if TYPE_CHECKING:
    from .domain import AgentDefinition


ROLE_LABELS: dict[str, str] = {
    "project-orchestrator": "orchestrator",
    "repository-cartographer": "cartographer",
    "architecture-guardian": "architect",
    "implementation-agent": "dev",
    "test-agent": "tester",
    "bdd-feature-agent": "bdd",
    "code-reviewer": "reviewer",
    "documentation-agent": "docs",
    "dependency-agent": "deps",
    "ci-build-agent": "ci",
    "performance-agent": "perf",
    "security-reviewer": "security",
    "release-agent": "release",
}

DEFAULT_ROLE = "generic"

TIER_BY_MODEL: dict[Model, str] = {
    Model.HAIKU: "1",
    Model.SONNET: "2",
    Model.OPUS: "3",
    Model.INHERIT: "4",
}

DEFAULT_TIER = "4"

AGENT_FILE_PREFIX = "qag-"


def agent_file_stem(agent_id: str) -> str:
    """Filesystem/config identity for a generated agent, distinct from its internal id.

    Generated agent files (and the name embedded in them) carry a `qag-`
    prefix so they're recognizable as QuattroAgents output alongside
    hand-authored agents in the same directory. `AgentDefinition.id` itself
    stays unprefixed — it's the stable internal key used for selection rules,
    decision effects, and swarm references.
    """
    return f"{AGENT_FILE_PREFIX}{agent_id}"


MANUAL_MODEL_TAG_PATTERN = re.compile(r"^\([^()]+\)\s")


def agent_display_description(agent: AgentDefinition) -> str:
    """Render-time `(model)` prefix for an agent's description.

    Mirrors `agent_file_stem`: `AgentDefinition.description` itself stays
    untagged so it can't go stale if `preferred_model` changes downstream of
    a decision after the description was written — the tag is computed
    fresh from `agent.preferred_model` at render time instead.

    If `description` already starts with a parenthesized tag (e.g. a
    hand-authored override), it is left as-is rather than double-wrapped;
    `validate_generated_configuration` flags that case on its own so a
    stale/mismatched pre-existing tag can't hide silently behind a second,
    correct one.
    """
    if MANUAL_MODEL_TAG_PATTERN.match(agent.description):
        return agent.description
    return f"({agent.preferred_model.value}) {agent.description}"


@dataclass
class AgentFormatConfig:
    allowed_tiers: list[str] = field(default_factory=lambda: ["1", "2", "3", "4"])
    role_minimum_length: int = 2
    role_maximum_length: int = 40


@dataclass
class FormatViolation:
    code: str
    message: str
    found: str
    expected: str | None = None


@dataclass
class ValidationResult:
    valid: bool
    violations: list[FormatViolation] = field(default_factory=list)
    role: str | None = None
    tier: str | None = None


@dataclass
class NormalizationResult:
    changed: bool
    normalized_line: str | None = None
    reason: str | None = None


def parse_agent_display_line(
    line: str, config: AgentFormatConfig | None = None
) -> ValidationResult:
    """Parse and validate a line against the canonical agent format.

    Uses a strict regex first. On failure, attempts specific diagnostics.
    On success, performs tier and role length validation.
    """
    if config is None:
        config = AgentFormatConfig()

    violations: list[FormatViolation] = []
    role: str | None = None
    tier: str | None = None

    strict_pattern = r"^(?P<role>[a-z][a-z0-9+/ -]*) \((?P<tier>[^()]*)\)$"
    match = re.match(strict_pattern, line)

    if match:
        role = match.group("role")
        tier = match.group("tier")

        if not tier:
            violations.append(
                FormatViolation(
                    code="missing_tier",
                    message="Tier cannot be empty inside parentheses",
                    found=line,
                )
            )
        elif tier not in config.allowed_tiers:
            violations.append(
                FormatViolation(
                    code="invalid_tier",
                    message=f"Tier '{tier}' is not in allowed_tiers: {config.allowed_tiers}",
                    found=line,
                )
            )

        if not role or not role.strip():
            violations.append(
                FormatViolation(
                    code="invalid_role",
                    message="Role cannot be empty",
                    found=line,
                )
            )
        else:
            role_len = len(role.strip())
            if role_len < config.role_minimum_length:
                violations.append(
                    FormatViolation(
                        code="role_too_short",
                        message=f"Role is {role_len} characters; minimum is {config.role_minimum_length}",
                        found=line,
                    )
                )
            elif role_len > config.role_maximum_length:
                violations.append(
                    FormatViolation(
                        code="role_too_long",
                        message=f"Role is {role_len} characters; maximum is {config.role_maximum_length}",
                        found=line,
                    )
                )

    else:
        bracket_pattern = r"\[([^\[\]]+)\]"
        if re.search(bracket_pattern, line):
            violations.append(
                FormatViolation(
                    code="malformed_delimiters",
                    message="Brackets [ ] used instead of parentheses ( )",
                    found=line,
                )
            )
        else:
            role_pattern = r"^([a-z][a-z0-9+/ -]*)"
            role_match = re.match(role_pattern, line)
            if not role_match:
                violations.append(
                    FormatViolation(
                        code="invalid_role",
                        message="Role must be lowercase, starting with a letter",
                        found=line,
                    )
                )
            else:
                if "(" in line or ")" in line:
                    if " (" not in line or not line.endswith(")"):
                        violations.append(
                            FormatViolation(
                                code="invalid_spacing",
                                message="Tier must be wrapped in ( ) preceded by exactly one space",
                                found=line,
                            )
                        )
                    else:
                        violations.append(
                            FormatViolation(
                                code="malformed_delimiters",
                                message="Parentheses are malformed or not properly closed",
                                found=line,
                            )
                        )
                else:
                    violations.append(
                        FormatViolation(
                            code="missing_tier",
                            message="Missing tier specification in parentheses (...)",
                            found=line,
                        )
                    )

    return ValidationResult(
        valid=(len(violations) == 0),
        violations=violations,
        role=role,
        tier=tier,
    )


def render_agent_display(agent: AgentDefinition) -> str:
    """Render an AgentDefinition as a canonical display line."""
    role = ROLE_LABELS.get(agent.archetype_id or agent.id, DEFAULT_ROLE)
    tier = TIER_BY_MODEL.get(agent.preferred_model, DEFAULT_TIER)
    return f"{role} ({tier})"


def normalize_agent_display_line(
    line: str, config: AgentFormatConfig | None = None
) -> NormalizationResult:
    """Normalize unambiguous format violations.

    Only fixes:
    - Brackets instead of parentheses: role [tier] -> role (tier)
    - Missing/extra spaces around parentheses: role(tier), role (tier)desc -> role (tier)
    Does not invent a missing role or tier.
    """
    if config is None:
        config = AgentFormatConfig()

    result = parse_agent_display_line(line, config)
    if result.valid:
        return NormalizationResult(changed=False, normalized_line=line)

    violation_codes = {v.code for v in result.violations}

    if "missing_tier" in violation_codes or "invalid_role" in violation_codes:
        reasons = []
        if "missing_tier" in violation_codes:
            reasons.append("missing tier")
        if "invalid_role" in violation_codes:
            reasons.append("invalid role")
        return NormalizationResult(changed=False, normalized_line=None, reason=": ".join(reasons))

    bracket_as_paren_pattern = r"^(?P<role>[a-z][a-z0-9+/ -]*)\s*\[(?P<tier>[^\[\]]+)\]\s*$"
    bracket_match = re.match(bracket_as_paren_pattern, line)
    if bracket_match:
        fixed = f"{bracket_match.group('role')} ({bracket_match.group('tier')})"
        return NormalizationResult(changed=True, normalized_line=fixed)

    paren_pattern = r"^(?P<role>[a-z][a-z0-9+/ -]*)\s*\((?P<tier>[^()]+)\)\s*$"
    paren_match = re.match(paren_pattern, line)
    if paren_match:
        role = paren_match.group("role")
        tier = paren_match.group("tier")
        if role.strip() and tier:
            fixed = f"{role.strip()} ({tier})"
            if fixed != line:
                return NormalizationResult(changed=True, normalized_line=fixed)
            return NormalizationResult(changed=False, normalized_line=line)

    return NormalizationResult(
        changed=False, normalized_line=None, reason="ambiguous: cannot safely auto-fix"
    )


def diagnose_agent_display_line(line: str, config: AgentFormatConfig | None = None) -> str:
    """Produce a human-readable diagnostic message."""
    if config is None:
        config = AgentFormatConfig()

    result = parse_agent_display_line(line, config)
    if result.valid:
        return "Valid agent format."

    lines = [
        "Invalid agent format",
        "",
        "Found:",
        line,
        "",
        "Expected:",
        "<role> (<tier>)",
        "",
        "Errors:",
    ]
    for violation in result.violations:
        lines.append(f"- {violation.code}: {violation.message}")

    return "\n".join(lines)


class AgentDisplayFormatValidator:
    """Convenience wrapper for agent display format operations."""

    def __init__(self, config: AgentFormatConfig | None = None) -> None:
        self.config = config if config is not None else AgentFormatConfig()

    def validate(self, line: str) -> ValidationResult:
        """Validate a display line."""
        return parse_agent_display_line(line, self.config)

    def normalize(self, line: str) -> NormalizationResult:
        """Normalize a display line."""
        return normalize_agent_display_line(line, self.config)

    def render(self, agent: AgentDefinition) -> str:
        """Render an agent definition."""
        return render_agent_display(agent)

    def diagnose(self, line: str) -> str:
        """Diagnose a display line."""
        return diagnose_agent_display_line(line, self.config)
