"""Unit tests for canonical agent display format parsing and validation.

Format: <role> (<tier>)
Examples: cartographer (1), dev (2), architect (3), boh (4)
"""

from quattroagents.domain import AgentDefinition, Model
from quattroagents.formatting import (
    AGENT_FILE_PREFIX,
    AgentDisplayFormatValidator,
    AgentFormatConfig,
    agent_file_stem,
    diagnose_agent_display_line,
    normalize_agent_display_line,
    parse_agent_display_line,
    render_agent_display,
)

# ============================================================================
# Test 1: Valid line parses successfully
# ============================================================================


def test_valid_cartographer_line() -> None:
    """Valid display line with known role."""
    line = "cartographer (1)"
    result = parse_agent_display_line(line)

    assert result.valid is True
    assert result.violations == []
    assert result.role == "cartographer"
    assert result.tier == "1"


def test_valid_dev_line() -> None:
    """Valid display line with 'dev' role."""
    line = "dev (2)"
    result = parse_agent_display_line(line)

    assert result.valid is True
    assert result.violations == []
    assert result.role == "dev"
    assert result.tier == "2"


def test_valid_boh_line() -> None:
    """Valid display line with default 'boh' role."""
    line = "boh (4)"
    result = parse_agent_display_line(line)

    assert result.valid is True
    assert result.violations == []
    assert result.role == "boh"
    assert result.tier == "4"


def test_render_agent_display_cartographer() -> None:
    """render_agent_display produces correct format for repository-cartographer."""
    agent = AgentDefinition(
        id="repository-cartographer",
        description="Analizza struttura, dipendenze e confini del repository.",
        preferred_model=Model.HAIKU,
    )
    rendered = render_agent_display(agent)

    assert rendered == "cartographer (1)"
    # Parse it back to verify
    result = parse_agent_display_line(rendered)
    assert result.valid is True
    assert result.role == "cartographer"


def test_render_agent_display_uses_archetype_id_for_tier_suffixed_ids() -> None:
    """A tier-suffixed id (e.g. 'implementation-agent-haiku') still resolves its role
    via archetype_id, instead of falling back to the 'boh' default."""
    agent = AgentDefinition(
        id="implementation-agent-haiku",
        archetype_id="implementation-agent",
        description="Applies a fully-specified, mechanical change.",
        preferred_model=Model.HAIKU,
    )
    rendered = render_agent_display(agent)

    assert rendered == "dev (1)"


# ============================================================================
# Test 2: Invalid - square brackets used instead of parens -> malformed_delimiters
# ============================================================================


def test_invalid_square_brackets_instead_of_parens() -> None:
    """Square brackets instead of parentheses is detected as malformed_delimiters."""
    line = "cartographer [1]"
    result = parse_agent_display_line(line)

    assert result.valid is False
    assert len(result.violations) > 0
    violation_codes = [v.code for v in result.violations]
    assert "malformed_delimiters" in violation_codes


def test_invalid_square_brackets_with_tier() -> None:
    """Another square bracket variant should fail."""
    line = "dev [2]"
    result = parse_agent_display_line(line)

    assert result.valid is False
    violation_codes = [v.code for v in result.violations]
    assert "malformed_delimiters" in violation_codes


# ============================================================================
# Test 3: Invalid - missing tier entirely / empty parens -> missing_tier
# ============================================================================


def test_invalid_missing_tier_no_parens() -> None:
    """Line with no parentheses at all."""
    line = "cartographer"
    result = parse_agent_display_line(line)

    assert result.valid is False
    assert len(result.violations) > 0
    violation_codes = [v.code for v in result.violations]
    assert "missing_tier" in violation_codes


def test_invalid_empty_parens() -> None:
    """Empty parentheses ()."""
    line = "cartographer ()"
    result = parse_agent_display_line(line)

    assert result.valid is False
    assert len(result.violations) > 0
    violation_codes = [v.code for v in result.violations]
    assert "missing_tier" in violation_codes


def test_invalid_whitespace_only_in_parens() -> None:
    """Whitespace-only inside parentheses is treated as invalid tier."""
    line = "cartographer (  )"
    result = parse_agent_display_line(line)

    assert result.valid is False
    violation_codes = [v.code for v in result.violations]
    # Whitespace-only tier gets matched but is not in allowed_tiers
    assert "invalid_tier" in violation_codes


# ============================================================================
# Test 4: Invalid - role starts with uppercase or digit -> invalid_role
# ============================================================================


