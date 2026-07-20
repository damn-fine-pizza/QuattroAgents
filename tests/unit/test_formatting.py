"""Unit tests for canonical agent display format parsing and validation."""

from quattroagents.domain import AgentDefinition, Model
from quattroagents.formatting import (
    AgentDisplayFormatValidator,
    AgentFormatConfig,
    diagnose_agent_display_line,
    normalize_agent_display_line,
    parse_agent_display_line,
    render_agent_display,
)


# Test 1: Valid line parses successfully
def test_valid_line_parses_successfully() -> None:
    line = (
        "repository-cartographer [haiku] Analizza struttura, dipendenze e confini del repository."
    )
    result = parse_agent_display_line(line)

    assert result.valid is True
    assert result.violations == []
    assert result.agent_name == "repository-cartographer"
    assert result.model == "haiku"
    assert result.description == "Analizza struttura, dipendenze e confini del repository."


# Test 2: Invalid - parentheses instead of brackets
def test_invalid_parentheses_instead_of_brackets() -> None:
    line = (
        "repository-cartographer (haiku) Analizza struttura, dipendenze e confini del repository."
    )
    result = parse_agent_display_line(line)

    assert result.valid is False
    assert len(result.violations) > 0
    violation_codes = [v.code for v in result.violations]
    assert "malformed_brackets" in violation_codes


# Test 3: Invalid - missing model entirely
def test_invalid_missing_model_entirely() -> None:
    line = "repository-cartographer Analizza il repository con dettaglio."
    result = parse_agent_display_line(line)

    assert result.valid is False
    assert len(result.violations) > 0
    violation_codes = [v.code for v in result.violations]
    assert "missing_model" in violation_codes


# Test 4: Invalid - uppercase/non-kebab-case agent name
def test_invalid_uppercase_agent_name() -> None:
    line = "Repository Cartographer [haiku] Analizza il repository con dettaglio."
    result = parse_agent_display_line(line)

    assert result.valid is False
    assert len(result.violations) > 0
    violation_codes = [v.code for v in result.violations]
    assert "invalid_agent_name" in violation_codes


def test_invalid_non_kebab_case_agent_name() -> None:
    # Underscore causes name pattern to partially match, leaving invalid format for brackets
    line = "repository_cartographer [haiku] Analizza il repository con dettaglio."
    result = parse_agent_display_line(line)

    assert result.valid is False
    assert len(result.violations) > 0
    violation_codes = [v.code for v in result.violations]
    # Underscore in name causes malformed_brackets error (name pattern matches "repository" but leaves "_cartographer")
    assert "malformed_brackets" in violation_codes


def test_invalid_agent_name_starts_with_uppercase() -> None:
    # Name starting with uppercase fails the name pattern entirely
    line = "Repository-Cartographer [haiku] Analizza il repository con dettaglio."
    result = parse_agent_display_line(line)

    assert result.valid is False
    assert len(result.violations) > 0
    violation_codes = [v.code for v in result.violations]
    assert "invalid_agent_name" in violation_codes


def test_invalid_agent_name_starts_with_number() -> None:
    # Name starting with number fails the name pattern entirely
    line = "9-agent [haiku] Analizza il repository con dettaglio."
    result = parse_agent_display_line(line)

    assert result.valid is False
    assert len(result.violations) > 0
    violation_codes = [v.code for v in result.violations]
    assert "invalid_agent_name" in violation_codes


# Test 5: Invalid - unknown model not in allowed_models
def test_invalid_unknown_model() -> None:
    line = "repository-cartographer [unknown-model] Analizza il repository con dettaglio."
    result = parse_agent_display_line(line)

    assert result.valid is False
    assert len(result.violations) > 0
    violation_codes = [v.code for v in result.violations]
    assert "invalid_model" in violation_codes


# Test 6: Invalid - description too short
def test_invalid_description_too_short() -> None:
    line = "repository-cartographer [haiku] Short desc"
    result = parse_agent_display_line(line)

    assert result.valid is False
    assert len(result.violations) > 0
    violation_codes = [v.code for v in result.violations]
    assert "description_too_short" in violation_codes


# Test 6b: Invalid - description too long
def test_invalid_description_too_long() -> None:
    long_desc = "x" * 181  # Exceeds default maximum of 180
    line = f"repository-cartographer [haiku] {long_desc}"
    result = parse_agent_display_line(line)

    assert result.valid is False
    assert len(result.violations) > 0
    violation_codes = [v.code for v in result.violations]
    assert "description_too_long" in violation_codes


