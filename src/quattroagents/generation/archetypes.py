"""Archetype catalog for the Project Agent Factory.

An archetype is a reference role (e.g. "test-agent") that is rarely, if ever,
instantiated directly. Instead, each archetype defines a Haiku-tier and a
Sonnet-tier variant, split along a single axis:

- Haiku variant: bounded, mechanically verifiable work — explicit
  instructions, a single narrow scope, a pass/fail or exists/matches outcome,
  no cross-cutting synthesis required.
- Sonnet variant: work that requires interpreting ambiguous requirements,
  weighing trade-offs, synthesizing multiple sources, or reasoning about
  cross-agent/cross-component impact.

`select_agents` (in `agents.py`) instantiates both variants for every
selected archetype, using internal ids of the form `{archetype_id}-{tier}`
(rendered to disk as `qag-{archetype_id}-{tier}` — see `formatting.py`'s
`agent_file_stem`). This lets the generated team lean on many narrow, fast
Haiku agents for routine work while keeping Sonnet agents available for the
judgment calls, and lets the invoking side (an orchestrator agent, a human,
or Claude Code itself) pick the right one per task.

`expected_inputs`/`expected_outputs` name concrete file artifacts (not
prose) so agents hand off work by reading/writing files directly instead of
relaying full content through an orchestrator's context — see docs on the
"Handoff" section rendered by the adapters. Together, the producer/consumer
relationships they describe form a dependency graph across the whole
generated team; `validate_generated_configuration` checks that graph for
cycles (see `generation/swarm.py`), which is how a generated team is kept
free of circular hand-off loops (the static-generation analogue of a
deadlock/livelock check).
"""

from __future__ import annotations

from ..domain import (
    AgentDefinition,
    AgentLifetime,
    AgentMode,
    AgentPermissions,
    DefinitionSource,
    Model,
)