def test_invalid_role_starts_with_uppercase() -> None:
    """Role starting with uppercase letter."""
    line = "Cartographer (1)"
    result = parse_agent_display_line(line)

    assert result.valid is False
    assert len(result.violations) > 0
    violation_codes = [v.code for v in result.violations]
    assert "invalid_role" in violation_codes


def test_invalid_role_starts_with_digit() -> None:
    """Role starting with a digit."""
    line = "9dev (2)"
    result = parse_agent_display_line(line)

    assert result.valid is False
    violation_codes = [v.code for v in result.violations]
    assert "invalid_role" in violation_codes


def test_invalid_role_mixed_case() -> None:
    """Role with mixed case."""
    line = "CartOGrapher (1)"
    result = parse_agent_display_line(line)

    assert result.valid is False
    violation_codes = [v.code for v in result.violations]
    assert "invalid_role" in violation_codes


# ============================================================================
# Test 5: Invalid - tier not in allowed_tiers -> invalid_tier
# ============================================================================


def test_invalid_tier_5() -> None:
    """Tier 5 not in default allowed_tiers."""
    line = "cartographer (5)"
    result = parse_agent_display_line(line)

    assert result.valid is False
    assert len(result.violations) > 0
    violation_codes = [v.code for v in result.violations]
    assert "invalid_tier" in violation_codes


def test_invalid_tier_0() -> None:
    """Tier 0 not allowed."""
    line = "dev (0)"
    result = parse_agent_display_line(line)

    assert result.valid is False
    violation_codes = [v.code for v in result.violations]
    assert "invalid_tier" in violation_codes


def test_invalid_tier_abc() -> None:
    """Tier with letters."""
    line = "architect (abc)"
    result = parse_agent_display_line(line)

    assert result.valid is False
    violation_codes = [v.code for v in result.violations]
    assert "invalid_tier" in violation_codes


def test_invalid_tier_two_digits() -> None:
    """Tier with two digits."""
    line = "reviewer (10)"
    result = parse_agent_display_line(line)

    assert result.valid is False
    violation_codes = [v.code for v in result.violations]
    assert "invalid_tier" in violation_codes


# ============================================================================
# Test 6: Invalid - role too short -> role_too_short
# ============================================================================


def test_invalid_role_too_short_single_char() -> None:
    """Single-character role is below minimum of 2."""
    line = "d (2)"
    result = parse_agent_display_line(line)

    assert result.valid is False
    assert len(result.violations) > 0
    violation_codes = [v.code for v in result.violations]
    assert "role_too_short" in violation_codes


def test_invalid_role_too_short_empty() -> None:
    """Empty role."""
    line = " (2)"
    result = parse_agent_display_line(line)

    assert result.valid is False
    violation_codes = [v.code for v in result.violations]
    # Empty role may be caught as invalid_role or role_too_short
    assert "invalid_role" in violation_codes or "role_too_short" in violation_codes


# ============================================================================
# Test 7: Invalid - role too long -> role_too_long
# ============================================================================


def test_invalid_role_too_long() -> None:
    """Role exceeding maximum length of 40 characters."""
    long_role = "a" * 41
    line = f"{long_role} (2)"
    result = parse_agent_display_line(line)

    assert result.valid is False
    assert len(result.violations) > 0
    violation_codes = [v.code for v in result.violations]
    assert "role_too_long" in violation_codes


def test_invalid_role_exactly_at_max_length() -> None:
    """Role exactly at maximum (40 chars) should be valid."""
    role = "a" * 40
    line = f"{role} (2)"
    result = parse_agent_display_line(line)

    assert result.valid is True


def test_invalid_role_just_over_max_length() -> None:
    """Role one char over maximum (41 chars)."""
    role = "a" * 41
    line = f"{role} (2)"
    result = parse_agent_display_line(line)

    assert result.valid is False
    violation_codes = [v.code for v in result.violations]
    assert "role_too_long" in violation_codes


# ============================================================================
# Test 8: render_agent_display for each Model value
# ============================================================================


def test_render_agent_display_haiku() -> None:
    """render_agent_display with Model.HAIKU -> tier 1."""
    agent = AgentDefinition(
        id="repository-cartographer",
        description="",
        preferred_model=Model.HAIKU,
    )
    rendered = render_agent_display(agent)

    assert rendered == "cartographer (1)"
    result = parse_agent_display_line(rendered)
    assert result.valid is True
    assert result.tier == "1"


def test_render_agent_display_sonnet() -> None:
    """render_agent_display with Model.SONNET -> tier 2."""
    agent = AgentDefinition(
        id="code-reviewer",
        description="",
        preferred_model=Model.SONNET,
    )
    rendered = render_agent_display(agent)

    assert rendered == "reviewer (2)"
    result = parse_agent_display_line(rendered)
    assert result.valid is True
    assert result.tier == "2"