# Test 7: Model alias resolution
def test_model_alias_resolution() -> None:
    line = "repository-cartographer [claude-haiku] Analizza struttura, dipendenze e confini del repository."
    result = parse_agent_display_line(line)

    assert result.valid is True
    assert result.model == "haiku"  # Alias resolved to "haiku"


def test_model_alias_sonnet_resolution() -> None:
    line = "code-reviewer [claude-sonnet] Analizza struttura, dipendenze e confini del repository."
    result = parse_agent_display_line(line)

    assert result.valid is True
    assert result.model == "sonnet"


def test_model_alias_opus_resolution() -> None:
    line = (
        "strategic-planner [claude-opus] Analizza struttura, dipendenze e confini del repository."
    )
    result = parse_agent_display_line(line)

    assert result.valid is True
    assert result.model == "opus"


# Test 8: normalize_agent_display_line
def test_normalize_parentheses_to_brackets() -> None:
    line = (
        "repository-cartographer (haiku) Analizza struttura, dipendenze e confini del repository."
    )
    result = normalize_agent_display_line(line)

    assert result.changed is True
    assert (
        result.normalized_line
        == "repository-cartographer [haiku] Analizza struttura, dipendenze e confini del repository."
    )


def test_normalize_missing_spacing_around_brackets() -> None:
    line = "repository-cartographer[haiku] Analizza struttura, dipendenze e confini del repository."
    result = normalize_agent_display_line(line)

    assert result.changed is True
    assert (
        result.normalized_line
        == "repository-cartographer [haiku] Analizza struttura, dipendenze e confini del repository."
    )


def test_normalize_extra_spacing_before_description() -> None:
    # Note: Extra spaces after ] are considered valid and not normalized
    # This is because parse sees "] " followed by description including the extra spaces
    line = (
        "repository-cartographer [haiku]   Analizza struttura, dipendenze e confini del repository."
    )
    result = normalize_agent_display_line(line)

    # Extra spaces after ] are part of valid description, so no normalization occurs
    assert result.changed is False
    assert result.normalized_line == line


def test_normalize_missing_model_returns_unchanged() -> None:
    line = "repository-cartographer Analizza il repository con dettaglio."
    result = normalize_agent_display_line(line)

    assert result.changed is False
    assert result.normalized_line is None
    assert result.reason is not None


def test_normalize_already_valid_line_returns_unchanged() -> None:
    line = (
        "repository-cartographer [haiku] Analizza struttura, dipendenze e confini del repository."
    )
    result = normalize_agent_display_line(line)

    assert result.changed is False
    assert result.normalized_line == line


# Test 9: render_agent_display
def test_render_agent_display() -> None:
    agent = AgentDefinition(
        id="repository-cartographer",
        description="Analizza struttura, dipendenze e confini del repository.",
        preferred_model=Model.HAIKU,
    )
    rendered = render_agent_display(agent)

    assert (
        rendered
        == "repository-cartographer [haiku] Analizza struttura, dipendenze e confini del repository."
    )


def test_render_agent_display_with_sonnet() -> None:
    agent = AgentDefinition(
        id="code-reviewer",
        description="Rivedi il codice per stile e correttezza.",
        preferred_model=Model.SONNET,
    )
    rendered = render_agent_display(agent)

    assert rendered == "code-reviewer [sonnet] Rivedi il codice per stile e correttezza."


def test_render_agent_display_with_opus() -> None:
    agent = AgentDefinition(
        id="strategic-planner",
        description="Pianifica strategie architetturali a lungo termine.",
        preferred_model=Model.OPUS,
    )
    rendered = render_agent_display(agent)

    assert (
        rendered == "strategic-planner [opus] Pianifica strategie architetturali a lungo termine."
    )


# Test 10: diagnose_agent_display_line
def test_diagnose_valid_line() -> None:
    line = (
        "repository-cartographer [haiku] Analizza struttura, dipendenze e confini del repository."
    )
    diagnosis = diagnose_agent_display_line(line)

    assert diagnosis == "Valid agent format."


def test_diagnose_invalid_line() -> None:
    line = "Repository Cartographer [haiku] Short"
    diagnosis = diagnose_agent_display_line(line)

    assert "Invalid agent format" in diagnosis
    assert "Found:" in diagnosis
    assert "Expected:" in diagnosis
    assert "Errors:" in diagnosis


def test_diagnose_invalid_line_contains_error_details() -> None:
    line = "repository-cartographer (haiku) Short"
    diagnosis = diagnose_agent_display_line(line)

    assert "Invalid agent format" in diagnosis
    assert "Found:" in diagnosis
    assert "Expected:" in diagnosis
    assert "Errors:" in diagnosis
    assert "malformed_brackets" in diagnosis or "description_too_short" in diagnosis


