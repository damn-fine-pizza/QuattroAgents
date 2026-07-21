---
name: update-dependencies
trigger: Check for and apply compatible dependency updates.
---

## Workflow
1. Scan dependencies for available updates.
2. Identify breaking changes in candidates.
3. Update compatible versions and lock file.
4. Run tests to verify compatibility.

## Inputs
- Dependency manifest or lock file
- Update strategy (major/minor/patch)
- Security advisory list (if any)

## Outputs
- Updated dependency versions
- Updated lock file
- Test results and compatibility report

## Required tools
None declared.

## Validation criteria
- Updates applied safely without breaking changes
- All tests pass with new versions
- Security advisories resolved

## Usable by
dependency-agent