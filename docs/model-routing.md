# Model routing

Each `AgentDefinition` declares a `preferred_model` (from the `Model` enum: `haiku`, `sonnet`, `opus`, or `inherit`) and an optional `fallback_model`. These are selected during agent generation based on the agent's role and responsibilities — for example, bounded deterministic work typically defaults to haiku, integration and semantic review to sonnet, and architecture resolution to opus. There is no separate routing configuration file; model choice is intrinsic to each generated agent definition and can be overridden by decisions or manual edits to the generated files.