def test_render_agent_display_opus() -> None:
    """render_agent_display with Model.OPUS -> tier 3."""
    agent = AgentDefinition(
        id="project-orchestrator",
        description="",
        preferred_model=Model.OPUS,
    )
    rendered = render_agent_display(agent)

    assert rendered == "orchestrator (3)"
    result = parse_agent_display_line(rendered)
    assert result.valid is True
    assert result.tier == "3"


def test_render_agent_display_inherit() -> None:
    """render_agent_display with Model.INHERIT -> tier 4."""
    agent = AgentDefinition(
        id="unknown-custom-agent",
        description="",
        preferred_model=Model.INHERIT,
    )
    rendered = render_agent_display(agent)

    assert rendered == "boh (4)"
    result = parse_agent_display_line(rendered)
    assert result.valid is True
    assert result.tier == "4"


# ============================================================================
# Test 9: render_agent_display for unknown agent id -> "boh"
# ============================================================================


def test_render_unknown_agent_id_uses_default_boh() -> None:
    """Agent id not in ROLE_LABELS renders with default 'boh' role."""
    agent = AgentDefinition(
        id="unknown-agent-xyz",
        description="",
        preferred_model=Model.HAIKU,
    )
    rendered = render_agent_display(agent)

    assert rendered == "boh (1)"
    result = parse_agent_display_line(rendered)
    assert result.valid is True
    assert result.role == "boh"


def test_render_all_known_role_labels() -> None:
    """Verify a few known role labels render correctly."""
    test_cases = [
        ("project-orchestrator", Model.OPUS, "orchestrator (3)"),
        ("repository-cartographer", Model.HAIKU, "cartographer (1)"),
        ("architecture-guardian", Model.SONNET, "architect (2)"),
        ("implementation-agent", Model.HAIKU, "dev (1)"),
        ("test-agent", Model.HAIKU, "tester (1)"),
        ("code-reviewer", Model.SONNET, "reviewer (2)"),
    ]

    for agent_id, model, expected in test_cases:
        agent = AgentDefinition(id=agent_id, description="", preferred_model=model)
        rendered = render_agent_display(agent)
        assert rendered == expected, f"Failed for {agent_id}: got {rendered}, expected {expected}"


# ============================================================================
# Test 10: normalize_agent_display_line
# ============================================================================


def test_normalize_brackets_to_parens() -> None:
    """Normalize square brackets to parentheses."""
    line = "cartographer [1]"
    result = normalize_agent_display_line(line)

    assert result.changed is True
    # The role character class includes space, capturing trailing space before bracket
    assert result.normalized_line == "cartographer  (1)"


def test_normalize_brackets_to_parens_with_spacing() -> None:
    """Normalize square brackets with irregular spacing."""
    line = "cartographer [ 1 ]"
    result = normalize_agent_display_line(line)

    assert result.changed is True
    # Role includes trailing space, tier content includes internal spaces
    assert result.normalized_line == "cartographer  ( 1 )"


def test_normalize_spacing_around_parens() -> None:
    """Normalize missing space before parentheses."""
    line = "cartographer(1)"
    result = normalize_agent_display_line(line)

    assert result.changed is True
    assert result.normalized_line == "cartographer (1)"


def test_normalize_extra_spacing_before_parens() -> None:
    """Normalize extra spacing before parentheses."""
    line = "cartographer  [1]"
    result = normalize_agent_display_line(line)

    assert result.changed is True
    # Bracket conversion plus space cleanup
    assert "cartographer" in result.normalized_line and "(1)" in result.normalized_line


def test_normalize_already_valid_unchanged() -> None:
    """Valid line remains unchanged."""
    line = "cartographer (1)"
    result = normalize_agent_display_line(line)

    assert result.changed is False
    assert result.normalized_line == line


def test_normalize_missing_tier_unfixable() -> None:
    """Cannot normalize line with missing tier."""
    line = "cartographer"
    result = normalize_agent_display_line(line)

    assert result.changed is False
    assert result.normalized_line is None
    assert result.reason is not None
    assert "missing tier" in result.reason


def test_normalize_invalid_role_unfixable() -> None:
    """Cannot normalize line with invalid role (uppercase)."""
    line = "Cartographer (1)"
    result = normalize_agent_display_line(line)

    assert result.changed is False
    assert result.normalized_line is None
    assert result.reason is not None


# ============================================================================
# Test 11: diagnose_agent_display_line
# ============================================================================


