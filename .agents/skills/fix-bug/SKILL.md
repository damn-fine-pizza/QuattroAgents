---
name: fix-bug
trigger: Diagnose and fix a reported bug.
---

## Workflow
1. Reproduce the bug with a minimal test case.
2. Identify root cause by inspecting relevant code.
3. Implement a targeted fix with regression tests.
4. Verify the fix resolves the issue without side effects.

## Inputs
- Bug report with reproduction steps
- Expected behavior
- Affected system or component

## Outputs
- Bug fix code
- Regression test
- Root cause analysis

## Required tools
None declared.

## Validation criteria
- Bug successfully reproduced and fixed
- Regression test passes
- No new issues introduced

## Usable by
implementation-agent