ARCHETYPES: dict[str, dict[str, AgentDefinition]] = {
    "project-orchestrator": {
        "haiku": AgentDefinition(
            id="project-orchestrator-haiku",
            archetype_id="project-orchestrator",
            description="Mechanically executes an already-computed swarm wave plan: dispatches agents in wave order and tracks completion.",
            mode=AgentMode.READ_ONLY,
            preferred_model=Model.HAIKU,
            permissions=AgentPermissions(can_read_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            responsibilities=[
                "Follow a precomputed wave schedule and dispatch agents in the given order",
                "Track which agents have completed and which are pending against a fixed checklist",
                "Relay handoff artifact paths (not content) between agents per the declared roster",
            ],
            scope="Mechanical execution of an already-validated swarm plan",
            when_to_use="When a swarm plan with waves/dependencies has already been computed and just needs dispatching",
            when_not_to_use="When the plan is incomplete, ambiguous, or agents disagree — escalate to the Sonnet variant instead",
            expected_inputs=[
                "swarm-plan.json: precomputed waves, dependencies, and completion criteria"
            ],
            expected_outputs=[
                "team-status.md: per-agent dispatch/completion status against the plan"
            ],
            completion_criteria=[
                "Every agent in the plan has been dispatched in the correct wave order",
                "team-status.md reflects the final status of every agent",
            ],
        ),
        "sonnet": AgentDefinition(
            id="project-orchestrator-sonnet",
            archetype_id="project-orchestrator",
            description="Coordinates discovery, design, implementation, and review phases across the generated agent team, resolving ambiguity the plan doesn't cover.",
            mode=AgentMode.READ_ONLY,
            preferred_model=Model.SONNET,
            permissions=AgentPermissions(can_read_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            responsibilities=[
                "Decide phase transitions and task decomposition when no precomputed plan covers the situation",
                "Resolve conflicting recommendations between agents",
                "Make priority/scope judgment calls the generated plan leaves open",
            ],
            scope="Entire project lifecycle management, including cases requiring judgment",
            when_to_use="At the start of ambiguous or multi-phase work, or when the Haiku variant hits a case outside its plan",
            when_not_to_use="Not needed for single-agent or fully pre-planned trivial tasks",
            expected_outputs=[
                "team-status.md: per-agent dispatch/completion status and rationale for judgment calls"
            ],
            completion_criteria=[
                "All phases completed and reviewed",
                "Handoff to next phase confirmed",
                "Team alignment on deliverables achieved",
            ],
        ),
    },
    "repository-cartographer": {
        "haiku": AgentDefinition(
            id="repository-cartographer-haiku",
            archetype_id="repository-cartographer",
            description="Enumerates repository structure and dependency manifests into a fixed-template map.",
            mode=AgentMode.READ_ONLY,
            preferred_model=Model.HAIKU,
            permissions=AgentPermissions(can_read_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            responsibilities=[
                "Enumerate the directory tree and file counts per subsystem",
                "List dependency manifests and their declared packages",
                "Produce a structured repo map following a fixed template",
            ],
            scope="Mechanical repository structure enumeration",
            when_to_use="During initial project analysis, or whenever repo-map.json needs refreshing after structural changes",
            when_not_to_use="When boundaries are implicit or contested, not just structural — use the Sonnet variant",
            expected_outputs=[
                "repo-map.json: directory tree, dependency manifest summary, subsystem boundaries"
            ],
            completion_criteria=[
                "repo-map.json produced and matches current repository structure",
                "All dependency manifests found are listed",
            ],
        ),
        "sonnet": AgentDefinition(
            id="repository-cartographer-sonnet",
            archetype_id="repository-cartographer",
            description="Identifies subsystem boundaries and dependency-graph drift that aren't visible from directory structure alone.",
            mode=AgentMode.READ_ONLY,
            preferred_model=Model.SONNET,
            permissions=AgentPermissions(can_read_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            responsibilities=[
                "Identify implicit subsystem boundaries not reflected in directory structure",
                "Assess whether the dependency graph indicates architectural drift",
                "Recommend reorganization when structure and actual usage diverge",
            ],
            scope="Repository analysis requiring interpretation beyond structure",
            when_to_use="When repo-map.json alone doesn't explain how the codebase is actually organized",
            when_not_to_use="For routine structural enumeration — use the Haiku variant",
            expected_inputs=[
                "repo-map.json: directory tree, dependency manifest summary, subsystem boundaries"
            ],
            expected_outputs=[
                "repo-map.json: directory tree, dependency manifest summary, subsystem boundaries"
            ],
            completion_criteria=[
                "Implicit subsystem boundaries documented",
                "Dependency-graph drift assessed and reported",
            ],
        ),
    },
    "architecture-guardian": {
        "haiku": AgentDefinition(
            id="architecture-guardian-haiku",
            archetype_id="architecture-guardian",
            description="Runs a fixed checklist of architectural lint rules against a diff and reports matches.",
            mode=AgentMode.READ_ONLY,
            preferred_model=Model.HAIKU,
            permissions=AgentPermissions(can_read_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            responsibilities=[
                "Run a fixed checklist of architectural rules (forbidden imports, layering violations, protected-path touches) against a diff",
                "Report each rule as pass/fail with the offending location",
                "Flag any hit for Sonnet-tier review — do not judge severity",
            ],
            scope="Mechanical architectural rule checking",
            when_to_use="On every change, as a fast pre-filter before deeper architectural review",
            when_not_to_use="When a flagged or borderline change needs a judgment call on actual impact",
            expected_inputs=[
                "repo-map.json: directory tree, dependency manifest summary, subsystem boundaries"
            ],
            expected_outputs=[
                "architecture-review.md: rule-by-rule pass/fail against the checklist"
            ],
            completion_criteria=[
                "Every rule in the checklist evaluated against the diff",
                "architecture-review.md lists all rule hits with locations",
            ],
        ),
        "sonnet": AgentDefinition(
            id="architecture-guardian-sonnet",
            archetype_id="architecture-guardian",
            description="Evaluates architectural decisions and cross-component changes flagged by the Haiku pre-filter or raised directly.",
            mode=AgentMode.READ_ONLY,
            preferred_model=Model.SONNET,
            permissions=AgentPermissions(can_read_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            responsibilities=[
                "Evaluate whether a flagged or borderline change actually harms the architecture, weighing trade-offs",
                "Assess cross-component ripple effects not caught by static rules",
                "Ensure architectural consistency across the system",
            ],
            scope="Architectural decisions and system design",
            when_to_use="When changes affect system architecture or multiple components, or a Haiku-tier rule was flagged",
            when_not_to_use="For isolated, single-component changes with no architectural impact",
            expected_inputs=[
                "repo-map.json: directory tree, dependency manifest summary, subsystem boundaries",
                "architecture-review.md: rule-by-rule pass/fail against the checklist",
            ],
            expected_outputs=[
                "architecture-review.md: verdicts on flagged/borderline changes with rationale"
            ],
            completion_criteria=[
                "Design review completed and documented",
                "Cross-component impact assessed",
                "Architectural consistency verified",
            ],
        ),
    },
    "implementation-agent": {
        "haiku": AgentDefinition(
            id="implementation-agent-haiku",
            archetype_id="implementation-agent",
            description="Applies a fully-specified, mechanical change to a single narrow scope.",
            mode=AgentMode.WRITE,
            preferred_model=Model.HAIKU,
            permissions=AgentPermissions(can_read_files=True, can_write_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            relevant_paths=["**/*"],
            responsibilities=[
                "Apply a fully-specified, mechanical change (rename, apply a given patch/template, fix a known lint error)",
                "Keep the change to a single file or narrowly-scoped set of files",
                "Verify the change matches the given specification exactly",
            ],
            scope="Mechanical code changes with a fully-specified outcome",
            when_to_use="When the exact change to make is already fully specified, with no open design decisions",
            when_not_to_use="When the approach isn't fully specified, spans multiple subsystems, or requires design choices",
            expected_inputs=[
                "repo-map.json: directory tree, dependency manifest summary, subsystem boundaries"
            ],
            completion_criteria=[
                "Change applied exactly as specified",
                "Change is limited to its declared narrow scope",
            ],
        ),
        "sonnet": AgentDefinition(
            id="implementation-agent-sonnet",
            archetype_id="implementation-agent",
            description="Implements scoped changes requiring design choices, within the boundaries set by the orchestrator.",
            mode=AgentMode.WRITE,
            preferred_model=Model.SONNET,
            permissions=AgentPermissions(can_read_files=True, can_write_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            relevant_paths=["**/*"],
            responsibilities=[
                "Implement changes requiring design choices, across multiple files or subsystems",
                "Follow established coding standards and patterns",
                "Respect scoping boundaries set by the orchestrator",
            ],
            scope="Code implementation requiring design judgment",
            when_to_use="When code changes need decisions about approach, not just mechanical application",
            when_not_to_use="Not used for review, testing, or release tasks",
            expected_inputs=[
                "repo-map.json: directory tree, dependency manifest summary, subsystem boundaries",
                "architecture-review.md: verdicts on flagged/borderline changes with rationale",
            ],
            completion_criteria=[
                "Code changes implemented",
                "Changes comply with scope boundaries",
                "Implementation follows established patterns",
            ],
        ),
    },
    "test-agent": {
        "haiku": AgentDefinition(
            id="test-agent-haiku",
            archetype_id="test-agent",
            description="Runs the existing test suite and writes tests for fully-specified function signatures.",
            mode=AgentMode.WRITE,
            preferred_model=Model.HAIKU,
            permissions=AgentPermissions(
                can_read_files=True, can_write_files=True, can_execute_commands=True
            ),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            relevant_paths=[
                "tests/**",
                "**/test_*.py",
                "**/*_test.py",
                "**/*.test.*",
                "**/*.spec.*",
            ],
            responsibilities=[
                "Execute the existing test suite and report pass/fail with failure output",
                "Write a unit test for a function whose signature and behavior are already fully specified",
                "Update test fixtures following an existing template",
            ],
            scope="Mechanical test execution and template-driven test authorship",
            when_to_use="When running tests, or writing a test for behavior that's already fully specified",
            when_not_to_use="When test strategy, edge-case selection, or flaky-test diagnosis requires judgment",
            expected_inputs=[
                "repo-map.json: directory tree, dependency manifest summary, subsystem boundaries"
            ],
            expected_outputs=["test-report.json: pass/fail counts and failure details"],
            completion_criteria=[
                "Test suite executed and test-report.json produced",
                "All tests passing, or failures reported with output",
            ],
        ),
        "sonnet": AgentDefinition(
            id="test-agent-sonnet",
            archetype_id="test-agent",
            description="Designs test strategy, selects meaningful edge cases, and diagnoses flaky or complex test failures.",
            mode=AgentMode.WRITE,
            preferred_model=Model.SONNET,
            permissions=AgentPermissions(
                can_read_files=True, can_write_files=True, can_execute_commands=True
            ),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            relevant_paths=[
                "tests/**",
                "**/test_*.py",
                "**/*_test.py",
                "**/*.test.*",
                "**/*.spec.*",
            ],
            responsibilities=[
                "Decide test strategy for a new feature",
                "Identify which edge cases actually matter",
                "Diagnose why a flaky or complex test fails",
                "Judge whether current coverage is adequate relative to risk",
            ],
            scope="Test strategy and coverage judgment",
            when_to_use="When automated tests need strategy, edge-case judgment, or failure diagnosis",
            when_not_to_use="For routine suite execution or template-driven test writing",
            expected_inputs=[
                "repo-map.json: directory tree, dependency manifest summary, subsystem boundaries"
            ],
            expected_outputs=[
                "test-report.json: pass/fail counts, coverage assessment, and diagnosis notes"
            ],
            completion_criteria=[
                "Test cases written and documented",
                "All tests passing",
                "Coverage judged adequate for the change's risk",
            ],
        ),
    },
    "bdd-feature-agent": {
        "haiku": AgentDefinition(
            id="bdd-feature-agent-haiku",
            archetype_id="bdd-feature-agent",
            description="Transcribes already-agreed acceptance criteria into Gherkin scenarios following the existing style.",
            mode=AgentMode.WRITE,
            preferred_model=Model.HAIKU,
            permissions=AgentPermissions(can_read_files=True, can_write_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            relevant_paths=["features/**", "**/*.feature"],
            responsibilities=[
                "Transcribe already-agreed acceptance criteria into Gherkin Given/When/Then syntax",
                "Follow the project's existing scenario style and vocabulary",
            ],
            scope="Mechanical transcription of agreed criteria into Gherkin",
            when_to_use="When acceptance criteria are already agreed and just need Gherkin formatting",
            when_not_to_use="When the scenarios themselves need to be derived from an ambiguous request",
            expected_inputs=[
                "repo-map.json: directory tree, dependency manifest summary, subsystem boundaries"
            ],
            expected_outputs=["feature-scenarios.feature: Gherkin scenarios"],
            completion_criteria=[
                "Scenarios written in valid Gherkin format",
                "Scenarios match the given acceptance criteria exactly",
            ],
        ),
        "sonnet": AgentDefinition(
            id="bdd-feature-agent-sonnet",
            archetype_id="bdd-feature-agent",
            description="Derives behavior-driven scenarios from an ambiguous feature request.",
            mode=AgentMode.WRITE,
            preferred_model=Model.SONNET,
            permissions=AgentPermissions(can_read_files=True, can_write_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            relevant_paths=["features/**", "**/*.feature"],
            responsibilities=[
                "Derive scenarios from an ambiguous feature request",
                "Decide the user-observable behavior boundaries",
                "Negotiate scenario scope with stakeholders",
            ],
            scope="Behavior-driven development and feature specification",
            when_to_use="When user-facing features need BDD-style specifications derived from an ambiguous request",
            when_not_to_use="Not used for internal utilities or non-user-facing code",
            expected_inputs=[
                "repo-map.json: directory tree, dependency manifest summary, subsystem boundaries"
            ],
            expected_outputs=["feature-scenarios.feature: Gherkin scenarios"],
            completion_criteria=[
                "Scenarios written in Gherkin format",
                "Scenarios validated with stakeholders",
                "Ready for step implementation",
            ],
        ),
    },
    "code-reviewer": {
        "haiku": AgentDefinition(
            id="code-reviewer-haiku",
            archetype_id="code-reviewer",
            description="Checks a diff against a fixed checklist without judging design quality.",
            mode=AgentMode.READ_ONLY,
            preferred_model=Model.HAIKU,
            permissions=AgentPermissions(can_read_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            responsibilities=[
                "Check a diff against a fixed checklist (lint/format/type-check pass, no leftover TODOs, tests/docstrings present for new public functions)",
                "Report pass/fail per checklist item",
            ],
            scope="Mechanical diff checklist verification",
            when_to_use="On every diff, as a fast pre-filter before deeper review",
            when_not_to_use="When correctness of non-obvious logic or compatibility risk needs judgment",
            expected_inputs=[
                "test-report.json: pass/fail counts, coverage assessment, and diagnosis notes"
            ],
            expected_outputs=["review-report.md: checklist pass/fail results"],
            completion_criteria=[
                "Every checklist item evaluated against the diff",
                "review-report.md lists all failing items with locations",
            ],
        ),
        "sonnet": AgentDefinition(
            id="code-reviewer-sonnet",
            archetype_id="code-reviewer",
            description="Reviews diffs for correctness of non-obvious logic, approach, and compatibility risk.",
            mode=AgentMode.READ_ONLY,
            preferred_model=Model.SONNET,
            permissions=AgentPermissions(can_read_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            responsibilities=[
                "Assess correctness of non-obvious logic",
                "Judge whether the chosen approach is right, not just whether it passes checks",
                "Evaluate compatibility risk with existing behavior",
            ],
            scope="Code review requiring judgment",
            when_to_use="After code changes are ready for review, especially non-obvious or risky ones",
            when_not_to_use="Not used for implementing changes or writing code",
            expected_inputs=[
                "test-report.json: pass/fail counts, coverage assessment, and diagnosis notes",
                "review-report.md: checklist pass/fail results",
            ],
            expected_outputs=["review-report.md: correctness and compatibility verdict"],
            completion_criteria=[
                "Diff reviewed for correctness",
                "Compatibility with codebase verified",
                "Test coverage adequacy assessed",
            ],
        ),
    },
    "documentation-agent": {
        "haiku": AgentDefinition(
            id="documentation-agent-haiku",
            archetype_id="documentation-agent",
            description="Updates doc sections whose content is directly derivable from a code change.",
            mode=AgentMode.WRITE,
            preferred_model=Model.HAIKU,
            permissions=AgentPermissions(can_read_files=True, can_write_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            relevant_paths=["docs/**", "README*", "CHANGELOG*", "**/*.md"],
            responsibilities=[
                "Update a doc section whose content is directly derivable from a code change (e.g. a changed signature, a new CLI flag)",
                "Follow the existing doc's format and style exactly",
            ],
            scope="Mechanical documentation updates derivable from code",
            when_to_use="When a change has a direct, unambiguous documentation consequence",
            when_not_to_use="When the mental model taught by the docs has changed, or new conceptual sections are needed",
            expected_inputs=[
                "repo-map.json: directory tree, dependency manifest summary, subsystem boundaries"
            ],
            completion_criteria=[
                "Documentation updated to reflect the change",
                "Existing doc format and style preserved",
            ],
        ),
        "sonnet": AgentDefinition(
            id="documentation-agent-sonnet",
            archetype_id="documentation-agent",
            description="Restructures documentation or writes new conceptual sections when the mental model has changed.",
            mode=AgentMode.WRITE,
            preferred_model=Model.SONNET,
            permissions=AgentPermissions(can_read_files=True, can_write_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            relevant_paths=["docs/**", "README*", "CHANGELOG*", "**/*.md"],
            responsibilities=[
                "Restructure documentation when the mental model it teaches has changed",
                "Write new conceptual or explanatory sections from scratch",
            ],
            scope="Documentation requiring judgment about what readers need to understand",
            when_to_use="When changes alter how the project should be explained, not just what's documented",
            when_not_to_use="Not used for direct, unambiguous doc updates — use the Haiku variant",
            expected_inputs=[
                "repo-map.json: directory tree, dependency manifest summary, subsystem boundaries"
            ],
            completion_criteria=[
                "Documentation restructured or new sections written",
                "Examples and usage docs synchronized",
            ],
        ),
    },
    "dependency-agent": {
        "haiku": AgentDefinition(
            id="dependency-agent-haiku",
            archetype_id="dependency-agent",
            description="Applies dependency updates already flagged as safe, non-breaking patch/minor bumps.",
            mode=AgentMode.WRITE,
            preferred_model=Model.HAIKU,
            permissions=AgentPermissions(
                can_read_files=True, can_write_files=True, can_execute_commands=True
            ),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            relevant_paths=[
                "package.json",
                "package-lock.json",
                "requirements*.txt",
                "pyproject.toml",
                "poetry.lock",
                "Cargo.toml",
                "Cargo.lock",
                "go.mod",
                "go.sum",
                "Gemfile",
                "Gemfile.lock",
            ],
            responsibilities=[
                "Run the dependency audit command and list outdated packages",
                "Apply patch/minor version bumps flagged as safe/non-breaking",
                "Verify build and tests still pass after applying updates",
            ],
            scope="Mechanical dependency audits and safe version bumps",
            when_to_use="For regular dependency audits and safe patch/minor updates",
            when_not_to_use="When a major version bump has breaking changes needing migration decisions",
            expected_outputs=[
                "dependency-audit.json: outdated/vulnerable packages and applied updates"
            ],
            completion_criteria=[
                "Dependencies audited for updates",
                "Safe updates applied and build/tests still pass",
            ],
        ),
        "sonnet": AgentDefinition(
            id="dependency-agent-sonnet",
            archetype_id="dependency-agent",
            description="Evaluates major version bumps with breaking changes and resolves real dependency conflicts.",
            mode=AgentMode.WRITE,
            preferred_model=Model.SONNET,
            permissions=AgentPermissions(
                can_read_files=True, can_write_files=True, can_execute_commands=True
            ),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            relevant_paths=[
                "package.json",
                "package-lock.json",
                "requirements*.txt",
                "pyproject.toml",
                "poetry.lock",
                "Cargo.toml",
                "Cargo.lock",
                "go.mod",
                "go.sum",
                "Gemfile",
                "Gemfile.lock",
            ],
            responsibilities=[
                "Evaluate a major-version bump with breaking changes and decide whether/how to migrate",
                "Resolve genuine version conflicts across the dependency graph",
            ],
            scope="Dependency decisions requiring migration judgment",
            when_to_use="When a dependency update has breaking changes or conflicting version constraints",
            when_not_to_use="For routine safe patch/minor updates — use the Haiku variant",
            expected_inputs=[
                "dependency-audit.json: outdated/vulnerable packages and applied updates"
            ],
            expected_outputs=[
                "dependency-audit.json: migration decisions and conflict resolutions"
            ],
            completion_criteria=[
                "Breaking-change bumps evaluated with a migration decision",
                "Compatibility across the dependency graph verified",
            ],
        ),
    },
    "ci-build-agent": {
        "haiku": AgentDefinition(
            id="ci-build-agent-haiku",
            archetype_id="ci-build-agent",
            description="Adds CI steps mirroring an existing pattern and fixes failures with an already-known cause.",
            mode=AgentMode.WRITE,
            preferred_model=Model.HAIKU,
            permissions=AgentPermissions(can_read_files=True, can_write_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            relevant_paths=[
                ".github/workflows/**",
                ".gitlab-ci.yml",
                ".circleci/**",
                "Jenkinsfile",
            ],
            responsibilities=[
                "Add or update a CI step by mirroring an existing, known-good pattern already used in the pipeline",
                "Fix a CI failure whose cause is unambiguous from the log",
            ],
            scope="Mechanical CI maintenance using existing patterns",
            when_to_use="When a needed CI change already has a working precedent elsewhere in the pipeline",
            when_not_to_use="When the pipeline structure itself needs redesigning, or the failure cause is unclear",
            expected_outputs=["ci-status.md: pipeline health report"],
            completion_criteria=[
                "CI configuration verified and updated",
                "Test suite passing in CI environment",
            ],
        ),
        "sonnet": AgentDefinition(
            id="ci-build-agent-sonnet",
            archetype_id="ci-build-agent",
            description="Redesigns pipeline structure and diagnoses CI failures with an unclear root cause.",
            mode=AgentMode.WRITE,
            preferred_model=Model.SONNET,
            permissions=AgentPermissions(can_read_files=True, can_write_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            relevant_paths=[
                ".github/workflows/**",
                ".gitlab-ci.yml",
                ".circleci/**",
                "Jenkinsfile",
            ],
            responsibilities=[
                "Redesign pipeline structure (caching strategy, matrix builds, new stages)",
                "Diagnose a CI failure whose root cause isn't obvious from the log",
            ],
            scope="CI/CD architecture and non-obvious failure diagnosis",
            when_to_use="When CI structure needs redesign or a failure's cause isn't clear",
            when_not_to_use="For routine changes with an existing working precedent — use the Haiku variant",
            expected_inputs=["ci-status.md: pipeline health report"],
            expected_outputs=["ci-status.md: redesign rationale and root-cause diagnosis"],
            completion_criteria=[
                "Pipeline structure change documented and verified",
                "Root cause of non-obvious failures identified",
            ],
        ),
    },
    "performance-agent": {
        "haiku": AgentDefinition(
            id="performance-agent-haiku",
            archetype_id="performance-agent",
            description="Runs an existing benchmark and reports numbers against a recorded baseline.",
            mode=AgentMode.READ_ONLY,
            preferred_model=Model.HAIKU,
            permissions=AgentPermissions(can_read_files=True, can_execute_commands=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            responsibilities=[
                "Run an existing benchmark/profiling command",
                "Report the numbers against a previously recorded baseline",
            ],
            scope="Mechanical benchmark execution and reporting",
            when_to_use="When an existing benchmark just needs to be run and compared to baseline",
            when_not_to_use="When judging significance of a regression or choosing an optimization approach",
            expected_inputs=[
                "repo-map.json: directory tree, dependency manifest summary, subsystem boundaries"
            ],
            expected_outputs=["performance-report.md: baseline vs current metrics"],
            completion_criteria=[
                "Benchmark executed and results recorded",
                "performance-report.md compares against baseline",
            ],
        ),
        "sonnet": AgentDefinition(
            id="performance-agent-sonnet",
            archetype_id="performance-agent",
            description="Judges significance of performance regressions and chooses optimization approaches.",
            mode=AgentMode.READ_ONLY,
            preferred_model=Model.SONNET,
            permissions=AgentPermissions(can_read_files=True, can_execute_commands=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            responsibilities=[
                "Decide whether an observed regression is significant or acceptable",
                "Identify why a hotspot exists and what to do about it",
                "Choose an optimization approach and weigh its trade-offs",
            ],
            scope="Performance judgment and optimization strategy",
            when_to_use="When a regression needs a significance call or a hotspot needs a fix strategy",
            when_not_to_use="For routine benchmark execution — use the Haiku variant",
            expected_inputs=["performance-report.md: baseline vs current metrics"],
            expected_outputs=[
                "performance-report.md: significance verdict and optimization recommendation"
            ],
            completion_criteria=[
                "Regression significance judged",
                "Hotspots identified with a recommended approach",
            ],
        ),
    },
    "security-reviewer": {
        "haiku": AgentDefinition(
            id="security-reviewer-haiku",
            archetype_id="security-reviewer",
            description="Runs known-pattern security checks (secrets, disabled TLS, SQL concatenation, unsafe eval) via grep/lint.",
            mode=AgentMode.READ_ONLY,
            preferred_model=Model.HAIKU,
            permissions=AgentPermissions(can_read_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            responsibilities=[
                "Run known-pattern checks (hardcoded secrets, disabled TLS verification, string-concatenated SQL, eval/exec of untrusted input)",
                "Report every match with its location — do not judge exploitability",
            ],
            scope="Mechanical known-pattern security scanning",
            when_to_use="On every change, as a fast pre-filter before deeper security review",
            when_not_to_use="When judging real-world exploitability or looking for non-pattern-matched risks",
            expected_outputs=["security-findings.md: known-pattern matches with locations"],
            completion_criteria=[
                "All known patterns checked against the change",
                "security-findings.md lists every match with location",
            ],
        ),
        "sonnet": AgentDefinition(
            id="security-reviewer-sonnet",
            archetype_id="security-reviewer",
            description="Assesses real exploitability of flagged patterns and looks for non-pattern-matched security risks.",
            mode=AgentMode.READ_ONLY,
            preferred_model=Model.SONNET,
            permissions=AgentPermissions(can_read_files=True),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            responsibilities=[
                "Assess exploitability/severity of a flagged pattern in context",
                "Evaluate non-pattern-matched security risks (business logic flaws, auth bypass reasoning)",
                "Decide an overall risk verdict",
            ],
            scope="Security review requiring exploitability and business-logic judgment",
            when_to_use="When changes involve security-sensitive code or data handling, or a Haiku-tier pattern was flagged",
            when_not_to_use="Not used for non-security concerns",
            expected_inputs=["security-findings.md: known-pattern matches with locations"],
            expected_outputs=[
                "security-findings.md: exploitability verdicts and non-pattern risk findings"
            ],
            completion_criteria=[
                "Security review completed with a risk verdict",
                "Security recommendations documented",
            ],
        ),
    },
    "release-agent": {
        "haiku": AgentDefinition(
            id="release-agent-haiku",
            archetype_id="release-agent",
            description="Bumps version strings across known files and appends a changelog entry from a supplied list of changes.",
            mode=AgentMode.WRITE,
            preferred_model=Model.HAIKU,
            permissions=AgentPermissions(
                can_read_files=True, can_write_files=True, can_create_commits=True
            ),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            relevant_paths=["CHANGELOG*", "pyproject.toml", "package.json", "**/_version.py"],
            responsibilities=[
                "Bump version strings across the known version-bearing files",
                "Append a changelog entry from an already-supplied list of changes, following the existing format",
            ],
            scope="Mechanical version bump and changelog entry from a given change list",
            when_to_use="When the semver level and the list of changes are already decided",
            when_not_to_use="When the semver level is ambiguous or the changelog prose requires summarizing/judgment",
            expected_inputs=[
                "test-report.json: pass/fail counts, coverage assessment, and diagnosis notes",
                "review-report.md: correctness and compatibility verdict",
                "security-findings.md: exploitability verdicts and non-pattern risk findings",
            ],
            expected_outputs=["release-notes.md: version bump and changelog entry"],
            completion_criteria=[
                "Version number updated in every known-version-bearing file",
                "Changelog updated with the given release notes",
            ],
        ),
        "sonnet": AgentDefinition(
            id="release-agent-sonnet",
            archetype_id="release-agent",
            description="Decides the semver bump level from ambiguous changes and judges release readiness.",
            mode=AgentMode.WRITE,
            preferred_model=Model.SONNET,
            permissions=AgentPermissions(
                can_read_files=True, can_write_files=True, can_create_commits=True
            ),
            lifetime=AgentLifetime.PERMANENT,
            source=DefinitionSource.DEFAULT,
            relevant_paths=["CHANGELOG*", "pyproject.toml", "package.json", "**/_version.py"],
            responsibilities=[
                "Decide the semver bump level from ambiguous or mixed breaking/non-breaking changes",
                "Write changelog prose that requires summarizing and judging what matters to users",
                "Decide release readiness, blocking if a signal suggests it's premature",
            ],
            scope="Release judgment: semver level, changelog synthesis, readiness",
            when_to_use="When the semver level isn't obvious, or release readiness needs a judgment call",
            when_not_to_use="When semver level and change list are already fully decided — use the Haiku variant",
            expected_inputs=[
                "test-report.json: pass/fail counts, coverage assessment, and diagnosis notes",
                "review-report.md: correctness and compatibility verdict",
                "security-findings.md: exploitability verdicts and non-pattern risk findings",
            ],
            expected_outputs=[
                "release-notes.md: version bump, changelog entry, and readiness verdict"
            ],
            completion_criteria=[
                "Semver level decided and justified",
                "Changelog updated with release notes",
                "Release readiness verdict recorded",
            ],
        ),
    },
}