def test_diagnose_valid_line() -> None:
    """Diagnose valid line shows simple success message."""
    line = "cartographer (1)"
    diagnosis = diagnose_agent_display_line(line)

    assert diagnosis == "Valid agent format."


def test_diagnose_invalid_line_contains_structure() -> None:
    """Diagnose invalid line includes Found/Expected/Errors."""
    line = "Cartographer (1)"
    diagnosis = diagnose_agent_display_line(line)

    assert "Invalid agent format" in diagnosis
    assert "Found:" in diagnosis
    assert "Expected:" in diagnosis
    assert "Errors:" in diagnosis


def test_diagnose_invalid_line_includes_violation_codes() -> None:
    """Diagnose message includes violation codes."""
    line = "cartographer [1]"
    diagnosis = diagnose_agent_display_line(line)

    assert "Invalid agent format" in diagnosis
    assert "malformed_delimiters" in diagnosis


def test_diagnose_missing_tier() -> None:
    """Diagnose line with missing tier."""
    line = "cartographer"
    diagnosis = diagnose_agent_display_line(line)

    assert "Invalid agent format" in diagnosis
    assert "missing_tier" in diagnosis


def test_diagnose_role_too_short() -> None:
    """Diagnose line with role too short."""
    line = "a (1)"
    diagnosis = diagnose_agent_display_line(line)

    assert "Invalid agent format" in diagnosis
    assert "role_too_short" in diagnosis


# ============================================================================
# Test 12: AgentDisplayFormatValidator wrapper class
# ============================================================================


def test_validator_validate_delegates() -> None:
    """Validator.validate() delegates to parse_agent_display_line()."""
    validator = AgentDisplayFormatValidator()
    line = "cartographer (1)"

    validator_result = validator.validate(line)
    direct_result = parse_agent_display_line(line)

    assert validator_result.valid == direct_result.valid
    assert validator_result.role == direct_result.role
    assert validator_result.tier == direct_result.tier
    assert validator_result.violations == direct_result.violations


def test_validator_normalize_delegates() -> None:
    """Validator.normalize() delegates to normalize_agent_display_line()."""
    validator = AgentDisplayFormatValidator()
    line = "cartographer(1)"

    validator_result = validator.normalize(line)
    direct_result = normalize_agent_display_line(line)

    assert validator_result.changed == direct_result.changed
    assert validator_result.normalized_line == direct_result.normalized_line


def test_validator_render_delegates() -> None:
    """Validator.render() delegates to render_agent_display()."""
    validator = AgentDisplayFormatValidator()
    agent = AgentDefinition(
        id="repository-cartographer",
        description="",
        preferred_model=Model.HAIKU,
    )

    validator_result = validator.render(agent)
    direct_result = render_agent_display(agent)

    assert validator_result == direct_result


def test_validator_diagnose_delegates() -> None:
    """Validator.diagnose() delegates to diagnose_agent_display_line()."""
    validator = AgentDisplayFormatValidator()
    line = "cartographer (1)"

    validator_result = validator.diagnose(line)
    direct_result = diagnose_agent_display_line(line)

    assert validator_result == direct_result


# ============================================================================
# Test 13: AgentFormatConfig custom configuration
# ============================================================================


def test_custom_config_allowed_tiers() -> None:
    """Custom allowed_tiers configuration takes effect."""
    config = AgentFormatConfig(allowed_tiers=["2", "3"])
    result = parse_agent_display_line("cartographer (1)", config)

    assert result.valid is False
    violation_codes = [v.code for v in result.violations]
    assert "invalid_tier" in violation_codes


def test_custom_config_allowed_tiers_valid() -> None:
    """Custom allowed_tiers allows specified tiers."""
    config = AgentFormatConfig(allowed_tiers=["1", "5"])
    result = parse_agent_display_line("cartographer (5)", config)

    assert result.valid is True


def test_custom_config_role_minimum_length() -> None:
    """Custom role_minimum_length takes effect."""
    config = AgentFormatConfig(role_minimum_length=5)
    result = parse_agent_display_line("dev (1)", config)

    assert result.valid is False
    violation_codes = [v.code for v in result.violations]
    assert "role_too_short" in violation_codes


def test_custom_config_role_minimum_length_valid() -> None:
    """Custom role_minimum_length allows valid roles."""
    config = AgentFormatConfig(role_minimum_length=1)
    result = parse_agent_display_line("d (1)", config)

    assert result.valid is True


def test_custom_config_role_maximum_length() -> None:
    """Custom role_maximum_length takes effect."""
    config = AgentFormatConfig(role_maximum_length=5)
    result = parse_agent_display_line("developer (1)", config)

    assert result.valid is False
    violation_codes = [v.code for v in result.violations]
    assert "role_too_long" in violation_codes


