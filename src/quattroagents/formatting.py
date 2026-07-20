"""Canonical text formatting for agent display lines.

Format: <agent-name> [<model>] <description>

Valid example: repository-cartographer [haiku] Analizza struttura, dipendenze e confini del repository.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .domain import AgentDefinition


@dataclass
class AgentFormatConfig:
    allowed_models: list[str] = field(
        default_factory=lambda: ["haiku", "sonnet", "opus", "inherit"]
    )
    model_aliases: dict[str, str] = field(
        default_factory=lambda: {
            "claude-haiku": "haiku",
            "claude-sonnet": "sonnet",
            "claude-opus": "opus",
        }
    )
    description_minimum_length: int = 12
    description_maximum_length: int = 180


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
    agent_name: str | None = None
    model: str | None = None
    description: str | None = None


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
    On success, performs model and description length validation.
    """
    if config is None:
        config = AgentFormatConfig()

    violations: list[FormatViolation] = []
    agent_name: str | None = None
    model: str | None = None
    description: str | None = None

    strict_pattern = (
        r"^(?P<name>[a-z][a-z0-9]*(?:-[a-z0-9]+)*) \[(?P<model>[^\[\]]*)\] (?P<description>.+)$"
    )
    match = re.match(strict_pattern, line)

    if match:
        agent_name = match.group("name")
        model = match.group("model")
        description = match.group("description")

        if not model:
            violations.append(
                FormatViolation(
                    code="missing_model",
                    message="Model cannot be empty inside brackets",
                    found=line,
                )
            )
        else:
            resolved_model = config.model_aliases.get(model, model)
            if resolved_model not in config.allowed_models:
                violations.append(
                    FormatViolation(
                        code="invalid_model",
                        message=f"Model '{resolved_model}' is not in allowed_models: {config.allowed_models}",
                        found=line,
                    )
                )
            model = resolved_model

        if not description or not description.strip():
            violations.append(
                FormatViolation(
                    code="missing_description",
                    message="Description cannot be empty",
                    found=line,
                )
            )
        else:
            desc_len = len(description.strip())
            if desc_len < config.description_minimum_length:
                violations.append(
                    FormatViolation(
                        code="description_too_short",
                        message=f"Description is {desc_len} characters; minimum is {config.description_minimum_length}",
                        found=line,
                    )
                )
            elif desc_len > config.description_maximum_length:
                violations.append(
                    FormatViolation(
                        code="description_too_long",
                        message=f"Description is {desc_len} characters; maximum is {config.description_maximum_length}",
                        found=line,
                    )
                )

    else:
        paren_pattern = r"\(([^()]+)\)"
        if re.search(paren_pattern, line):
            violations.append(
                FormatViolation(
                    code="malformed_brackets",
                    message="Parentheses ( ) used instead of brackets [ ]",
                    found=line,
                )
            )
        else:
            name_pattern = r"^([a-z][a-z0-9]*(?:-[a-z0-9]+)*)"
            name_match = re.match(name_pattern, line)
            if not name_match:
                violations.append(
                    FormatViolation(
                        code="invalid_agent_name",
                        message="Agent name must be lowercase kebab-case, starting with a letter",
                        found=line,
                    )
                )
            else:
                if "[" in line or "]" in line:
                    if " [" not in line or "] " not in line:
                        violations.append(
                            FormatViolation(
                                code="invalid_spacing",
                                message="Brackets must be surrounded by exactly one space on each side",
                                found=line,
                            )
                        )
                    else:
                        violations.append(
                            FormatViolation(
                                code="malformed_brackets",
                                message="Brackets are malformed or not properly closed",
                                found=line,
                            )
                        )
                else:
                    violations.append(
                        FormatViolation(
                            code="missing_model",
                            message="Missing model specification in brackets [...]",
                            found=line,
                        )
                    )

    return ValidationResult(
        valid=(len(violations) == 0),
        violations=violations,
        agent_name=agent_name,
        model=model,
        description=description,
    )


def render_agent_display(agent: AgentDefinition) -> str:
    """Render an AgentDefinition as a canonical display line."""
    return f"{agent.id} [{agent.preferred_model.value}] {agent.description}"


def normalize_agent_display_line(
    line: str, config: AgentFormatConfig | None = None
) -> NormalizationResult:
    """Normalize unambiguous format violations.

    Only fixes:
    - Parentheses instead of brackets: name (model) desc -> name [model] desc
    - Missing/extra spaces around brackets: name[model] desc, name [model]desc -> name [model] desc
    Does not invent missing model or description.
    """
    if config is None:
        config = AgentFormatConfig()

    result = parse_agent_display_line(line, config)
    if result.valid:
        return NormalizationResult(changed=False, normalized_line=line)

    violation_codes = {v.code for v in result.violations}

    if "missing_model" in violation_codes or "missing_description" in violation_codes:
        reasons = []
        if "missing_model" in violation_codes:
            reasons.append("missing model")
        if "missing_description" in violation_codes:
            reasons.append("missing description")
        return NormalizationResult(changed=False, normalized_line=None, reason=": ".join(reasons))

    paren_pattern = (
        r"^(?P<name>[a-z][a-z0-9]*(?:-[a-z0-9]+)*)\s*\((?P<model>[^()]+)\)\s+(?P<desc>.+)$"
    )
    paren_match = re.match(paren_pattern, line)
    if paren_match:
        fixed = f"{paren_match.group('name')} [{paren_match.group('model')}] {paren_match.group('desc')}"
        return NormalizationResult(changed=True, normalized_line=fixed)

    bracket_pattern = (
        r"^(?P<name>[a-z][a-z0-9]*(?:-[a-z0-9]+)*)\s*\[(?P<model>[^\[\]]+)\]\s*(?P<desc>.+)$"
    )
    bracket_match = re.match(bracket_pattern, line)
    if bracket_match:
        name = bracket_match.group("name")
        model = bracket_match.group("model")
        desc = bracket_match.group("desc")
        if model and desc.strip():
            fixed = f"{name} [{model}] {desc.strip()}"
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
        "<agent-name> [<model>] <description>",
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
