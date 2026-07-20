# Self-hosting

Dogfooding means low-risk local work; self-hosting means QuattroAgents develops QuattroAgents; self-configuration means it proposes, never activates, configuration changes. Bootstrap remains independent: create `.venv`, install the package, then run the CLI. If generated configuration is problematic, restore a timestamped backup from `.quattroagents/backups/` and rerun validation.

## 0.3 run record

Version 0.3 makes self-hosting auditable through one ordered workflow:

`plan → execute → review → integrate`

Create a run with a stable run ID bound to its task contract, source commit and runtime version. Append exactly one immutable snapshot for each stage, in that order. A snapshot has its own stable ID, a concise summary, changed-file references, artifact references (`id`, path, kind and SHA-256), evidence references (`id`, reference and SHA-256), and the digest of the preceding snapshot. The resulting SHA-256 digest chain can be verified after the run is recorded.

Use the local CLI to create, inspect and verify the record:

```bash
.venv/bin/python -m quattroagents self-hosting run create RUN-ID TASK-ID \
  --source-commit COMMIT --runtime-version VERSION --format json
.venv/bin/python -m quattroagents self-hosting run snapshot RUN-ID SNAPSHOT-ID plan \
  --summary "Concise plan reference" --format json
.venv/bin/python -m quattroagents self-hosting run show RUN-ID --format json
.venv/bin/python -m quattroagents self-hosting run verify RUN-ID --format json
```

Snapshots are append-only: they cannot be updated or removed. Keep their context synthetic and point to durable artifacts and evidence rather than embedding transcripts or raw logs.

## Safety boundary

Recording a run does not execute agents, dispatch a fleet or activate any configuration. The 0.2 contract, confirmed user interview and bounded-worker limits still apply. `integrate` is permitted only after `review`; protected-kernel paths listed in `quality-gates.json` additionally require explicit recorded human approval. This gate does not merge branches, push changes or create tags.

The future local-scripts/skills opportunity is a separate optimization milestone. Candidate scripts must be deterministic local operations, and their token or execution-time benefit must be demonstrated with reproducible benchmarks before it is claimed.
