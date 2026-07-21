# Roadmap

## Historical milestones

Versions 0.2.0 through 0.6.1 were planned under the previous "dogfooding via control-plane" architecture. That architecture has been replaced with the Project Agent Factory design, which provides a simpler, more explicit model for adaptive interviewing, decision recording, agent generation, swarm planning, and skill validation.

## Project Agent Factory roadmap

A roadmap for the Project Agent Factory architecture has not yet been written. Future milestones and feature plans will be documented as they are decided.

## TODO (deferred, not yet scheduled)

- **Agent activity dashboard.** Generate a `SubagentStart`/`SubagentStop` hook pair that
  appends per-agent activity (model, token usage, tool-use count, duration) to a local
  log (e.g. `.agent-factory/activity.jsonl`), plus a static local page that reads that
  log to show active/recent agents, model distribution, and cumulative token usage.
  Claude Code does track per-subagent token/tool-use/duration data (observed directly
  in Agent-tool completion notifications), but the exact `SubagentStop` hook payload
  and `transcript_path` JSONL schema are not fully documented — needs one empirical
  test (write a hook that dumps stdin + inspects `transcript_path`) before designing
  the log format. Not a live/real-time dashboard: refreshed per hook event, not
  per-token. Deferred until prioritized.
