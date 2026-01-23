# Documentation Guide

## Directory Documentation Mapping

When modifying code in a directory, **read the relevant documentation first**:

| Directory | Documentation |
|-----------|--------------|
| `agent/` | `agent/CLAUDE.md` |
| `agent/tools/` | `agent/tools/CLAUDE.md` |
| `agent/prompts/` | `agent/prompts/CLAUDE.md` |
| `agent/storage/` | `agent/storage/CLAUDE.md` |
| `bazi/` | `bazi/CLAUDE.md` |
| `web/` | `web/CLAUDE.md` |
| `storage/` | `storage/CLAUDE.md` |
| `tests/` | `tests/CLAUDE.md` |

## Documentation Policy

- Canonical project overview and configuration: `CLAUDE.md`
- Canonical agent core docs: `agent/CLAUDE.md`
- Engine API reference: `bazi/CLAUDE.md`
- **Documentation updates are NOT optional** - they are part of completing a task

## File Structure

All documentation uses CLAUDE.md files:
- `/CLAUDE.md` - Project overview, configuration, integration guide, documentation index
- `/agent/CLAUDE.md` - Agent core documentation
- `/tests/CLAUDE.md` - Test documentation
- Subdirectory CLAUDE.md files - Module-specific documentation
