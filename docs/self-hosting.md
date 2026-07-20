# Self-hosting

Dogfooding means low-risk local work; self-hosting means QuattroAgents develops QuattroAgents; self-configuration means it proposes, never activates, configuration changes. Version 0.2 enables only dogfooding. Bootstrap remains independent: create `.venv`, install the package, then run the CLI. If generated configuration is problematic, restore a timestamped backup from `.quattroagents/backups/` and rerun validation.

Protected kernel paths are recorded in `quality-gates.json`; small workers cannot change them. Official self-hosting requires 0.3 run snapshots, independent review and human approval.
