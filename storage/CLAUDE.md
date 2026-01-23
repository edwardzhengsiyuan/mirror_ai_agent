# Storage Directory Structure

Directory layout for user data and logs.

---

## Directory Structure

```
storage/
└── users/
    └── <user_id>/
        ├── profile.json              # User profile (includes node_cache)
        └── conversations/
            └── <session>.jsonl       # Session logs (includes LLM traces)
```

## Path Conventions

| Type | Path |
|------|------|
| Profile | `storage/users/<user_id>/profile.json` |
| Conversations | `storage/users/<user_id>/conversations/<session>.jsonl` |

## Notes

- **Do not create files at `storage/` root level** (legacy structure)
- All user data must be stored under `storage/users/<user_id>/`
- `save_profile`/`append_event` will automatically create directories

## API Reference

See `agent/storage/CLAUDE.md` for storage API details.
