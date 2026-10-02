"""Read-only public deployment checks; no users, payments or model calls created."""
import argparse
import json
from urllib.parse import urlsplit

import requests


def check(base):
    parsed = urlsplit(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("A plain HTTPS origin is required")
    base = base.rstrip("/")
    results = []
    session = requests.Session()
    for path, accepted in [("/health", {200}), ("/v1/balance", {401}),
                           ("/api/users", {401, 403, 404}), ("/admin/users", {401, 403, 404})]:
        try:
            response = session.get(base + path, timeout=20, allow_redirects=False)
            passed = response.status_code in accepted
            # An HTML SPA fallback with HTTP 200 is not a healthy API response.
            if path == "/health":
                passed = passed and isinstance(response.json(), dict)
            results.append({"path": path, "status": response.status_code, "passed": passed})
        except (requests.RequestException, ValueError) as exc:
            results.append({"path": path, "passed": False, "error_type": type(exc).__name__})
    return {"base": base, "read_only": True, "checks": results,
            "passed": all(item["passed"] for item in results),
            "scope": "Public reachability and anonymous access boundaries only; does not attest deployed revision or integrations."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    args = parser.parse_args(argv)
    result = check(args.base)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