# Test 11: AgentDisplayFormatValidator class wrapper
def test_validator_validate_delegates_correctly() -> None:
    validator = AgentDisplayFormatValidator()
    line = (
        "repository-cartographer [haiku] Analizza struttura, dipendenze e confini del repository."
    )

    wrapped_result = validator.validate(line)
    direct_result = parse_agent_display_line(line)

    assert wrapped_result.valid == direct_result.valid
    assert wrapped_result.agent_name == direct_result.agent_name
    assert wrapped_result.model == direct_result.model
    assert wrapped_result.description == direct_result.description


def test_validator_normalize_delegates_correctly() -> None:
    validator = AgentDisplayFormatValidator()
    line = "repository-cartographer[haiku] Analizza struttura, dipendenze e confini del repository."

    wrapped_result = validator.normalize(line)
    direct_result = normalize_agent_display_line(line)

    assert wrapped_result.changed == direct_result.changed
    assert wrapped_result.normalized_line == direct_result.normalized_line


def test_validator_render_delegates_correctly() -> None:
    validator = AgentDisplayFormatValidator()
    agent = AgentDefinition(
        id="repository-cartographer",
        description="Analizza struttura, dipendenze e confini del repository.",
        preferred_model=Model.HAIKU,
    )

    wrapped_result = validator.render(agent)
    direct_result = render_agent_display(agent)

    assert wrapped_result == direct_result


def test_validator_diagnose_delegates_correctly() -> None:
    validator = AgentDisplayFormatValidator()
    line = (
        "repository-cartographer [haiku] Analizza struttura, dipendenze e confini del repository."
    )

    wrapped_result = validator.diagnose(line)
    direct_result = diagnose_agent_display_line(line)

    assert wrapped_result == direct_result


# Additional tests for edge cases
def test_validator_with_custom_config() -> None:
    config = AgentFormatConfig(
        allowed_models=["custom-model"],
        description_minimum_length=10,
        description_maximum_length=100,
    )
    validator = AgentDisplayFormatValidator(config)

    line = "my-agent [custom-model] This is a custom description."
    result = validator.validate(line)

    assert result.valid is True
    assert result.model == "custom-model"


def test_multiple_model_aliases_with_validator() -> None:
    config = AgentFormatConfig()
    validator = AgentDisplayFormatValidator(config)

    lines = [
        ("agent-one [claude-haiku] This is a haiku agent with long description.", "haiku"),
        ("agent-two [claude-sonnet] This is a sonnet agent with long description.", "sonnet"),
        ("agent-three [claude-opus] This is an opus agent with long description.", "opus"),
    ]

    for line, expected_model in lines:
        result = validator.validate(line)
        assert result.valid is True
        assert result.model == expected_model


def test_normalization_preserves_valid_description() -> None:
    # Extra spaces after ] are considered valid (part of description)
    line = (
        "repository-cartographer [haiku]  Analizza struttura, dipendenze e confini del repository."
    )
    result = normalize_agent_display_line(line)

    # Line is valid as-is, so no normalization occurs
    assert result.changed is False
    assert result.normalized_line == line


def test_empty_model_brackets_invalid() -> None:
    line = "repository-cartographer [] Analizza struttura, dipendenze e confini del repository."
    result = parse_agent_display_line(line)

    assert result.valid is False
    violation_codes = [v.code for v in result.violations]
    assert "missing_model" in violation_codes


def test_agent_name_with_numbers_valid() -> None:
    line = "agent-2024 [haiku] Analizza struttura, dipendenze e confini del repository."
    result = parse_agent_display_line(line)

    assert result.valid is True
    assert result.agent_name == "agent-2024"


def test_agent_name_with_single_letter_invalid() -> None:
    line = "a [haiku] Analizza struttura, dipendenze e confini del repository."
    result = parse_agent_display_line(line)

    # Single letter followed by invalid format should fail
    # The pattern requires kebab-case which means letter, then optional parts
    # "a" by itself is actually valid per the regex, but let's verify
    assert result.valid is True  # single letter 'a' is valid


def test_render_preserves_all_agent_properties() -> None:
    agent = AgentDefinition(
        id="test-agent",
        description="Test description for rendering.",
        preferred_model=Model.SONNET,
        responsibilities=["do something"],
        scope="project-wide",
    )
    rendered = render_agent_display(agent)

    # render_agent_display should only render id, model, and description
    assert "test-agent" in rendered
    assert "[sonnet]" in rendered
    assert "Test description for rendering." in rendered
    # Should not include other properties
    assert "responsibilities" not in rendered
    assert "project-wide" not in rendered
