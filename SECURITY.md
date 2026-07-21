# Security policy

Do not commit secrets. QuattroAgents keeps all generated and analyzed state local to the target project's `.agent-factory/` directory, and validates every write path stays inside the project root before touching disk (`persistence.safe_path`). Report vulnerabilities privately to repository maintainers.