def test_validator_uses_custom_config() -> None:
    """Validator applies custom config to all operations."""
    config = AgentFormatConfig(allowed_tiers=["2"], role_minimum_length=3)
    validator = AgentDisplayFormatValidator(config)

    result = validator.validate("dev (1)")
    assert result.valid is False
    violation_codes = [v.code for v in result.violations]
    assert "invalid_tier" in violation_codes


# ============================================================================
# Test 14: Role labels can contain spaces and +
# ============================================================================


def test_role_with_spaces() -> None:
    """Role labels can contain spaces."""
    line = "dev tools (2)"
    result = parse_agent_display_line(line)

    assert result.valid is True
    assert result.role == "dev tools"
    assert result.tier == "2"


def test_role_with_plus_sign() -> None:
    """Role labels can contain + signs."""
    line = "dev c++ (2)"
    result = parse_agent_display_line(line)

    assert result.valid is True
    assert result.role == "dev c++"
    assert result.tier == "2"


def test_role_with_slash() -> None:
    """Role labels can contain forward slashes."""
    line = "ci/cd (2)"
    result = parse_agent_display_line(line)

    assert result.valid is True
    assert result.role == "ci/cd"
    assert result.tier == "2"


def test_role_with_mixed_special_chars() -> None:
    """Role labels can contain combination of special chars."""
    line = "dev c++ tools (3)"
    result = parse_agent_display_line(line)

    assert result.valid is True
    assert result.role == "dev c++ tools"
    assert result.tier == "3"


# ============================================================================
# Test 15: Edge cases and integration
# ============================================================================


def test_valid_tier_boundaries() -> None:
    """All valid tiers 1-4 parse successfully."""
    for tier in ["1", "2", "3", "4"]:
        line = f"dev ({tier})"
        result = parse_agent_display_line(line)
        assert result.valid is True
        assert result.tier == tier


def test_multiple_spaces_in_role() -> None:
    """Role with multiple consecutive spaces."""
    line = "agent  name (1)"
    result = parse_agent_display_line(line)

    # The regex allows spaces, so this should parse
    assert result.valid is True
    assert "agent  name" in result.role or result.role == "agent  name"


def test_render_then_parse_roundtrip() -> None:
    """Render an agent and parse it back."""
    original_agent = AgentDefinition(
        id="code-reviewer",
        description="",
        preferred_model=Model.SONNET,
    )

    rendered = render_agent_display(original_agent)
    parsed = parse_agent_display_line(rendered)

    assert parsed.valid is True
    assert parsed.role == "reviewer"
    assert parsed.tier == "2"


def test_normalize_then_parse_roundtrip() -> None:
    """Normalize a line and parse the result."""
    line = "cartographer[1]"
    normalized = normalize_agent_display_line(line)
    assert normalized.changed is True

    parsed = parse_agent_display_line(normalized.normalized_line or "")
    assert parsed.valid is True
    assert parsed.role == "cartographer"
    assert parsed.tier == "1"


def test_config_with_all_custom_settings() -> None:
    """Config with all custom settings applied correctly."""
    config = AgentFormatConfig(
        allowed_tiers=["1", "2"],
        role_minimum_length=3,
        role_maximum_length=20,
    )

    # Valid: within all bounds
    result = parse_agent_display_line("abc (1)", config)
    assert result.valid is True

    # Invalid: tier not allowed
    result = parse_agent_display_line("abc (3)", config)
    assert result.valid is False

    # Invalid: role too short
    result = parse_agent_display_line("ab (1)", config)
    assert result.valid is False

    # Invalid: role too long
    result = parse_agent_display_line("a" * 21 + " (1)", config)
    assert result.valid is False


# ============================================================================
# Tests: agent_file_stem
# ============================================================================


def test_agent_file_stem_adds_qag_prefix() -> None:
    """agent_file_stem adds qag- prefix to agent id."""
    result = agent_file_stem("project-orchestrator")

    assert result == "qag-project-orchestrator"


def test_agent_file_stem_prefix_constant_matches() -> None:
    """AGENT_FILE_PREFIX constant matches expected value and is used by agent_file_stem."""
    assert AGENT_FILE_PREFIX == "qag-"
    assert agent_file_stem("x") == AGENT_FILE_PREFIX + "x"


def test_agent_file_stem_preserves_id_structure() -> None:
    """agent_file_stem preserves internal hyphens in agent id."""
    result = agent_file_stem("implementation-agent")

    assert result == "qag-implementation-agent"
