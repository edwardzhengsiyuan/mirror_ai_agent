# Storage Structure

## Directory Layout

```
storage/
├── users/
│   └── <user_id>/
│       ├── profile.json              # User profile (includes node_cache)
│       └── conversations/
│           └── <session>.jsonl       # Session logs
└── logs/
    └── llm_trace.jsonl               # LLM call trace
```

## Path Conventions

| Type | Path |
|------|------|
| Profile | `storage/users/<user_id>/profile.json` |
| Conversations | `storage/users/<user_id>/conversations/<session>.jsonl` |
| Logs | `storage/logs/` |

## Rules

- All user data must be stored in `storage/users/<user_id>/`
- **Do not create files at `storage/` root level** (legacy structure)
- `save_profile`/`append_event` will automatically create directories

## API Reference

See `agent/storage/CLAUDE.md` for storage API details.
