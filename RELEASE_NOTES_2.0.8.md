# AI Dev Launcher v2.0.8

This patch fixes integrated Codex conversations with Codex CLI 0.146 and newer.

## Fixes

- Send an explicit blank stdin line so a completed Headroom-wrapped Codex turn
  exits successfully instead of returning exit code 1.
- Decode streaming stdout and stderr safely across UTF-8 chunk boundaries.
- Keep routine Codex and plugin warnings out of the conversation timeline.
- Show the meaningful stderr tail when a Codex task genuinely fails.
- Prevent centered status messages from collapsing into a narrow vertical
  column.

