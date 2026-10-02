"""Check vendored browser dependency versions against npm's advisory API."""
import json
from pathlib import Path
import urllib.request


def main():
    root = Path(__file__).resolve().parents[1]
    packages = json.loads((root / "web/vendor/manifest.json").read_text())
    payload = {item["package"]: [item["version"]] for item in packages}
    request = urllib.request.Request("https://registry.npmjs.org/-/npm/v1/security/advisories/bulk",
                                     data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        advisories = json.load(response)
    print(json.dumps({"packages": payload, "advisories": advisories}, indent=2))
    return 1 if advisories else 0


if __name__ == "__main__":
    raise SystemExit(main())
