"""Preview or apply age-based conversation retention, excluding active profiles."""
import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.storage.locking import ProfileBusyError, ProfileLease, profile_lock_path


def prune(root, days=90, apply=False):
    root = Path(root).resolve(strict=True)
    if days < 1:
        raise ValueError("Retention must be at least one day")
    cutoff = time.time() - days * 86400
    result = {"apply": apply, "eligible": [], "deleted": [], "busy_profiles": [], "unsafe_paths": []}
    for candidate in sorted(root.glob("users/*/conversations/*.jsonl")):
        relative = candidate.relative_to(root)
        # Never traverse user-controlled links, including parent directory links.
        if any(path.is_symlink() for path in (candidate, *candidate.parents) if path != root):
            result["unsafe_paths"].append(str(relative))
            continue
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root) or not resolved.is_file():
            continue
        profile = candidate.parent.parent / "profile.json"
        try:
            with ProfileLease(profile_lock_path(profile)):
                if candidate.stat().st_mtime >= cutoff:
                    continue
                result["eligible"].append(str(relative))
                if apply:
                    resolved.unlink()
                    result["deleted"].append(str(relative))
        except ProfileBusyError:
            result["busy_profiles"].append(candidate.parent.parent.name)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage", required=True, type=Path)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--apply", action="store_true", help="Delete eligible logs; default only previews")
    args = parser.parse_args(argv)
    if not args.storage.is_dir() or args.days < 1:
        parser.error("Existing storage directory and positive retention period required")
    print(json.dumps(prune(args.storage, args.days, args.apply), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
